import codecs
import html
import json
import os
from pathlib import Path
import re
from threading import Event
from typing import Any, Dict, Iterator, List, Optional, Tuple
import unicodedata

from charset_normalizer import from_bytes
import regex as safe_regex

from .progress import ImportProgressCallback, map_progress

MAX_TXT_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_NORMALIZED_BYTES = 30 * 1024 * 1024
MAX_TXT_CHAPTER_BYTES = 10 * 1024 * 1024
SOFT_CHAPTER_CHARS = 50_000
DEFAULT_CHAPTER_PATTERN = safe_regex.compile(
    r"^\s*(?:"
    r"第[零〇一二两三四五六七八九十百千万\d]+[章节回卷部篇集]"
    r"|序章|楔子|前言|后记|尾声|番外(?:\s*\d+)?"
    r"|(?:chapter|volume|book|part)\s+(?:\d+|[ivxlcdm]+)\b"
    r").*$",
    re.IGNORECASE,
)
VOLUME_PATTERN = safe_regex.compile(
    r"^\s*(?:第[零〇一二两三四五六七八九十百千万\d]+[卷部篇集]"
    r"|(?:volume|book|part)\s+(?:\d+|[ivxlcdm]+)\b).*$",
    re.IGNORECASE,
)


class TxtImportError(Exception):
    def __init__(self, message: str, user_message: Optional[str] = None) -> None:
        super().__init__(message)
        self.user_message = user_message or message


def _check_cancel(signal: Event) -> None:
    if signal.is_set():
        from ...exceptions import AbortedException

        raise AbortedException()


def _strict_utf8(path: Path) -> bool:
    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                decoder.decode(chunk)
        decoder.decode(b"", final=True)
        return True
    except UnicodeDecodeError:
        return False


