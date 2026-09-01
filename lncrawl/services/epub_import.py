from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import html
import io
import json
import logging
from pathlib import Path, PurePosixPath
import posixpath
import shutil
import stat
from threading import Event, Lock
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlsplit
import zipfile

import ebooklib
from ebooklib import epub
from fastapi import UploadFile
from lxml import etree
from PIL import Image, ImageOps
import sqlmodel as sq

from ..context import ctx
from ..dao import Chapter, ChapterImage, ImportSession, Job, Novel, Volume
from ..exceptions import AbortedException, ServerErrors
from ..utils.text_tools import generate_uuid
from ..utils.time_utils import current_timestamp

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_ZIP_ENTRIES = 10_000
MAX_ENTRY_BYTES = 50 * 1024 * 1024
MAX_CHAPTER_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_XML_BYTES = 2 * 1024 * 1024
SESSION_TTL_MS = 24 * 60 * 60 * 1000
SESSION_RETENTION_MS = 60 * 60 * 1000
IMPORT_DOMAIN = "本地导入"
IMPORT_URL_PREFIX = "local-import://sha256/"
_PENDING_NOVEL_MARKER = ".epub-import-pending"
_ACTIVE_SESSION_STATUSES = frozenset({"analyzing", "ready", "committing"})
_CHUNK_SIZE = 1024 * 1024

_ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}
_REMOVE_TAGS = {
    "audio",
    "embed",
    "form",
    "iframe",
    "input",
    "object",
    "script",
    "select",
    "style",
    "textarea",
    "video",
}


class EpubImportError(ValueError):
    """A user-facing EPUB validation or parsing failure."""

    def __init__(self, detail: str, user_message: str = "这个 EPUB 文件无法导入。") -> None:
        super().__init__(detail)
        self.user_message = user_message


@dataclass
class _TocEntry:
    href: str
    title: str
    volume: Optional[str] = None


def _check_cancel(signal: Event) -> None:
    if signal.is_set():
        raise AbortedException()


def _zip_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    if not normalized or normalized.startswith("/") or ":" in normalized.split("/", 1)[0]:
        raise EpubImportError("EPUB contains an absolute archive path.")
    parts = PurePosixPath(normalized).parts
    if any(part in ("", ".", "..") for part in parts):
        raise EpubImportError("EPUB contains an unsafe archive path.")
    return posixpath.normpath(normalized)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _parse_xml(raw: bytes, *, allow_doctype: bool = False) -> Any:
    if len(raw) > MAX_XML_BYTES:
        raise EpubImportError("EPUB XML metadata exceeds the supported size limit.")
    lowered = raw.lower()
    if b"<!entity" in lowered or (b"<!doctype" in lowered and not allow_doctype):
        raise EpubImportError("EPUB XML metadata contains unsupported declarations.")
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=False,
    )
    try:
        root = etree.fromstring(raw, parser=parser)
    except etree.XMLSyntaxError as error:
        raise EpubImportError("EPUB XML metadata is invalid.") from error
    docinfo: Any = root.getroottree().docinfo
    if docinfo.doctype and not allow_doctype:
        raise EpubImportError("EPUB XML metadata contains unsupported declarations.")
    if docinfo.internalDTD is not None and list(docinfo.internalDTD.iterentities()):
        raise EpubImportError("EPUB XML metadata contains unsupported entities.")
    return root


def _metadata(book: epub.EpubBook, namespace: str, key: str) -> List[str]:
    values: List[str] = []
    for value, _attrs in book.get_metadata(namespace, key):
        if value:
            values.append(str(value).strip())
    return [value for value in values if value]


def _normalize_language(value: str) -> Optional[str]:
    value = value.strip().lower()
    if not value:
        return None
    return value.split("-", 1)[0][:2] or None


def _reference_candidates(reference: str, base_dir: str = "") -> List[str]:
    parsed = urlsplit(unquote(str(reference)))
    path = parsed.path.replace("\\", "/")
    if parsed.scheme or parsed.netloc or not path or path.startswith("/"):
        return []

    candidates = [posixpath.join(base_dir, path)] if base_dir else []
    candidates.append(path)
    normalized: List[str] = []
    for candidate in candidates:
        try:
            name = _zip_name(posixpath.normpath(candidate))
        except EpubImportError:
            continue
        if name not in normalized:
            normalized.append(name)
    return normalized


def _match_name(
    href: str,
    names: Iterable[str],
    base_dir: str = "",
) -> Optional[str]:
    available = list(names)
    candidates = _reference_candidates(href, base_dir)
    for candidate in candidates:
        if candidate in available:
            return candidate
    matches = [
        name for candidate in candidates for name in available if name.endswith(f"/{candidate}")
    ]
    return min(matches, key=len) if matches else None


def _package_path(reference: str) -> str:
    candidates = _reference_candidates(reference)
    if not candidates:
        raise EpubImportError("EPUB contains an unsafe package path.")
    return candidates[0]


