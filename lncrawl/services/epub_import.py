from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import html
import io
import json
import logging
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
from threading import Event, Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple
import unicodedata
from urllib.parse import unquote, urlsplit
import zipfile

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
from .imports.progress import ImportProgressCallback, map_progress

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
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
MAX_PUBLIC_PREVIEW_BYTES = 32 * 1024
MAX_PREVIEW_WARNINGS = 20
_REJECTED_MEDIA_PREFIXES = ("audio/", "video/")
_REJECTED_MEDIA_TYPES = {
    "application/smil+xml",
    "application/javascript",
    "text/javascript",
}
_REJECTED_EXTENSIONS = {
    ".aac",
    ".avi",
    ".flac",
    ".js",
    ".m4a",
    ".m4v",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".smil",
    ".wav",
    ".webm",
}
_REJECTED_MARKUP_TAGS = {
    "audio",
    "video",
    "source",
    "track",
    "script",
    "object",
    "embed",
    "iframe",
}
_SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

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


def _normalize_heading(text: str) -> str:
    decoded = html.unescape(text)
    normalized = unicodedata.normalize("NFC", decoded)
    return " ".join(normalized.split())


def _leading_title_cleanup(root: Any, expected_title: str) -> Tuple[Any, Any]:
    from bs4 import Comment
    from bs4.element import NavigableString, Tag

    heading = root.find(["h1", "h2", "h3"])
    if heading is None or _normalize_heading(
        heading.get_text(" ", strip=True)
    ) != _normalize_heading(expected_title):
        return None, None

    marker = None
    for sibling in heading.previous_siblings:
        if isinstance(sibling, Comment):
            continue
        if isinstance(sibling, NavigableString) and not str(sibling).strip():
            continue
        if isinstance(sibling, Tag) and marker is None:
            hidden = str(sibling.get("aria-hidden") or "").lower()
            text = sibling.get_text(" ", strip=True)
            if hidden in {"true", "1"} and re.fullmatch(r"#\s*\d+", text):
                marker = sibling
                continue
        return None, None

    current = heading.parent
    while current is not None and current is not root:
        for sibling in current.previous_siblings:
            if isinstance(sibling, Comment):
                continue
            if isinstance(sibling, NavigableString) and not str(sibling).strip():
                continue
            return None, None
        current = current.parent
    if current is not root:
        return None, None
    return heading, marker


def _clean_html(
    raw: bytes,
    item_name: str,
    archive: zipfile.ZipFile,
    image_items: Dict[str, str],
    image_paths: Dict[str, str],
    prepared_images: Path,
    expected_title: str = "",
    strip_leading_title: bool = False,
    strip_leading_marker: bool = False,
) -> Tuple[str, List[str]]:
    from bs4 import BeautifulSoup, Comment

    soup = BeautifulSoup(raw, "html.parser")
    root = soup.body or soup
    used_images: List[str] = []
    if strip_leading_title:
        heading, marker = _leading_title_cleanup(root, expected_title)
        if heading is not None:
            heading.decompose()
            if strip_leading_marker and marker is not None:
                marker.decompose()
    for comment in root.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for tag in list(root.find_all(_REMOVE_TAGS)):
        tag.decompose()

    for svg in list(root.find_all("svg")):
        image = svg.find("image")
        href = str((image.get("href") or image.get("xlink:href") or "") if image else "").strip()
        replacement = soup.new_tag("img")
        replacement["src"] = href
        svg.replace_with(replacement)

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
            media_type = image_items[resource_name]
            if media_type == "image/svg+xml":
                svg_root = _parse_xml(_read_zip_entry(archive, resource_name, MAX_XML_BYTES))
                references = []
                for element in svg_root.iter():
                    if _local_name(element.tag).lower() != "image":
                        continue
                    href = str(
                        element.attrib.get("href")
                        or element.attrib.get("{http://www.w3.org/1999/xlink}href")
                        or ""
                    ).strip()
                    matched = _match_name(
                        href,
                        image_items.keys(),
                        posixpath.dirname(resource_name),
                    )
                    if matched and image_items.get(matched) in _SUPPORTED_IMAGE_TYPES:
                        references.append(matched)
                references = list(dict.fromkeys(references))
                if len(references) != 1:
                    tag.decompose()
                    continue
                resource_name = references[0]
            if resource_name not in image_paths:
                converted = _image_jpeg(_read_zip_entry(archive, resource_name, MAX_IMAGE_BYTES))
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