def _sample(path: Path, max_bytes: int = 1024 * 1024) -> bytes:
    size = path.stat().st_size
    each = min(max_bytes // 3, size)
    chunks: List[bytes] = []
    with path.open("rb") as source:
        for offset in (0, max(0, size // 2 - each // 2), max(0, size - each)):
            source.seek(offset)
            chunks.append(source.read(each))
    return b"\n".join(chunks)[:max_bytes]


def detect_encoding(path: Path, requested: Optional[str] = None) -> Dict[str, Any]:
    if requested:
        try:
            selected = codecs.lookup(requested).name
        except LookupError as error:
            raise TxtImportError(
                f"Unknown TXT encoding: {requested}",
                "TXT 编码名称无效，请重新选择。",
            ) from error
        return {
            "selected": selected,
            "confidence": 1.0,
            "requires_confirmation": False,
            "candidates": [selected],
        }

    with path.open("rb") as source:
        prefix = source.read(4)
    if prefix.startswith(codecs.BOM_UTF8):
        selected = "utf-8-sig"
    elif prefix.startswith(codecs.BOM_UTF16_LE):
        selected = "utf-16-le"
    elif prefix.startswith(codecs.BOM_UTF16_BE):
        selected = "utf-16-be"
    elif _strict_utf8(path):
        selected = "utf-8"
    else:
        matches = from_bytes(_sample(path))
        candidates: List[Tuple[str, float]] = []
        for match in matches:
            encoding = str(match.encoding or "").lower()
            if not encoding:
                continue
            confidence = max(0.0, min(1.0, float(match.percent_coherence) / 100.0))
            if encoding not in {item[0] for item in candidates}:
                candidates.append((encoding, confidence))
            if len(candidates) >= 5:
                break
        if not candidates:
            raise TxtImportError(
                "TXT encoding could not be detected.",
                "无法可靠识别 TXT 编码，请手动选择正确编码。",
            )
        candidates.sort(key=lambda item: item[1], reverse=True)
        selected, confidence = candidates[0]
        second = candidates[1][1] if len(candidates) > 1 else 0.0
        return {
            "selected": selected,
            "confidence": confidence,
            "requires_confirmation": confidence < 0.60 or confidence - second < 0.10,
            "candidates": [item[0] for item in candidates],
        }
    return {
        "selected": selected,
        "confidence": 1.0,
        "requires_confirmation": False,
        "candidates": [selected],
    }


def normalize_txt(
    source_path: Path,
    target_path: Path,
    encoding: str,
    signal: Event,
    on_progress: ImportProgressCallback,
) -> None:
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    temporary = target_path.with_suffix(".tmp")
    pending_cr = False
    written = 0
    read_bytes = 0
    source_size = source_path.stat().st_size
    try:
        with source_path.open("rb") as source, temporary.open("wb") as target:
            for raw in iter(lambda: source.read(64 * 1024), b""):
                _check_cancel(signal)
                read_bytes += len(raw)
                on_progress(
                    f"正在规范化正文 {read_bytes} / {source_size} bytes",
                    map_progress(5, 45, read_bytes, source_size),
                )
                text = decoder.decode(raw)
                if pending_cr:
                    text = "\r" + text
                    pending_cr = False
                if text.endswith("\r"):
                    text = text[:-1]
                    pending_cr = True
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                text = "".join(
                    char
                    for char in text
                    if char in "\n\t" or not unicodedata.category(char).startswith("C")
                )
                encoded = unicodedata.normalize("NFC", text).encode("utf-8")
                written += len(encoded)
                if written > MAX_NORMALIZED_BYTES:
                    raise TxtImportError(
                        "Normalized TXT is too large.",
                        "TXT 规范化后不能超过 30 MB。",
                    )
                target.write(encoded)
            tail = decoder.decode(b"", final=True)
            if pending_cr:
                tail = "\n" + tail
            encoded = unicodedata.normalize("NFC", tail).encode("utf-8")
            if written + len(encoded) > MAX_NORMALIZED_BYTES:
                raise TxtImportError("Normalized TXT is too large.")
            target.write(encoded)
        os.replace(temporary, target_path)
    except UnicodeDecodeError as error:
        temporary.unlink(missing_ok=True)
        raise TxtImportError(
            f"TXT decoding failed with {encoding}.",
            "无法用所选编码完整读取 TXT，请选择正确编码。",
        ) from error
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _resolve_mode(lines: List[str], requested: str) -> str:
    if requested != "auto":
        if requested not in {"block", "print", "single", "unformatted"}:
            raise TxtImportError("Unsupported TXT paragraph mode.", "TXT 段落模式无效。")
        return requested
    non_empty = [line for line in lines if line.strip()]
    if not non_empty:
        return "block"
    blank_ratio = 1 - len(non_empty) / max(1, len(lines))
    indent_ratio = sum(line.startswith((" ", "\t", "　")) for line in non_empty) / len(non_empty)
    lengths = [len(line.strip()) for line in non_empty]
    mean = sum(lengths) / len(lengths)
    similar = sum(abs(length - mean) <= max(3, mean * 0.25) for length in lengths) / len(lengths)
    if blank_ratio >= 0.18:
        return "block"
    if indent_ratio >= 0.25:
        return "print"
    if similar >= 0.7 and mean >= 20:
        return "block"
    return "single"


def _join_lines(lines: List[str]) -> str:
    result = ""
    for line in lines:
        value = line.strip()
        if not value:
            continue
        if (
            result
            and result[-1].isascii()
            and value[0].isascii()
            and result[-1].isalnum()
            and value[0].isalnum()
        ):
            result += " "
        result += value
    return result


def format_txt_body(text: str, mode: str, unwrap_lines: bool = True) -> str:
    lines = text.splitlines()
    if lines and DEFAULT_CHAPTER_PATTERN.match(lines[0], timeout=0.05):
        lines = lines[1:]
    paragraphs: List[str] = []
    if mode == "unformatted":
        escaped = html.escape("\n".join(lines), quote=False).replace("\n", "<br />\n")
        return f"<p>{escaped}</p>" if escaped.strip() else ""
    if mode == "single":
        paragraphs = [line.strip() for line in lines if line.strip()]
    elif mode == "print":
        current: List[str] = []
        for line in lines:
            if not line.strip():
                if current:
                    paragraphs.append(_join_lines(current))
                    current = []
                continue
            if line.startswith((" ", "\t", "　")) and current:
                paragraphs.append(_join_lines(current))
                current = []
            current.append(line)
        if current:
            paragraphs.append(_join_lines(current))
    else:
        blocks = re.split(r"\n\s*\n+", "\n".join(lines))
        paragraphs = [
            _join_lines(block.splitlines()) if unwrap_lines else block.strip()
            for block in blocks
            if block.strip()
        ]
    return "\n".join(f"<p>{html.escape(item, quote=False)}</p>" for item in paragraphs)


class TxtAdapter:
    def analyze(
        self,
        source_path: Path,
        prepared_dir: Path,
        signal: Event,
        on_progress: ImportProgressCallback,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        options = dict(options or {})
        prepared_dir.mkdir(parents=True, exist_ok=True)
        on_progress("识别 TXT 编码", 1)
        encoding_info = detect_encoding(source_path, options.get("encoding"))
        normalized = prepared_dir / "normalized.txt"
        on_progress("规范化 TXT 正文", 5)
        normalize_txt(
            source_path,
            normalized,
            encoding_info["selected"],
            signal,
            on_progress,
        )

        on_progress("识别章节和段落", 45)
        custom_pattern = options.get("chapter_pattern")
        try:
            chapter_pattern = (
                safe_regex.compile(custom_pattern, safe_regex.IGNORECASE)
                if custom_pattern
                else DEFAULT_CHAPTER_PATTERN
            )
        except safe_regex.error as error:
            raise TxtImportError("Invalid chapter pattern.", "自定义章节规则无效。") from error
        line_samples: List[str] = []
        chapters: List[Dict[str, Any]] = []
        current_start = 0
        current_title = "正文"
        current_volume = "正文"
        char_count = 0
        last_boundary = 0
        byte_offset = 0
        normalized_size = normalized.stat().st_size

        def append_chapter(end: int) -> None:
            nonlocal current_start, current_title
            if end <= current_start:
                return
            if end - current_start > MAX_TXT_CHAPTER_BYTES:
                raise TxtImportError("A TXT chapter exceeds 10 MB.", "TXT 单章不能超过 10 MB。")
            chapters.append(
                {
                    "stable_key": f"txt:{current_start}:{end}",
                    "byte_start": current_start,
                    "byte_end": end,
                    "title": current_title,
                    "volume_title": current_volume,
                }
            )

        with normalized.open("rb") as source:
            for raw_line in source:
                _check_cancel(signal)
                line_start = byte_offset
                byte_offset += len(raw_line)
                on_progress(
                    f"正在识别章节 {byte_offset} / {normalized_size} bytes",
                    map_progress(45, 90, byte_offset, normalized_size),
                )
                line = raw_line.decode("utf-8").rstrip("\n")
                if len(line_samples) < 500:
                    line_samples.append(line)
                stripped = line.strip()
                try:
                    is_heading = bool(chapter_pattern.match(line, timeout=0.05))
                except TimeoutError as error:
                    raise TxtImportError(
                        "TXT chapter pattern timed out.",
                        "自定义章节规则匹配超时，请简化规则。",
                    ) from error
                if is_heading and stripped:
                    append_chapter(line_start)
                    current_start = line_start
                    current_title = stripped[:200]
                    if VOLUME_PATTERN.match(line, timeout=0.05):
                        current_volume = stripped[:200]
                char_count += len(line)
                if not stripped:
                    last_boundary = byte_offset
                if char_count >= SOFT_CHAPTER_CHARS and last_boundary > current_start:
                    append_chapter(last_boundary)
                    current_start = last_boundary
                    current_title = f"第 {len(chapters) + 1} 章"
                    char_count = 0
        append_chapter(byte_offset)
        if not chapters:
            raise TxtImportError("TXT has no readable text.", "TXT 中没有可导入的正文。")
        paragraph_mode = str(options.get("paragraph_mode") or "auto")
        resolved_mode = _resolve_mode(line_samples, paragraph_mode)
        unwrap_lines = bool(options.get("unwrap_lines", True))

        samples: List[Dict[str, str]] = []
        on_progress("生成 TXT 预览", 95)
        with normalized.open("rb") as source:
            for index in sorted({0, len(chapters) // 2, len(chapters) - 1}):
                item = chapters[index]
                source.seek(item["byte_start"])
                raw = source.read(min(item["byte_end"] - item["byte_start"], 2048))
                samples.append(
                    {
                        "title": item["title"],
                        "body_preview": raw.decode("utf-8", errors="ignore")[:240],
                    }
                )
        title = source_path.stem
        public = {
            "source_format": "txt",
            "title": title,
            "authors": "",
            "language": None,
            "synopsis": "",
            "tags": [],
            "chapters": len(chapters),
            "volumes": len({item["volume_title"] for item in chapters}),
            "cover_available": False,
            "illustrations": 0,
            "encoding": encoding_info,
            "paragraph_mode": paragraph_mode,
            "resolved_paragraph_mode": resolved_mode,
            "can_commit": not encoding_info["requires_confirmation"],
            "warnings": (
                ["编码识别结果需要确认后才能导入。"]
                if encoding_info["requires_confirmation"]
                else []
            ),
            "samples": samples[:3],
        }
        private = {
            "schema_version": 1,
            "source_format": "txt",
            "metadata": {"title": title, "authors": ""},
            "options": {
                "encoding": encoding_info["selected"],
                "paragraph_mode": paragraph_mode,
                "resolved_paragraph_mode": resolved_mode,
                "unwrap_lines": unwrap_lines,
                "chapter_pattern": custom_pattern,
            },
            "chapters": chapters,
        }
        (prepared_dir / "manifest.json").write_text(
            json.dumps(private, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        on_progress("保存分析结果", 99)
        return public, private

    def iter_chapters(
        self, prepared_dir: Path, manifest: Dict[str, Any], signal: Event
    ) -> Iterator[Dict[str, Any]]:
        normalized = prepared_dir / "normalized.txt"
        file_size = normalized.stat().st_size
        previous_end = 0
        options = manifest.get("options") or {}
        mode = str(options.get("resolved_paragraph_mode") or "block")
        unwrap_lines = bool(options.get("unwrap_lines", True))
        with normalized.open("rb") as source:
            for item in manifest.get("chapters") or []:
                _check_cancel(signal)
                start = int(item["byte_start"])
                end = int(item["byte_end"])
                if (
                    start < previous_end
                    or end <= start
                    or end > file_size
                    or end - start > MAX_TXT_CHAPTER_BYTES
                ):
                    raise TxtImportError("TXT private manifest contains invalid byte ranges.")
                source.seek(start)
                raw = source.read(end - start)
                if len(raw) != end - start:
                    raise TxtImportError("TXT chapter could not be read completely.")
                body = format_txt_body(raw.decode("utf-8", errors="strict"), mode, unwrap_lines)
                yield {**item, "body": body}
                previous_end = end