def _cover_name(path: Path, names: set[str]) -> Optional[str]:
    try:
        with zipfile.ZipFile(path) as archive:
            container = _parse_xml(archive.read("META-INF/container.xml"))
            rootfile = next(
                (element for element in container.iter() if _local_name(element.tag) == "rootfile"),
                None,
            )
            if rootfile is None:
                return None
            opf_path = _package_path(str(rootfile.attrib.get("full-path") or ""))
            opf_dir = posixpath.dirname(opf_path)
            opf = _parse_xml(archive.read(opf_path))
            manifest: Dict[str, str] = {}
            for element in opf.iter():
                if _local_name(element.tag) != "item":
                    continue
                item_id = element.attrib.get("id")
                href = element.attrib.get("href")
                if item_id and href:
                    resolved = _match_name(href, names, opf_dir)
                    if resolved:
                        manifest[item_id] = resolved

            for element in opf.iter():
                if _local_name(element.tag) == "meta" and element.attrib.get("name") == "cover":
                    candidate = manifest.get(element.attrib.get("content", ""))
                    if candidate in names:
                        return candidate

            for element in opf.iter():
                if _local_name(element.tag) == "item":
                    properties = set(str(element.attrib.get("properties", "")).split())
                    if "cover-image" in properties:
                        candidate = manifest.get(element.attrib.get("id", ""))
                        if candidate in names:
                            return candidate

            for element in opf.iter():
                if (
                    _local_name(element.tag) == "reference"
                    and element.attrib.get("type") == "cover"
                ):
                    candidate = _match_name(
                        posixpath.join(opf_dir, element.attrib.get("href", "")),
                        names,
                    )
                    if candidate in names:
                        return candidate
    except (KeyError, ValueError, zipfile.BadZipFile):
        return None
    return next(
        (
            name
            for name in sorted(names)
            if "cover" in Path(name).stem.lower()
            and Path(name).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ),
        None,
    )


def _manifest_properties(path: Path, opf_path: str) -> Dict[str, set[str]]:
    with zipfile.ZipFile(path) as archive:
        opf = _parse_xml(archive.read(opf_path))
    properties: Dict[str, set[str]] = {}
    for element in opf.iter():
        if _local_name(element.tag) != "item":
            continue
        item_id = element.attrib.get("id")
        if item_id:
            properties[item_id] = set(str(element.attrib.get("properties", "")).split())
    return properties


def _toc_base_dir(path: Path, opf_path: str, names: set[str]) -> str:
    with zipfile.ZipFile(path) as archive:
        opf = _parse_xml(archive.read(opf_path))
    manifest: Dict[str, str] = {}
    opf_dir = posixpath.dirname(opf_path)
    for element in opf.iter():
        if _local_name(element.tag) != "item":
            continue
        item_id = element.attrib.get("id")
        href = element.attrib.get("href")
        if item_id and href:
            resolved = _match_name(href, names, opf_dir)
            if resolved:
                manifest[item_id] = resolved
    spine = next((element for element in opf.iter() if _local_name(element.tag) == "spine"), None)
    toc_id = spine.attrib.get("toc") if spine is not None else None
    toc_name = manifest.get(str(toc_id)) if toc_id else None
    return posixpath.dirname(toc_name) if toc_name else opf_dir


def _flatten_toc(nodes: Iterable[Any], volume: Optional[str] = None) -> List[_TocEntry]:
    entries: List[_TocEntry] = []
    for node in nodes:
        title = str(getattr(node, "title", "") or "").strip()
        subitems = getattr(node, "subitems", None)
        href = str(getattr(node, "href", "") or "").strip()
        if subitems:
            entries.extend(_flatten_toc(subitems, title or volume))
        elif href:
            entries.append(_TocEntry(href=href, title=title, volume=volume))
    return entries


def _image_jpeg(raw: bytes) -> Optional[bytes]:
    if len(raw) > MAX_IMAGE_BYTES:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                return None
            image = ImageOps.exif_transpose(image).convert("RGB")
            output = io.BytesIO()
            image.save(output, "JPEG", optimize=True)
            data = output.getvalue()
            return data if len(data) <= MAX_IMAGE_BYTES else None
    except (OSError, ValueError):
        return None


def _clean_html(
    raw: bytes,
    item_name: str,
    image_items: Dict[str, Any],
    image_paths: Dict[str, str],
    prepared_images: Path,
) -> Tuple[str, List[str]]:
    from bs4 import BeautifulSoup, Comment

    soup = BeautifulSoup(raw, "html.parser")
    root = soup.body or soup
    used_images: List[str] = []
    for comment in root.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for tag in list(root.find_all(_REMOVE_TAGS)):
        tag.decompose()

    for tag in list(root.find_all(True)):
        name = str(tag.name).lower()
        if name not in _ALLOWED_TAGS:
            tag.unwrap()
            continue
        if name == "a":
            tag.unwrap()
            continue
        if name == "img":
            src = str(tag.get("src") or "").strip()
            split = urlsplit(src)
            if split.scheme or split.netloc or src.startswith("data:"):
                tag.decompose()
                continue
            resource_name = _match_name(
                split.path,
                image_items.keys(),
                posixpath.dirname(item_name),
            )
            if resource_name is None:
                tag.decompose()
                continue
            image_item = image_items[resource_name]
            if resource_name not in image_paths:
                converted = _image_jpeg(image_item.get_content())
                if converted is None:
                    tag.decompose()
                    continue
                image_id = sha256(resource_name.encode("utf-8") + converted).hexdigest()[:32]
                relative = f"images/{image_id}.jpg"
                target = prepared_images / f"{image_id}.jpg"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(converted)
                image_paths[resource_name] = relative
            relative = image_paths[resource_name]
            image_id = Path(relative).stem
            tag.attrs = {"src": relative, "alt": image_id}
            if image_id not in used_images:
                used_images.append(image_id)
            continue
        tag.attrs = {}

    body = "".join(str(child) for child in root.contents).strip()
    text = root.get_text(" ", strip=True)
    if not text and not used_images:
        return "", used_images
    if len(body.encode("utf-8")) > MAX_CHAPTER_BYTES:
        raise EpubImportError("A chapter exceeds the supported size limit.")
    return body, used_images


