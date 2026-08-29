import argparse
import ast
import base64
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable, Optional

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sync_localized_frontend import validate_frontend  # noqa: E402

APP_NAME = "BearReader"
EXPECTED_EXES = {"BearReader.exe", "backendtool.exe"}
RETIRED_EXES = {"小熊小说下载器.exe", "后台工具不要点.exe"}
READER_FONT_PREFIXES = (
    "XiaoXiongReaderKai-Regular-",
    "XiaoXiongReaderSerif-Regular-",
)
READER_FONT_NOTICES = (
    "LICENSE-XIAOXIONG-READER-KAI-OFL.txt",
    "LICENSE-XIAOXIONG-READER-SERIF-OFL.txt",
    "THIRD_PARTY_READER_FONTS.md",
)
_ICON_EXTRACTION_SCRIPT = r"""
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Icon]::ExtractAssociatedIcon($env:BEARREADER_ICON_EXE)
if ($null -eq $icon) { throw "Executable has no associated icon" }
$bitmap = $null
$stream = $null
try {
  $bitmap = $icon.ToBitmap()
  $stream = New-Object System.IO.MemoryStream
  $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
  [Console]::Out.Write([Convert]::ToBase64String($stream.ToArray()))
}
finally {
  if ($null -ne $stream) { $stream.Dispose() }
  if ($null -ne $bitmap) { $bitmap.Dispose() }
  $icon.Dispose()
}
"""


def _single_path(paths: Iterable[Path], description: str) -> Path:
    found = list(paths)
    if len(found) != 1:
        raise ValueError(f"Expected one {description}, found: {found}")
    return found[0]


def _bundle_sources(bundle: Path) -> Path:
    return _single_path(
        (path.parent for path in bundle.glob("**/_index.json") if path.parent.name == "sources"),
        "bundled sources directory",
    )


def _analysis_file(analysis_root: Path) -> Path:
    return _single_path(analysis_root.glob("**/Analysis-00.toc"), "PyInstaller analysis file")


def _walk_analysis(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_analysis(item)


def _validate_analysis_content(content: str) -> None:
    try:
        analysis = ast.literal_eval(content)
    except (SyntaxError, ValueError) as error:
        raise ValueError(f"PyInstaller analysis is not a Python literal: {error}") from error

    source_modules = {
        module for module in _walk_analysis(analysis) if module.startswith("sources.")
    }
    unexpected = sorted(
        module
        for module in source_modules
        if module != "sources.zh" and not module.startswith("sources.zh.")
    )
    if unexpected:
        raise ValueError(f"PyInstaller analysis includes non-Chinese source modules: {unexpected}")
    if not any(
        module == "sources.zh" or module.startswith("sources.zh.") for module in source_modules
    ):
        raise ValueError("PyInstaller analysis does not include any sources.zh module")


def _validate_analysis(analysis_file: Path) -> None:
    _validate_analysis_content(analysis_file.read_text(encoding="utf-8", errors="replace"))


def _executable_icon_digest(executable: Path) -> str:
    env = os.environ.copy()
    env["BEARREADER_ICON_EXE"] = str(executable)
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _ICON_EXTRACTION_SCRIPT,
        ],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"Failed to extract executable icon from {executable}: {message}")
    try:
        encoded = base64.b64decode(result.stdout.strip(), validate=True)
        with Image.open(BytesIO(encoded)) as image:
            normalized = image.convert("RGBA")
            size = normalized.size
            pixels = normalized.tobytes()
    except (ValueError, OSError) as error:
        raise ValueError(f"Invalid executable icon extracted from {executable}: {error}") from error
    payload = size[0].to_bytes(4, "little") + size[1].to_bytes(4, "little") + pixels
    return sha256(payload).hexdigest()


