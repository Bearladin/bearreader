from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import locale
import logging
import os
from pathlib import Path
import platform
import sys
from tempfile import gettempdir
from threading import Lock
import traceback
from typing import Deque, Iterable, Optional

DATA_ENV = "XIAOXIONG_NOVEL_DATA_PATH"
LOG_NAME = "startup-error.log"
MAX_LOG_BYTES = 1024 * 1024
MAX_CAPTURE_CHARS = 128 * 1024

_write_lock = Lock()


def _data_dir() -> Path:
    configured = os.getenv(DATA_ENV)
    if configured:
        return Path(configured).expanduser().absolute()
    roaming = os.getenv("APPDATA")
    if roaming:
        return (Path(roaming) / "XiaoXiongNovel").absolute()
    return (Path.home() / "AppData" / "Roaming" / "XiaoXiongNovel").absolute()


def _candidate_paths() -> Iterable[Path]:
    primary: Optional[Path] = None
    try:
        primary = _data_dir() / LOG_NAME
        yield primary
    except (OSError, RuntimeError, ValueError):
        pass
    try:
        fallback = Path(gettempdir()).absolute() / f"BearReader-{LOG_NAME}"
    except (OSError, RuntimeError, ValueError):
        return
    if fallback != primary:
        yield fallback


def _version() -> str:
    try:
        return (Path(__file__).resolve().parent / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _rotate(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < MAX_LOG_BYTES:
        return
    backup = path.with_name(f"{path.name}.1")
    backup.unlink(missing_ok=True)
    path.replace(backup)


def _format_report(
    stage: str,
    message: str,
    error: Optional[BaseException],
    captured_logs: str,
) -> str:
    lines = [
        "=" * 72,
        f"time_utc: {datetime.now(timezone.utc).isoformat()}",
        f"stage: {stage}",
        f"message: {message}",
        f"version: {_version()}",
        f"windows: {platform.platform()}",
        f"utf8_mode: {sys.flags.utf8_mode}",
        f"executable: {sys.executable}",
        f"program_dir: {Path(sys.executable).resolve().parent}",
        f"working_dir: {Path.cwd()}",
        f"data_dir: {_data_dir()}",
        f"filesystem_encoding: {sys.getfilesystemencoding()}",
        f"preferred_encoding: {locale.getpreferredencoding(False)}",
        f"stdout_encoding: {getattr(sys.stdout, 'encoding', None)}",
        f"stderr_encoding: {getattr(sys.stderr, 'encoding', None)}",
    ]
    if captured_logs.strip():
        lines.extend(["", "--- startup logs ---", captured_logs.rstrip()])
    if error is not None:
        lines.extend(
            [
                "",
                "--- exception ---",
                "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                ).rstrip(),
            ]
        )
    lines.extend(["", ""])
    return "\n".join(lines)


def record_startup_failure(
    stage: str,
    message: str,
    *,
    error: Optional[BaseException] = None,
    captured_logs: str = "",
) -> Optional[Path]:
    """Append one UTF-8 startup diagnostic without ever masking the launch error."""
    try:
        report = _format_report(stage, message, error, captured_logs[-MAX_CAPTURE_CHARS:])
    except Exception:
        report = f"{datetime.now(timezone.utc).isoformat()} {stage}: {message}\n"

    with _write_lock:
        for path in _candidate_paths():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                _rotate(path)
                with path.open("a", encoding="utf-8", errors="replace", newline="\n") as handle:
                    handle.write(report)
                return path
            except OSError:
                continue
    return None


def show_startup_failure(message: str, log_path: Optional[Path]) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        if ctypes.windll.kernel32.GetConsoleWindow():
            return
        detail = message
        if log_path is not None:
            detail += f"\n\n诊断日志：\n{log_path}"
        ctypes.windll.user32.MessageBoxW(None, detail, "BearReader", 0x10)
    except (AttributeError, OSError):
        return


class StartupLogCapture(logging.Handler):
    """Keep a bounded copy of startup logs for a later failure report."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self._lines: Deque[str] = deque()
        self._chars = 0
        self._targets: list[logging.Logger] = []
        self._lock = Lock()
        self.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:
            self.handleError(record)
            return
        with self._lock:
            self._lines.append(line)
            self._chars += len(line) + 1
            while self._lines and self._chars > MAX_CAPTURE_CHARS:
                self._chars -= len(self._lines.popleft()) + 1

    def install(self) -> "StartupLogCapture":
        for name in ("", "uvicorn", "uvicorn.error"):
            target = logging.getLogger(name)
            if target not in self._targets:
                target.addHandler(self)
                self._targets.append(target)
        return self

    def text(self) -> str:
        with self._lock:
            return "\n".join(self._lines)

    def close(self) -> None:
        targets = [
            *self._targets,
            *(logging.getLogger(name) for name in ("", "uvicorn", "uvicorn.error")),
        ]
        for target in dict.fromkeys(targets):
            target.removeHandler(self)
        self._targets.clear()
        super().close()