def _validate_archive(path: Path) -> Tuple[set[str], str]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise EpubImportError("EPUB contains too many archive entries.")
            names: set[str] = set()
            total = 0
            for info in infos:
                name = _zip_name(info.filename)
                if name in names:
                    raise EpubImportError("EPUB contains duplicate archive paths.")
                names.add(name)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise EpubImportError("EPUB contains a symbolic link.")
                if info.flag_bits & 0x1:
                    raise EpubImportError("Encrypted EPUB files are not supported.")
                if info.file_size > MAX_ENTRY_BYTES:
                    raise EpubImportError("An EPUB entry exceeds the supported size limit.")
                total += info.file_size
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise EpubImportError("EPUB expands beyond the supported size limit.")
                if info.compress_size == 0 and info.file_size:
                    raise EpubImportError("EPUB contains an invalid compressed entry.")
                if info.compress_size and info.file_size / info.compress_size > 1000:
                    raise EpubImportError("EPUB compression ratio is too high.")

            if "mimetype" not in names or archive.read("mimetype") != b"application/epub+zip":
                raise EpubImportError("EPUB mimetype is missing or invalid.")
            container = _parse_xml(archive.read("META-INF/container.xml"))
            for name in names:
                if Path(name).suffix.lower() == ".opf":
                    _parse_xml(archive.read(name))
                elif Path(name).suffix.lower() == ".ncx":
                    _parse_xml(archive.read(name), allow_doctype=True)
            rootfile = next(
                (element for element in container.iter() if _local_name(element.tag) == "rootfile"),
                None,
            )
            if rootfile is None:
                raise EpubImportError("EPUB package document is missing.")
            opf_path = _package_path(str(rootfile.attrib.get("full-path") or ""))
            if opf_path not in names:
                raise EpubImportError("EPUB package document is missing.")
            return names, opf_path
    except zipfile.BadZipFile as error:
        raise EpubImportError("The uploaded file is not a valid ZIP archive.") from error
    except KeyError as error:
        raise EpubImportError("EPUB package files are incomplete.") from error