def _validate_executable_icons(bundle: Path) -> None:
    app = bundle / "BearReader.exe"
    tool = bundle / "backendtool.exe"
    if _executable_icon_digest(app) == _executable_icon_digest(tool):
        raise ValueError("BearReader.exe and backendtool.exe must use different icons")


def run_self_test() -> None:
    synthetic = repr(
        (
            "entry",
            (
                "sources.zh.valid",
                ("sources.en.transitive_fixture", "unrelated"),
            ),
        )
    )
    try:
        _validate_analysis_content(synthetic)
    except ValueError as error:
        if "sources.en.transitive_fixture" not in str(error):
            raise AssertionError(f"Synthetic TOC failed for the wrong reason: {error}") from error
    else:
        raise AssertionError("Synthetic non-Chinese source module passed analysis validation")


def verify_bundle(bundle: Path, analysis_root: Optional[Path] = None) -> None:
    bundle = bundle.absolute()
    executable = bundle / f"{APP_NAME}.exe"
    if not executable.is_file():
        raise ValueError(f"Missing BearReader executable: {executable}")
    executable_names = {path.name for path in bundle.glob("*.exe")}
    if executable_names != EXPECTED_EXES:
        raise ValueError(
            f"Bundle executables must be exactly {sorted(EXPECTED_EXES)}, "
            f"found: {sorted(executable_names)}"
        )
    retired = sorted(executable_names & RETIRED_EXES)
    if retired:
        raise ValueError(f"Bundle contains retired compatibility entries: {retired}")
    _validate_executable_icons(bundle)

    source_root = _bundle_sources(bundle)
    language_dirs = {
        path.name
        for path in source_root.iterdir()
        if path.is_dir() and not path.name.startswith("_")
    }
    if language_dirs != {"zh"}:
        raise ValueError(
            f"Bundled source languages must be only zh, found: {sorted(language_dirs)}"
        )

    index_file = source_root / "_index.json"
    index = json.loads(index_file.read_text(encoding="utf-8"))
    crawlers = index.get("crawlers")
    supported = index.get("supported")
    if not isinstance(crawlers, dict) or not isinstance(supported, dict):
        raise ValueError("Bundled source index has invalid crawler metadata")
    if not crawlers:
        raise ValueError("Bundled source index contains zero crawlers")
    if not all(
        isinstance(info, dict) and str(info.get("file_path", "")).startswith("sources/zh/")
        for info in crawlers.values()
    ):
        raise ValueError("Bundled source index references a non-Chinese crawler")
    if "https://www.mayiwsk.com/" not in supported:
        raise ValueError("Bundled source index is missing mayiwsk")
    if "https://www.nieba.net/" not in supported:
        raise ValueError("Bundled source index is missing nieba")

    web_root = bundle / "_internal" / "lncrawl" / "server" / "web"
    validate_frontend(web_root)

    web_assets = web_root / "assets"
    for prefix in READER_FONT_PREFIXES:
        fonts = list(web_assets.glob(f"{prefix}*.woff2"))
        if len(fonts) != 1 or fonts[0].stat().st_size < 1_000_000:
            raise ValueError(f"Bundled reader font is missing or truncated: {prefix}")

    internal_root = bundle / "_internal"
    for notice in READER_FONT_NOTICES:
        notice_path = internal_root / notice
        if not notice_path.is_file() or notice_path.stat().st_size == 0:
            raise ValueError(f"Bundled reader font notice is missing: {notice_path}")

    root = analysis_root or PROJECT_ROOT / "windows" / "build"
    _validate_analysis(_analysis_file(root))


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a BearReader Windows PyInstaller bundle")
    parser.add_argument("bundle", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("Verified PyInstaller analysis self-test.")
        return
    if args.bundle is None:
        parser.error("bundle is required unless --self-test is used")
    try:
        verify_bundle(args.bundle)
    except ValueError as error:
        parser.error(str(error))
    print(f"Verified BearReader Windows bundle: {args.bundle}")


if __name__ == "__main__":
    main()