def _read_zip_entry(
    archive: zipfile.ZipFile,
    name: str,
    limit: int,
) -> bytes:
    info = archive.getinfo(name)
    if info.file_size > limit:
        raise EpubImportError(f"EPUB entry exceeds its read limit: {name}")
    chunks: List[bytes] = []
    total = 0
    with archive.open(info) as stream:
        while True:
            chunk = stream.read(min(_CHUNK_SIZE, limit - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise EpubImportError(f"EPUB entry exceeds its read limit: {name}")
            chunks.append(chunk)
    return b"".join(chunks)


def _opf_values(root: Any, local_name: str) -> List[str]:
    values: List[str] = []
    for element in root.iter():
        if _local_name(element.tag).lower() != local_name.lower():
            continue
        value = " ".join(str(element.text or "").split())
        if value:
            values.append(value)
    return values


def _nav_toc(
    archive: zipfile.ZipFile,
    nav_name: str,
    names: set[str],
) -> Dict[str, _TocEntry]:
    from bs4 import BeautifulSoup

    raw = _read_zip_entry(archive, nav_name, MAX_CHAPTER_BYTES)
    soup = BeautifulSoup(raw, "html.parser")
    nav = next(
        (
            item
            for item in soup.find_all("nav")
            if "toc" in str(item.get("epub:type") or item.get("type") or "").lower().split()
        ),
        None,
    )
    nav = nav or soup.find("nav")
    if nav is None:
        return {}

    result: Dict[str, _TocEntry] = {}
    base_dir = posixpath.dirname(nav_name)

    def walk(list_tag: Any, volume: Optional[str] = None) -> None:
        for item in list_tag.find_all("li", recursive=False):
            link = item.find("a", recursive=False)
            nested = item.find(["ol", "ul"], recursive=False)
            title = link.get_text(" ", strip=True) if link else ""
            if nested is not None:
                walk(nested, title or volume)
                continue
            href = str(link.get("href") or "") if link else ""
            matched = _match_name(href, names, base_dir)
            if matched and matched not in result:
                result[matched] = _TocEntry(
                    href=href,
                    title=title,
                    volume=volume,
                )

    root_list = nav.find(["ol", "ul"])
    if root_list is not None:
        walk(root_list)
    return result


def _ncx_toc(
    archive: zipfile.ZipFile,
    ncx_name: str,
    names: set[str],
) -> Dict[str, _TocEntry]:
    root = _parse_xml(
        _read_zip_entry(archive, ncx_name, MAX_XML_BYTES),
        allow_doctype=True,
    )
    result: Dict[str, _TocEntry] = {}
    base_dir = posixpath.dirname(ncx_name)

    def children(node: Any, name: str) -> List[Any]:
        return [child for child in node if _local_name(child.tag) == name]

    def label(node: Any) -> str:
        for nav_label in children(node, "navLabel"):
            for text_node in nav_label.iter():
                if _local_name(text_node.tag) == "text":
                    return " ".join(str(text_node.text or "").split())
        return ""

    def walk(node: Any, volume: Optional[str] = None) -> None:
        for point in children(node, "navPoint"):
            title = label(point)
            nested = children(point, "navPoint")
            if nested:
                walk(point, title or volume)
                continue
            content = next(iter(children(point, "content")), None)
            href = str(content.attrib.get("src") or "") if content is not None else ""
            matched = _match_name(href, names, base_dir)
            if matched and matched not in result:
                result[matched] = _TocEntry(
                    href=href,
                    title=title,
                    volume=volume,
                )

    nav_map = next(
        (element for element in root.iter() if _local_name(element.tag) == "navMap"),
        None,
    )
    if nav_map is not None:
        walk(nav_map)
    return result


def _package_index(
    archive: zipfile.ZipFile,
    names: set[str],
    opf_path: str,
) -> Dict[str, Any]:
    opf = _parse_xml(_read_zip_entry(archive, opf_path, MAX_XML_BYTES))
    opf_dir = posixpath.dirname(opf_path)
    items: Dict[str, Dict[str, Any]] = {}
    for element in opf.iter():
        if _local_name(element.tag) != "item":
            continue
        item_id = str(element.attrib.get("id") or "")
        href = str(element.attrib.get("href") or "")
        if not item_id or not href:
            continue
        archive_name = _match_name(href, names, opf_dir)
        if archive_name is None:
            continue
        media_type = str(element.attrib.get("media-type") or "").lower()
        suffix = Path(archive_name).suffix.lower()
        if media_type.startswith(_REJECTED_MEDIA_PREFIXES) or suffix in {
            ".aac",
            ".avi",
            ".flac",
            ".m4a",
            ".m4v",
            ".mov",
            ".mp3",
            ".mp4",
            ".ogg",
            ".wav",
            ".webm",
        }:
            raise EpubImportError(
                "EPUB contains audio or video resources.",
                "EPUB 包含音频或视频内容，仅支持文字和静态插图。",
            )
        if media_type in _REJECTED_MEDIA_TYPES or suffix in {".js", ".smil"}:
            raise EpubImportError(
                "EPUB contains scripted or interactive resources.",
                "EPUB 包含脚本或交互内容，无法安全导入。",
            )
        if element.attrib.get("media-overlay"):
            raise EpubImportError(
                "EPUB contains a media overlay.",
                "EPUB 包含音频或视频内容，仅支持文字和静态插图。",
            )
        items[item_id] = {
            "archive_name": archive_name,
            "media_type": media_type,
            "properties": sorted(set(str(element.attrib.get("properties") or "").split())),
        }

    spine = next(
        (element for element in opf.iter() if _local_name(element.tag) == "spine"),
        None,
    )
    if spine is None:
        raise EpubImportError("EPUB package has no spine.", "这个 EPUB 没有可读章节。")
    spine_ids: List[str] = []
    for itemref in spine:
        if _local_name(itemref.tag) != "itemref":
            continue
        if str(itemref.attrib.get("linear") or "yes").lower() == "no":
            continue
        item_id = str(itemref.attrib.get("idref") or "")
        item = items.get(item_id)
        if item is None or "nav" in item["properties"]:
            continue
        if item["media_type"] not in {"application/xhtml+xml", "text/html"}:
            continue
        spine_ids.append(item_id)

    nav_item = next(
        (item for item in items.values() if "nav" in item["properties"]),
        None,
    )
    toc_by_name: Dict[str, _TocEntry] = {}
    if nav_item is not None:
        toc_by_name = _nav_toc(archive, nav_item["archive_name"], names)
    if not toc_by_name:
        toc_id = str(spine.attrib.get("toc") or "")
        toc_item = items.get(toc_id)
        if toc_item is not None:
            toc_by_name = _ncx_toc(archive, toc_item["archive_name"], names)

    return {
        "metadata": {
            "title": (_opf_values(opf, "title") or [""])[0],
            "authors": ", ".join(_opf_values(opf, "creator")),
            "language": _normalize_language((_opf_values(opf, "language") or [""])[0]),
            "descriptions": _opf_values(opf, "description"),
            "tags": _opf_values(opf, "subject")[:50],
        },
        "items": items,
        "spine_ids": spine_ids,
        "toc_by_name": toc_by_name,
    }


class EpubParser:
    def analyze(
        self,
        source_path: Path,
        prepared_dir: Path,
        signal: Event,
        on_progress: ImportProgressCallback,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        prepared_dir.mkdir(parents=True, exist_ok=True)

        on_progress("校验 EPUB 文件", 1)
        names, opf_path = _validate_archive(source_path)
        _check_cancel(signal)

        on_progress("读取书籍信息和目录", 5)
        with zipfile.ZipFile(source_path) as archive:
            package = _package_index(archive, names, opf_path)
            metadata = package["metadata"]
            items = package["items"]
            toc_by_name = package["toc_by_name"]
            spine_names = [items[item_id]["archive_name"] for item_id in package["spine_ids"]]
            if not spine_names:
                raise EpubImportError(
                    "EPUB has no readable spine documents.",
                    "这个 EPUB 没有可读章节。",
                )

            image_items = {
                item["archive_name"]: item["media_type"]
                for item in items.values()
                if item["media_type"] in _SUPPORTED_IMAGE_TYPES
                or item["media_type"] == "image/svg+xml"
            }
            svg_count = sum(
                1 for media_type in image_items.values() if media_type == "image/svg+xml"
            )
            warnings: List[str] = []
            if svg_count:
                warnings.append(f"检测到 {svg_count} 个 SVG 插图；仅导入引用普通位图的安全外壳。")

            cover_name = _cover_name(source_path, set(names))
            title = str(metadata["title"] or "") or source_path.stem
            authors = str(metadata["authors"] or "")
            language = metadata["language"]
            descriptions = metadata["descriptions"]
            tags = metadata["tags"]
            synopsis = f"<p>{html.escape(str(descriptions[0]))}</p>" if descriptions else ""

            on_progress("预检查正文内容", 10)
            sample_indices = {0, len(spine_names) // 2, len(spine_names) - 1}
            sample_text: Dict[str, str] = {}
            headings: Dict[str, str] = {}
            cleanup_flags: Dict[str, Tuple[bool, bool]] = {}
            readable: List[str] = []
            from bs4 import BeautifulSoup

            total_spine = len(spine_names)
            for index, item_name in enumerate(spine_names, 1):
                _check_cancel(signal)
                on_progress(
                    f"正在预检查正文 {index} / {total_spine}",
                    map_progress(10, 85, index, total_spine),
                )
                raw = _read_zip_entry(archive, item_name, MAX_CHAPTER_BYTES)
                soup = BeautifulSoup(raw, "html.parser")
                root = soup.body or soup
                dangerous = root.find(list(_REJECTED_MARKUP_TAGS))
                if dangerous is not None:
                    tag_name = str(dangerous.name or "").lower()
                    if tag_name in {"audio", "video", "source", "track"}:
                        raise EpubImportError(
                            f"EPUB chapter contains a {tag_name} element.",
                            "EPUB 包含音频或视频内容，仅支持文字和静态插图。",
                        )
                    raise EpubImportError(
                        f"EPUB chapter contains a {tag_name} element.",
                        "EPUB 包含脚本或交互内容，无法安全导入。",
                    )
                heading_tag = root.find(["h1", "h2", "h3"])
                if heading_tag:
                    headings[item_name] = heading_tag.get_text(" ", strip=True)
                toc = toc_by_name.get(item_name)
                expected_title = (toc.title if toc else "") or headings.get(item_name, "")
                duplicate_heading, hidden_marker = _leading_title_cleanup(root, expected_title)
                cleanup_flags[item_name] = (
                    duplicate_heading is not None,
                    hidden_marker is not None,
                )
                if duplicate_heading is not None:
                    duplicate_heading.extract()
                    if hidden_marker is not None:
                        hidden_marker.extract()
                text = root.get_text(" ", strip=True)
                has_image = root.find(["img", "svg"]) is not None
                if text or has_image:
                    readable.append(item_name)
                    if index - 1 in sample_indices:
                        sample_text[item_name] = text[:240]

        on_progress("生成导入预览", 85)
        chapters: List[Dict[str, Any]] = []
        volume_numbers: Dict[str, int] = {}
        volume_titles: Dict[int, str] = {}
        for index, item_name in enumerate(readable, 1):
            _check_cancel(signal)
            on_progress(
                f"正在生成预览索引 {index} / {len(readable)}",
                map_progress(85, 95, index, len(readable)),
            )
            toc = toc_by_name.get(item_name)
            chapter_title = (toc.title if toc else "") or headings.get(item_name, "")
            chapter_title = chapter_title or f"第 {len(chapters) + 1} 章"
            volume_title = (toc.volume if toc else None) or "正文"
            if volume_title not in volume_numbers:
                volume_number = len(volume_numbers) + 1
                volume_numbers[volume_title] = volume_number
                volume_titles[volume_number] = volume_title
            volume_number = volume_numbers[volume_title]
            output_serial = len(chapters) + 1
            chapters.append(
                {
                    "stable_key": item_name,
                    "archive_name": item_name,
                    "title": chapter_title,
                    "serial": output_serial,
                    "volume": volume_number,
                    "volume_title": volume_title,
                    "body_preview": sample_text.get(item_name, ""),
                    "strip_leading_title": cleanup_flags.get(item_name, (False, False))[0],
                    "strip_leading_marker": cleanup_flags.get(item_name, (False, False))[1],
                }
            )

        if not chapters:
            raise EpubImportError(
                "EPUB has no non-empty chapter bodies.",
                "这个 EPUB 没有可读章节正文。",
            )

        duplicate_title_count = sum(bool(item["strip_leading_title"]) for item in chapters)
        if duplicate_title_count:
            warnings.append(
                f"检测到 {duplicate_title_count} 章正文重复包含章节标题，导入时将隐藏重复标题。"
            )

        sample_chapters = [
            chapters[0],
            chapters[len(chapters) // 2],
            chapters[-1],
        ]
        unique_samples: List[Dict[str, Any]] = []
        seen_samples: set[str] = set()
        for sample in sample_chapters:
            if sample["stable_key"] in seen_samples:
                continue
            seen_samples.add(sample["stable_key"])
            if not sample["body_preview"]:
                with zipfile.ZipFile(source_path) as archive:
                    raw = _read_zip_entry(
                        archive,
                        str(sample["archive_name"]),
                        MAX_CHAPTER_BYTES,
                    )
                from bs4 import BeautifulSoup

                sample["body_preview"] = BeautifulSoup(raw, "html.parser").get_text(
                    " ", strip=True
                )[:240]
            unique_samples.append(sample)
        preview = {
            "source_format": "epub",
            "title": title,
            "authors": authors,
            "language": language,
            "synopsis": synopsis,
            "tags": tags,
            "chapters": len(chapters),
            "volumes": len(volume_titles),
            "cover_available": cover_name in image_items,
            "illustrations": sum(
                1 for media_type in image_items.values() if media_type in _SUPPORTED_IMAGE_TYPES
            ),
            "warnings": warnings[:MAX_PREVIEW_WARNINGS],
            "samples": [
                {
                    "title": sample["title"],
                    "body_preview": sample["body_preview"],
                }
                for sample in unique_samples
            ],
        }
        manifest = {
            "schema_version": 1,
            "source_format": "epub",
            "title": title,
            "authors": authors,
            "language": language,
            "synopsis": synopsis,
            "tags": tags,
            "cover_resource": cover_name,
            "volume_titles": {str(key): value for key, value in volume_titles.items()},
            "chapters_data": chapters,
            "image_items": image_items,
        }
        (prepared_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        on_progress("保存分析结果", 99)
        return preview, manifest

    def prepare_commit(
        self,
        source_path: Path,
        prepared_dir: Path,
        manifest: Dict[str, Any],
        signal: Event,
        on_progress: ImportProgressCallback,
    ) -> Dict[str, Any]:
        prepared_images = prepared_dir / "images"
        prepared_chapters = prepared_dir / "chapters"
        prepared_images.mkdir(parents=True, exist_ok=True)
        prepared_chapters.mkdir(parents=True, exist_ok=True)
        image_items = {
            str(name): str(media_type)
            for name, media_type in (manifest.get("image_items") or {}).items()
        }
        image_paths: Dict[str, str] = {}
        chapters: List[Dict[str, Any]] = []
        volume_numbers: Dict[str, int] = {}
        volume_titles: Dict[int, str] = {}
        cover_path: Optional[str] = None

        with zipfile.ZipFile(source_path) as archive:
            cover_name = str(manifest.get("cover_resource") or "")
            if cover_name in image_items:
                if image_items[cover_name] == "image/svg+xml":
                    svg_root = _parse_xml(_read_zip_entry(archive, cover_name, MAX_XML_BYTES))
                    references: List[str] = []
                    for element in svg_root.iter():
                        if _local_name(element.tag).lower() != "image":
                            continue
                        href = str(
                            element.attrib.get("href")
                            or element.attrib.get("{http://www.w3.org/1999/xlink}href")
                            or ""
                        ).strip()
                        matched = _match_name(
                            href,
                            image_items.keys(),
                            posixpath.dirname(cover_name),
                        )
                        if matched and image_items.get(matched) in _SUPPORTED_IMAGE_TYPES:
                            references.append(matched)
                    references = list(dict.fromkeys(references))
                    cover_name = references[0] if len(references) == 1 else ""
                if cover_name:
                    converted_cover = _image_jpeg(
                        _read_zip_entry(archive, cover_name, MAX_IMAGE_BYTES)
                    )
                    if converted_cover is not None:
                        cover_path = "cover.jpg"
                        (prepared_dir / cover_path).write_bytes(converted_cover)

            source_chapters = manifest.get("chapters_data") or []
            for index, source_item in enumerate(source_chapters, 1):
                _check_cancel(signal)
                on_progress(
                    f"正在整理章节 {index} / {len(source_chapters)}",
                    map_progress(5, 50, index, len(source_chapters)),
                )
                item = dict(source_item)
                archive_name = str(item["archive_name"])
                raw = _read_zip_entry(archive, archive_name, MAX_CHAPTER_BYTES)
                body, used_images = _clean_html(
                    raw,
                    archive_name,
                    archive,
                    image_items,
                    image_paths,
                    prepared_images,
                    expected_title=str(item.get("title") or ""),
                    strip_leading_title=bool(item.get("strip_leading_title")),
                    strip_leading_marker=bool(item.get("strip_leading_marker")),
                )
                if not body:
                    continue
                volume_title = str(item.get("volume_title") or "正文")
                if volume_title not in volume_numbers:
                    volume_number = len(volume_numbers) + 1
                    volume_numbers[volume_title] = volume_number
                    volume_titles[volume_number] = volume_title
                serial = len(chapters) + 1
                body_path = f"chapters/{serial:06d}.html"
                (prepared_dir / body_path).write_text(body, encoding="utf-8")
                item.update(
                    serial=serial,
                    volume=volume_numbers[volume_title],
                    body_path=body_path,
                    images=used_images,
                )
                chapters.append(item)

        if not chapters:
            raise EpubImportError(
                "EPUB has no safe chapter bodies after sanitizing.",
                "这个 EPUB 清理后没有可导入的文字或插图。",
            )
        prepared = dict(manifest)
        prepared.update(
            cover_path=cover_path,
            images=image_paths,
            chapters_data=chapters,
            volume_titles={str(key): value for key, value in volume_titles.items()},
        )
        return prepared


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
                        raise ServerErrors.invalid_input.with_extra("EPUB 文件不能超过 50 MB")
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
                    source_format="epub",
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

    async def start_txt_upload(self, user: Any, upload: UploadFile) -> Dict[str, Any]:
        from .imports.txt import MAX_TXT_UPLOAD_BYTES

        filename = Path(str(upload.filename or "")).name
        if not filename.lower().endswith(".txt"):
            raise ServerErrors.invalid_input.with_extra("仅支持 TXT 文件")
        session_id = generate_uuid()
        directory = self._session_dir(session_id)
        digest = sha256()
        size = 0
        try:
            directory.mkdir(parents=True, exist_ok=False)
            path = directory / "upload.txt"
            with path.open("wb") as output:
                while True:
                    chunk = await upload.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_TXT_UPLOAD_BYTES:
                        raise ServerErrors.invalid_input.with_extra("TXT 文件不能超过 20 MB")
                    digest.update(chunk)
                    output.write(chunk)
            if not size:
                raise ServerErrors.invalid_input.with_extra("TXT 文件不能为空")
            existing = self.find_imported_novel(digest.hexdigest())
            if existing:
                self._delete_staging(session_id)
                return {
                    "session_id": None,
                    "job_id": None,
                    "existing_novel_id": existing.id,
                }
            now = current_timestamp()
            staging_path = str(Path("tmp") / "imports" / session_id / "upload.txt")
            with ctx.db.session() as sess:
                session = ImportSession(
                    id=session_id,
                    user_id=user.id,
                    file_sha256=digest.hexdigest(),
                    source_format="txt",
                    original_name=filename,
                    file_size=size,
                    staging_path=staging_path,
                    status="analyzing",
                    expires_at=now + SESSION_TTL_MS,
                )
                sess.add(session)
                sess.commit()
            job = ctx.jobs.import_txt_analysis(user, session_id, filename)
            if not self.attach_job(
                session_id,
                analyze_job_id=job.id,
                expected_status="analyzing",
            ):
                ctx.scheduler.stop_job(job.id)
                ctx.jobs.cancel(job.id)
                raise ServerErrors.invalid_input.with_extra("该 TXT 导入已取消")
            return {"session_id": session_id, "job_id": job.id, "existing_novel_id": None}
        except Exception:
            if self._session_dir(session_id).exists():
                self.delete_session(session_id)
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
        session = self._get_by_id(session_id)
        backup = self._session_dir(session_id) / "prepared-backup"
        if (session.source_format or "epub") == "txt" and backup.is_dir():
            prepared = self._session_dir(session_id) / "prepared"
            self._delete_directory(prepared)
            backup.replace(prepared)
            self._transition_session(
                session_id,
                {"analyzing"},
                status="ready",
                error=message,
            )
            return
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
        on_progress: ImportProgressCallback,
    ) -> None:
        session = self._get_by_id(session_id)
        if session.status != "analyzing":
            raise AbortedException()
        path = ctx.files.resolve(session.staging_path)
        if not path.is_file():
            raise EpubImportError("The uploaded staging file is missing.", "找不到待分析的文件。")
        prepared_dir = self._session_dir(session_id) / "prepared"
        if (session.source_format or "epub") == "txt":
            from .imports.txt import TxtAdapter

            options_path = self._session_dir(session_id) / "options.json"
            options = (
                json.loads(options_path.read_text(encoding="utf-8"))
                if options_path.is_file()
                else {}
            )
            preview, _manifest = TxtAdapter().analyze(
                path, prepared_dir, signal, on_progress, options
            )
        else:
            preview, _manifest = EpubParser().analyze(path, prepared_dir, signal, on_progress)
        _check_cancel(signal)
        if len(json.dumps(preview, ensure_ascii=False).encode("utf-8")) > MAX_PUBLIC_PREVIEW_BYTES:
            raise EpubImportError("The EPUB preview exceeds the supported size limit.")
        if not self._transition_session(
            session_id,
            {"analyzing"},
            status="ready",
            preview=preview,
            error=None,
        ):
            raise AbortedException()
        backup = self._session_dir(session_id) / "prepared-backup"
        self._delete_directory(backup)

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
            "source_format": session.source_format or "epub",
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
        source_format = session.source_format or "epub"
        if session.status != "ready":
            raise ServerErrors.invalid_input.with_extra("该文件当前不能导入")
        if source_format == "txt" and not bool(session.preview.get("can_commit", True)):
            raise ServerErrors.invalid_input.with_extra("请先确认 TXT 编码并更新预览")
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
                raise ServerErrors.invalid_input.with_extra("该文件当前不能导入")
            sess.commit()
        try:
            job = (
                ctx.jobs.import_txt_commit(user, session_id, title, authors)
                if source_format == "txt"
                else ctx.jobs.import_epub_commit(user, session_id, title, authors)
            )
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

    def reanalyze_txt(
        self,
        session_id: str,
        user: Any,
        options: Dict[str, Any],
    ) -> Job:
        session = self.get_session(session_id, user)
        if (session.source_format or "epub") != "txt" or session.status != "ready":
            raise ServerErrors.invalid_input.with_extra("该 TXT 当前不能重新分析")
        options_path = self._session_dir(session_id) / "options.json"
        options_path.write_text(json.dumps(options, ensure_ascii=False), encoding="utf-8")
        prepared = self._session_dir(session_id) / "prepared"
        backup = self._session_dir(session_id) / "prepared-backup"
        self._delete_directory(backup)
        if prepared.is_dir():
            prepared.replace(backup)
        with ctx.db.session() as sess:
            result = sess.exec(
                sq.update(ImportSession)
                .where(
                    sq.col(ImportSession.id) == session_id,
                    sq.col(ImportSession.status) == "ready",
                )
                .values(
                    status="analyzing",
                    analyze_job_id=None,
                    error=None,
                    updated_at=current_timestamp(),
                )
            )
            if result.rowcount != 1:
                if backup.is_dir():
                    backup.replace(prepared)
                raise ServerErrors.invalid_input.with_extra("该 TXT 当前不能重新分析")
            sess.commit()
        job = ctx.jobs.import_txt_analysis(user, session_id, session.original_name, options)
        if not self.attach_job(
            session_id,
            analyze_job_id=job.id,
            expected_status="analyzing",
        ):
            self._delete_directory(prepared)
            if backup.is_dir():
                backup.replace(prepared)
            self._transition_session(
                session_id,
                {"analyzing"},
                status="ready",
                error="TXT 重新分析任务未创建",
            )
            raise ServerErrors.invalid_input.with_extra("TXT 重新分析任务未创建")
        return job

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
        on_progress: ImportProgressCallback,
    ) -> str:
        while not self._commit_lock.acquire(timeout=0.25):
            _check_cancel(signal)
        try:
            return self._commit_session(session_id, title, authors, signal, on_progress)
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
        on_progress: ImportProgressCallback,
    ) -> str:
        session = self._get_by_id(session_id)
        on_progress("准备导入", 1)
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

        source_format = session.source_format or "epub"
        if source_format == "txt":
            from .imports.txt import TxtAdapter

            chapter_items: List[Dict[str, Any]] = []
            volume_numbers: Dict[str, int] = {}
            volume_titles: Dict[int, str] = {}
            source_chapters = manifest.get("chapters") or []
            for index, imported in enumerate(
                TxtAdapter().iter_chapters(prepared_dir, manifest, signal), 1
            ):
                on_progress(
                    f"正在整理章节 {index} / {len(source_chapters)}",
                    map_progress(5, 50, index, len(source_chapters)),
                )
                volume_title = str(imported.get("volume_title") or "正文")
                if volume_title not in volume_numbers:
                    volume_number = len(volume_numbers) + 1
                    volume_numbers[volume_title] = volume_number
                    volume_titles[volume_number] = volume_title
                serial = len(chapter_items) + 1
                body_path = f"chapters/{serial:06d}.html"
                target = prepared_dir / body_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(imported["body"]), encoding="utf-8")
                chapter_items.append(
                    {
                        "serial": serial,
                        "volume": volume_numbers[volume_title],
                        "title": str(imported["title"]),
                        "body_path": body_path,
                        "images": [],
                    }
                )
            metadata = manifest.get("metadata") or {}
            manifest = {
                "title": metadata.get("title"),
                "authors": metadata.get("authors"),
                "synopsis": "",
                "tags": [],
                "language": None,
                "cover_path": None,
                "images": {},
                "volume_titles": {str(key): value for key, value in volume_titles.items()},
                "chapters_data": chapter_items,
            }
        else:
            path = ctx.files.resolve(session.staging_path)
            if not path.is_file():
                raise EpubImportError(
                    "The uploaded EPUB staging file is missing.",
                    "找不到待导入的 EPUB 文件。",
                )
            manifest = EpubParser().prepare_commit(
                path,
                prepared_dir,
                manifest,
                signal,
                on_progress,
            )

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
            prepared_chapters = manifest.get("chapters_data") or []
            for index, item in enumerate(prepared_chapters, 1):
                _check_cancel(signal)
                on_progress(
                    f"正在保存章节 {index} / {len(prepared_chapters)}",
                    map_progress(50, 95, index, len(prepared_chapters)),
                )
                serial = int(item["serial"])
                chapter = Chapter(
                    id=generate_uuid(),
                    novel_id=novel_id,
                    serial=serial,
                    volume_id=volumes[int(item["volume"])].id,
                    url=f"{novel_url}#chapter-{serial}",
                    title=str(item["title"]),
                    is_done=True,
                    extra={"imported": True, "source_format": source_format},
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
                    "source_format": source_format,
                    "original_name": session.original_name,
                    "file_sha256": session.file_sha256,
                    "imported_at": current_timestamp(),
                },
            )

            _check_cancel(signal)
            on_progress("正在写入书库", 97)
            on_progress("正在写入书库", 99)
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