class EpubParser:
    def analyze(
        self,
        source_path: Path,
        prepared_dir: Path,
        signal: Event,
        on_phase: Callable[[str], None],
    ) -> Dict[str, Any]:
        prepared_dir.mkdir(parents=True, exist_ok=True)
        prepared_images = prepared_dir / "images"
        prepared_chapters = prepared_dir / "chapters"
        prepared_images.mkdir()
        prepared_chapters.mkdir()

        on_phase("校验 EPUB 文件")
        names, opf_path = _validate_archive(source_path)
        opf_dir = posixpath.dirname(opf_path)
        _check_cancel(signal)

        on_phase("读取书籍信息和封面")
        manifest_properties = _manifest_properties(source_path, opf_path)
        toc_base_dir = _toc_base_dir(source_path, opf_path, names)
        try:
            book = epub.read_epub(str(source_path))
        except Exception as error:
            raise EpubImportError("ebooklib could not read the EPUB package.") from error
        title = (_metadata(book, "DC", "title") or [""])[0]
        authors = ", ".join(_metadata(book, "DC", "creator"))
        language = _normalize_language((_metadata(book, "DC", "language") or [""])[0])
        descriptions = _metadata(book, "DC", "description")
        tags = _metadata(book, "DC", "subject")
        synopsis = f"<p>{html.escape(descriptions[0])}</p>" if descriptions else ""

        image_items: Dict[str, Any] = {}
        for item in book.get_items():
            if item.get_type() not in {ebooklib.ITEM_IMAGE, ebooklib.ITEM_COVER}:
                continue
            item_name = _match_name(str(item.get_name()), names, opf_dir)
            if item_name:
                image_items[item_name] = item
        cover_name = _cover_name(source_path, set(names))
        cover_path: Optional[str] = None
        if cover_name and cover_name in image_items:
            cover = _image_jpeg(image_items[cover_name].get_content())
            if cover is not None:
                cover_path = "cover.jpg"
                (prepared_dir / cover_path).write_bytes(cover)

        on_phase("读取目录与章节")
        toc_entries = _flatten_toc(book.toc)
        toc_by_name: Dict[str, _TocEntry] = {}
        for entry in toc_entries:
            matched = _match_name(entry.href, names, toc_base_dir)
            if matched is None and toc_base_dir != opf_dir:
                matched = _match_name(entry.href, names, opf_dir)
            if matched and matched not in toc_by_name:
                toc_by_name[matched] = entry

        spine_items: List[Tuple[str, Any]] = []
        for idref, linear in book.spine:
            if str(linear).lower() == "no":
                continue
            item = book.get_item_with_id(idref)
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue
            if "nav" in manifest_properties.get(str(idref), set()):
                continue
            item_name = _match_name(str(item.get_name()), names, opf_dir)
            if item_name:
                spine_items.append((item_name, item))
        if not spine_items:
            raise EpubImportError(
                "EPUB has no readable spine documents.",
                "这个 EPUB 没有可读章节。",
            )

        on_phase("清理正文和图片")
        image_paths: Dict[str, str] = {}
        chapters: List[Dict[str, Any]] = []
        volume_numbers: Dict[str, int] = {}
        volume_titles: Dict[int, str] = {}
        for serial, (item_name, item) in enumerate(spine_items, start=1):
            _check_cancel(signal)
            toc = toc_by_name.get(item_name)
            raw = item.get_content()
            body, used_images = _clean_html(
                raw,
                item_name,
                image_items,
                image_paths,
                prepared_images,
            )
            if not body:
                continue
            heading = ""
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(raw, "html.parser")
            heading_tag = soup.find(["h1", "h2", "h3"])
            if heading_tag:
                heading = heading_tag.get_text(" ", strip=True)
            chapter_title = (
                (toc.title if toc else "")
                or heading
                or str(getattr(item, "title", "") or "").strip()
            )
            chapter_title = chapter_title or f"第 {len(chapters) + 1} 章"
            volume_title = (toc.volume if toc else None) or "正文"
            if volume_title not in volume_numbers:
                volume_number = len(volume_numbers) + 1
                volume_numbers[volume_title] = volume_number
                volume_titles[volume_number] = volume_title
            volume_number = volume_numbers[volume_title]
            output_serial = len(chapters) + 1
            body_path = f"chapters/{output_serial:06}.html"
            (prepared_chapters / f"{output_serial:06}.html").write_text(
                body,
                encoding="utf-8",
            )
            chapters.append(
                {
                    "stable_key": item_name,
                    "title": chapter_title,
                    "serial": output_serial,
                    "volume": volume_number,
                    "volume_title": volume_title,
                    "body_path": body_path,
                    "images": used_images,
                    "body_preview": BeautifulSoup(body, "html.parser").get_text(" ", strip=True)[
                        :240
                    ],
                }
            )

        if not chapters:
            raise EpubImportError(
                "EPUB has no non-empty chapter bodies.",
                "这个 EPUB 没有可读章节正文。",
            )

        on_phase("生成导入预览")
        if not title:
            title = source_path.stem
        samples = [
            chapters[0],
            chapters[len(chapters) // 2],
            chapters[-1],
        ]
        preview = {
            "title": title,
            "authors": authors,
            "language": language,
            "synopsis": synopsis,
            "tags": tags,
            "chapters": len(chapters),
            "volumes": len(volume_titles),
            "cover_available": cover_path is not None,
            "samples": [
                {
                    "title": sample["title"],
                    "body_preview": sample["body_preview"],
                }
                for sample in samples
            ],
        }
        manifest = {
            **preview,
            "cover_path": cover_path,
            "volume_titles": {str(key): value for key, value in volume_titles.items()},
            "chapters_data": chapters,
            "images": image_paths,
        }
        (prepared_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return manifest


class EpubImportService:
    def __init__(self) -> None:
        self._commit_lock = Lock()

    def _session_dir(self, session_id: str) -> Path:
        return ctx.files.resolve(Path("tmp") / "imports" / session_id)

    def _staging_path(self, session_id: str) -> str:
        return str(Path("tmp") / "imports" / session_id / "upload.epub")

    def _delete_staging(self, session_id: str) -> None:
        directory = self._session_dir(session_id)
        if not directory.exists():
            return
        try:
            shutil.rmtree(directory)
        except OSError:
            logger.warning("Failed to remove EPUB staging directory %s", directory, exc_info=True)

    @staticmethod
    def _delete_directory(directory: Path) -> None:
        if not directory.exists():
            return
        try:
            shutil.rmtree(directory)
        except OSError:
            logger.warning("Failed to remove EPUB directory %s", directory, exc_info=True)

    async def start_upload(self, user: Any, upload: UploadFile) -> Dict[str, Any]:
        filename = Path(str(upload.filename or "")).name
        if not filename.lower().endswith(".epub"):
            raise ServerErrors.invalid_input.with_extra("仅支持 EPUB 文件")

        session_id = generate_uuid()
        directory = self._session_dir(session_id)
        digest = sha256()
        size = 0
        try:
            directory.mkdir(parents=True, exist_ok=False)
            path = directory / "upload.epub"
            with path.open("wb") as output:
                while True:
                    chunk = await upload.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise ServerErrors.invalid_input.with_extra("EPUB 文件不能超过 100 MB")
                    digest.update(chunk)
                    output.write(chunk)
            if size < 4:
                raise ServerErrors.invalid_input.with_extra("文件内容不是有效的 EPUB")
            existing = self.find_imported_novel(digest.hexdigest())
            if existing:
                self._delete_staging(session_id)
                return {
                    "session_id": None,
                    "job_id": None,
                    "existing_novel_id": existing.id,
                }

            now = current_timestamp()
            with ctx.db.session() as sess:
                session = ImportSession(
                    id=session_id,
                    user_id=user.id,
                    file_sha256=digest.hexdigest(),
                    original_name=filename,
                    file_size=size,
                    staging_path=self._staging_path(session_id),
                    status="analyzing",
                    expires_at=now + SESSION_TTL_MS,
                )
                sess.add(session)
                sess.commit()
            try:
                job = ctx.jobs.import_epub_analysis(user, session_id, filename)
                if not self.attach_job(
                    session_id,
                    analyze_job_id=job.id,
                    expected_status="analyzing",
                ):
                    ctx.scheduler.stop_job(job.id)
                    ctx.jobs.cancel(job.id)
                    raise ServerErrors.invalid_input.with_extra("该 EPUB 导入已取消")
            except Exception:
                self.delete_session(session_id)
                raise
            return {"session_id": session_id, "job_id": job.id, "existing_novel_id": None}
        except Exception:
            if self._session_dir(session_id).exists():
                self._delete_staging(session_id)
            raise
        finally:
            await upload.close()

    def find_imported_novel(self, file_sha256: str) -> Optional[Novel]:
        url = f"{IMPORT_URL_PREFIX}{file_sha256}"
        return ctx.novels.find_by_url(url)

    def get_session(self, session_id: str, user: Any) -> ImportSession:
        with ctx.db.session() as sess:
            session = sess.get(ImportSession, session_id)
            if not session:
                raise ServerErrors.no_such_file
            if session.user_id != user.id and not user.is_admin:
                raise ServerErrors.forbidden
            return session

    def attach_job(
        self,
        session_id: str,
        *,
        analyze_job_id: Optional[str] = None,
        commit_job_id: Optional[str] = None,
        expected_status: Optional[str] = None,
    ) -> bool:
        if not analyze_job_id and not commit_job_id:
            return False
        values: Dict[str, Any] = {"updated_at": current_timestamp()}
        conditions: List[Any] = [sq.col(ImportSession.id) == session_id]
        if expected_status is not None:
            conditions.append(sq.col(ImportSession.status) == expected_status)
        if analyze_job_id:
            values["analyze_job_id"] = analyze_job_id
            conditions.append(sq.col(ImportSession.analyze_job_id).is_(None))
        if commit_job_id:
            values["commit_job_id"] = commit_job_id
            conditions.append(sq.col(ImportSession.commit_job_id).is_(None))
        with ctx.db.session() as sess:
            result = sess.exec(sq.update(ImportSession).where(*conditions).values(**values))
            if result.rowcount != 1:
                return False
            sess.commit()
        return True

    def _transition_session(
        self,
        session_id: str,
        expected_statuses: Iterable[str],
        **values: Any,
    ) -> bool:
        values["updated_at"] = current_timestamp()
        with ctx.db.session() as sess:
            result = sess.exec(
                sq.update(ImportSession)
                .where(
                    sq.col(ImportSession.id) == session_id,
                    sq.col(ImportSession.status).in_(list(expected_statuses)),
                )
                .values(**values)
            )
            if result.rowcount != 1:
                return False
            sess.commit()
        return True

    def fail_session(self, session_id: str, message: str) -> None:
        self._transition_session(
            session_id,
            _ACTIVE_SESSION_STATUSES,
            status="failed",
            error=message,
        )
        self._delete_staging(session_id)

    def cancel_by_job(self, session_id: str) -> None:
        self._transition_session(
            session_id,
            _ACTIVE_SESSION_STATUSES,
            status="canceled",
            error=None,
        )
        self._delete_staging(session_id)

    def cancel_for_job(self, job_id: str, user: Any) -> None:
        job = ctx.jobs.get(job_id)
        if job.is_done:
            return
        session_id = job.extra.get("import_session_id")
        if not session_id:
            raise ServerErrors.invalid_input.with_extra("无效的 EPUB 导入任务")
        self.cancel(str(session_id), user)

    def delete_session(self, session_id: str) -> None:
        self._delete_staging(session_id)
        with ctx.db.session() as sess:
            session = sess.get(ImportSession, session_id)
            if session:
                sess.delete(session)
                sess.commit()

    def analyze_session(
        self,
        session_id: str,
        signal: Event,
        on_phase: Callable[[str], None],
    ) -> None:
        session = self._get_by_id(session_id)
        if session.status != "analyzing":
            raise AbortedException()
        path = ctx.files.resolve(session.staging_path)
        if not path.is_file():
            raise EpubImportError(
                "The uploaded EPUB staging file is missing.",
                "找不到待分析的 EPUB 文件。",
            )
        prepared_dir = self._session_dir(session_id) / "prepared"
        manifest = EpubParser().analyze(path, prepared_dir, signal, on_phase)
        _check_cancel(signal)
        if not self._transition_session(
            session_id,
            {"analyzing"},
            status="ready",
            preview=manifest,
            error=None,
        ):
            raise AbortedException()

    def _get_by_id(self, session_id: str) -> ImportSession:
        with ctx.db.session() as sess:
            session = sess.get(ImportSession, session_id)
            if not session:
                raise EpubImportError("Import session was not found.")
            return session

    def session_view(self, session_id: str, user: Any) -> Dict[str, Any]:
        session = self.get_session(session_id, user)
        job: Optional[Job] = None
        with ctx.db.session() as sess:
            job_id = session.commit_job_id or session.analyze_job_id
            if job_id:
                job = sess.get(Job, job_id)
        if job:
            progress = job.progress
            job_status = job.status
            phase = job.extra.get("phase")
        else:
            progress = 100 if session.status in ("ready", "completed") else 0
            job_status = None
            phase = None
        return {
            "id": session.id,
            "status": session.status,
            "original_name": session.original_name,
            "file_size": session.file_size,
            "expires_at": session.expires_at,
            "analyze_job_id": session.analyze_job_id,
            "commit_job_id": session.commit_job_id,
            "novel_id": session.novel_id,
            "job_status": job_status,
            "progress": progress,
            "phase": phase,
            "error": session.error,
            "preview": session.preview or None,
        }

    def claim_commit(self, session_id: str, user: Any, title: str, authors: str) -> Job:
        session = self.get_session(session_id, user)
        if session.status != "ready":
            raise ServerErrors.invalid_input.with_extra("该 EPUB 当前不能导入")
        title = title.strip() or str(session.preview.get("title") or "").strip()
        authors = authors.strip() or str(session.preview.get("authors") or "").strip()
        if not title:
            raise ServerErrors.invalid_input.with_extra("小说标题不能为空")
        with ctx.db.session() as sess:
            result = sess.exec(
                sq.update(ImportSession)
                .where(
                    sq.col(ImportSession.id) == session_id,
                    sq.col(ImportSession.status) == "ready",
                )
                .values(
                    status="committing",
                    error=None,
                    updated_at=current_timestamp(),
                )
            )
            if result.rowcount != 1:
                raise ServerErrors.invalid_input.with_extra("该 EPUB 当前不能导入")
            sess.commit()
        try:
            job = ctx.jobs.import_epub_commit(user, session_id, title, authors)
            if not self.attach_job(
                session_id,
                commit_job_id=job.id,
                expected_status="committing",
            ):
                ctx.scheduler.stop_job(job.id)
                ctx.jobs.cancel(job.id)
                raise ServerErrors.invalid_input.with_extra("该 EPUB 导入已取消")
            return job
        except Exception:
            self._transition_session(
                session_id,
                {"committing"},
                status="ready",
                error=None,
            )
            raise

    def cancel(self, session_id: str, user: Any) -> None:
        self.get_session(session_id, user)
        if not self._transition_session(
            session_id,
            _ACTIVE_SESSION_STATUSES,
            status="canceled",
            error=None,
        ):
            return
        current = self._get_by_id(session_id)
        job_ids = {job_id for job_id in (current.analyze_job_id, current.commit_job_id) if job_id}
        for job_id in job_ids:
            ctx.scheduler.stop_job(job_id)
            with ctx.db.session() as sess:
                exists = sess.get(Job, job_id)
            if exists and not exists.is_done:
                ctx.jobs.cancel(job_id)
        self._delete_staging(session_id)

    def commit_session(
        self,
        session_id: str,
        title: str,
        authors: str,
        signal: Event,
    ) -> str:
        while not self._commit_lock.acquire(timeout=0.25):
            _check_cancel(signal)
        try:
            return self._commit_session(session_id, title, authors, signal)
        finally:
            self._commit_lock.release()

    def _reserve_novel_id(self, session_id: str) -> str:
        novel_id = generate_uuid()
        with ctx.db.session() as sess:
            result = sess.exec(
                sq.update(ImportSession)
                .where(
                    sq.col(ImportSession.id) == session_id,
                    sq.col(ImportSession.status) == "committing",
                    sq.col(ImportSession.novel_id).is_(None),
                )
                .values(
                    novel_id=novel_id,
                    updated_at=current_timestamp(),
                )
            )
            if result.rowcount == 1:
                sess.commit()
                return novel_id

            current = sess.get(ImportSession, session_id)
            if current and current.status == "committing" and current.novel_id:
                return current.novel_id
        raise AbortedException()

    def _commit_session(
        self,
        session_id: str,
        title: str,
        authors: str,
        signal: Event,
    ) -> str:
        session = self._get_by_id(session_id)
        if session.status == "completed" and session.novel_id:
            return session.novel_id
        if session.status != "committing":
            if session.status in {"canceled", "expired"}:
                raise AbortedException()
            raise EpubImportError("Import session is not ready to commit.")
        prepared_dir = self._session_dir(session_id) / "prepared"
        manifest_path = prepared_dir / "manifest.json"
        if not manifest_path.is_file():
            raise EpubImportError("The prepared EPUB manifest is missing.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        title = title.strip() or str(manifest.get("title") or "").strip()
        authors = authors.strip() or str(manifest.get("authors") or "").strip()
        if not title:
            raise EpubImportError("The imported novel has no title.", "小说标题不能为空")
        existing = self.find_imported_novel(session.file_sha256)
        if existing:
            if not self._transition_session(
                session_id,
                {"committing"},
                status="completed",
                novel_id=existing.id,
                staging_path="",
                error=None,
                expires_at=current_timestamp() + SESSION_TTL_MS,
            ):
                raise AbortedException()
            self._delete_staging(session_id)
            return existing.id

        novel_id = session.novel_id or self._reserve_novel_id(session_id)
        novel_url = f"{IMPORT_URL_PREFIX}{session.file_sha256}"
        final_dir = ctx.files.resolve(f"novels/{novel_id}")
        if final_dir.exists():
            marker = final_dir / _PENDING_NOVEL_MARKER
            if marker.is_file():
                self._delete_directory(final_dir)
            else:
                raise EpubImportError("The destination novel directory already exists.")
        try:
            final_dir.mkdir(parents=True)
            (final_dir / _PENDING_NOVEL_MARKER).write_text(session_id, encoding="utf-8")
            cover_path = manifest.get("cover_path")
            if cover_path:
                shutil.copy2(prepared_dir / cover_path, final_dir / "cover.jpg")
            image_records = manifest.get("images") or {}
            image_paths_by_id = {
                Path(str(relative)).stem: str(relative) for relative in image_records.values()
            }

            volume_titles = {
                int(serial): str(volume_title)
                for serial, volume_title in (manifest.get("volume_titles") or {}).items()
            }
            volumes = {
                serial: Volume(
                    id=generate_uuid(),
                    novel_id=novel_id,
                    serial=serial,
                    title=volume_titles.get(serial, f"第 {serial} 卷"),
                    chapter_count=0,
                )
                for serial in sorted(volume_titles)
            }
            chapters: List[Chapter] = []
            images: List[ChapterImage] = []
            for item in manifest.get("chapters_data") or []:
                _check_cancel(signal)
                serial = int(item["serial"])
                chapter = Chapter(
                    id=generate_uuid(),
                    novel_id=novel_id,
                    serial=serial,
                    volume_id=volumes[int(item["volume"])].id,
                    url=f"{novel_url}#chapter-{serial}",
                    title=str(item["title"]),
                    is_done=True,
                    extra={"imported": True, "source_format": "epub"},
                )
                body = (prepared_dir / str(item["body_path"])).read_text(encoding="utf-8")
                for image_id in item.get("images") or []:
                    stored_image_id = sha256(f"{chapter.id}:{image_id}".encode()).hexdigest()[:32]
                    body = body.replace(
                        f"images/{image_id}.jpg",
                        f"images/{stored_image_id}.jpg",
                    )
                ctx.files.save_text(chapter.content_file, body)
                chapters.append(chapter)
                volumes[int(item["volume"])].chapter_count += 1
                for image_id in item.get("images") or []:
                    stored_image_id = sha256(f"{chapter.id}:{image_id}".encode()).hexdigest()[:32]
                    source_relative = image_paths_by_id.get(image_id)
                    if source_relative is None:
                        raise EpubImportError("A prepared EPUB image is missing.")
                    source = prepared_dir / source_relative
                    target = final_dir / "images" / f"{stored_image_id}.jpg"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    images.append(
                        ChapterImage(
                            id=stored_image_id,
                            novel_id=novel_id,
                            chapter_id=chapter.id,
                            url=f"{novel_url}#image-{stored_image_id}",
                            is_done=True,
                            extra={"imported": True},
                        )
                    )

            novel = Novel(
                id=novel_id,
                domain=IMPORT_DOMAIN,
                url=novel_url,
                title=title,
                authors=authors or None,
                synopsis=str(manifest.get("synopsis") or ""),
                tags=list(manifest.get("tags") or []),
                cover_url="",
                language=manifest.get("language"),
                volume_count=len(volumes),
                chapter_count=len(chapters),
                extra={
                    "imported": True,
                    "source_format": "epub",
                    "original_name": session.original_name,
                    "file_sha256": session.file_sha256,
                    "imported_at": current_timestamp(),
                },
            )

            _check_cancel(signal)
            with ctx.db.session() as sess:
                current_session = sess.get(ImportSession, session_id)
                if current_session is None:
                    raise EpubImportError("Import session was removed while committing.")
                if current_session.status != "committing":
                    raise AbortedException()
                if current_session.novel_id != novel_id:
                    raise EpubImportError("Import session target changed while committing.")
                sess.add(novel)
                sess.add_all(volumes.values())
                sess.add_all(chapters)
                sess.add_all(images)
                current_session.status = "completed"
                current_session.novel_id = novel_id
                current_session.staging_path = ""
                current_session.error = None
                current_session.expires_at = current_timestamp() + SESSION_TTL_MS
                sess.add(current_session)
                sess.commit()
            try:
                (final_dir / _PENDING_NOVEL_MARKER).unlink(missing_ok=True)
            except OSError:
                logger.warning(
                    "Failed to remove EPUB pending marker for imported novel %s",
                    novel_id,
                    exc_info=True,
                )
            try:
                ctx.recommendations.index_add(novel.id, novel.title)
                if novel.tags:
                    ctx.tags.set_novel_tags(novel.id, novel.tags)
            except Exception:
                logger.warning("Failed to update optional indexes for imported novel %s", novel.id)
            self._delete_staging(session_id)
            return novel_id
        except Exception:
            if final_dir.exists():
                self._delete_directory(final_dir)
            raise

    def _reconcile_novel_directories(self, now: int) -> None:
        root = ctx.files.resolve("novels")
        if not root.is_dir():
            return
        try:
            directories = [item for item in root.iterdir() if item.is_dir()]
        except OSError:
            logger.warning("Failed to scan EPUB novel directories", exc_info=True)
            return
        if not directories:
            return

        with ctx.db.session() as sess:
            sessions = list(sess.exec(sq.select(ImportSession)).all())
            sessions_by_novel_id = {
                session.novel_id: session for session in sessions if session.novel_id
            }
            candidate_ids = {
                directory.name
                for directory in directories
                if directory.name in sessions_by_novel_id
                or (directory / _PENDING_NOVEL_MARKER).is_file()
            }
            novel_ids = set()
            if candidate_ids:
                novel_ids = set(
                    sess.exec(sq.select(Novel.id).where(sq.col(Novel.id).in_(candidate_ids))).all()
                )
            job_ids = {
                job_id
                for session in sessions
                for job_id in (session.analyze_job_id, session.commit_job_id)
                if job_id
            }
            active_job_ids = {
                job.id
                for job in sess.exec(sq.select(Job).where(sq.col(Job.id).in_(job_ids))).all()
                if not job.is_done
            }

        for directory in directories:
            if directory.name not in candidate_ids:
                continue
            session = sessions_by_novel_id.get(directory.name)
            if (
                session
                and session.status in _ACTIVE_SESSION_STATUSES
                and (
                    session.expires_at >= now
                    or session.analyze_job_id in active_job_ids
                    or session.commit_job_id in active_job_ids
                )
            ):
                continue
            if session and session.status == "completed" and directory.name in novel_ids:
                try:
                    (directory / _PENDING_NOVEL_MARKER).unlink(missing_ok=True)
                except OSError:
                    logger.warning(
                        "Failed to remove EPUB pending marker for imported novel %s",
                        directory.name,
                        exc_info=True,
                    )
                continue
            self._delete_directory(directory)

    def _cleanup_orphaned_staging(self, tracked_session_ids: set[str], now: int) -> None:
        root = ctx.files.resolve(Path("tmp") / "imports")
        if not root.is_dir():
            return
        try:
            directories = [item for item in root.iterdir() if item.is_dir()]
        except OSError:
            logger.warning("Failed to scan EPUB staging directories", exc_info=True)
            return
        cutoff = now - SESSION_TTL_MS
        for directory in directories:
            if directory.name in tracked_session_ids:
                continue
            try:
                is_old = int(directory.stat().st_mtime * 1000) < cutoff
            except OSError:
                continue
            if is_old:
                self._delete_directory(directory)

    def cleanup_expired(self) -> None:
        now = current_timestamp()
        jobs_to_cancel: set[str] = set()
        staging_to_delete: set[str] = set()
        with ctx.db.session() as sess:
            sessions = list(sess.exec(sq.select(ImportSession)).all())
            tracked_session_ids = {session.id for session in sessions}
            for session in sessions:
                if session.expires_at >= now:
                    continue
                job_ids = {
                    job_id for job_id in (session.analyze_job_id, session.commit_job_id) if job_id
                }
                active_job_ids = {
                    job.id
                    for job in sess.exec(sq.select(Job).where(sq.col(Job.id).in_(job_ids))).all()
                    if not job.is_done
                }
                if session.status in _ACTIVE_SESSION_STATUSES and active_job_ids:
                    continue
                staging_to_delete.add(session.id)
                if session.status in _ACTIVE_SESSION_STATUSES:
                    session.status = "expired"
                    session.error = "导入会话已过期"
                    session.staging_path = ""
                    session.expires_at = now + SESSION_RETENTION_MS
                    session.updated_at = now
                    sess.add(session)
                    jobs_to_cancel.update(active_job_ids)
                else:
                    sess.delete(session)
                    tracked_session_ids.discard(session.id)
            sess.commit()

        for job_id in jobs_to_cancel:
            ctx.scheduler.stop_job(job_id)
            ctx.jobs.cancel(job_id)
        for session_id in staging_to_delete:
            self._delete_staging(session_id)
        self._reconcile_novel_directories(now)
        self._cleanup_orphaned_staging(tracked_session_ids, now)
