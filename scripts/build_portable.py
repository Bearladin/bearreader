#!/usr/bin/env python
"""Build and verify the portable BearReader ZIP, then remove its bundle."""

import datetime
import hashlib
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "dist" / "BearReader"
VERSION = (ROOT / "lncrawl" / "VERSION").read_text(encoding="utf8").strip()
NOW = datetime.datetime.now()
OUTPUT = ROOT / "dist" / f"BearReader-portable-{VERSION}-{NOW:%Y-%m-%d}-{NOW:%H%M}.zip"
ZIP_PREFIX = "BearReader-portable"


def cleanup_bundle() -> None:
    expected_parent = (ROOT / "dist").resolve()
    resolved_bundle = BUNDLE.resolve()
    if (
        BUNDLE.is_symlink()
        or resolved_bundle.parent != expected_parent
        or resolved_bundle.name != "BearReader"
    ):
        raise SystemExit(f"Refusing to remove unexpected bundle path: {resolved_bundle}")
    try:
        shutil.rmtree(resolved_bundle)
    except OSError as error:
        raise SystemExit(f"Portable ZIP is valid, but bundle cleanup failed: {error}") from error


def main() -> None:
    exe = BUNDLE / "BearReader.exe"
    tool = BUNDLE / "backendtool.exe"
    internal = BUNDLE / "_internal"
    if not exe.is_file() or not tool.is_file() or not internal.is_dir():
        raise SystemExit("dist\\BearReader is incomplete; run `uv run python setup_pyi.py` first")

    if OUTPUT.exists():
        OUTPUT.unlink()

    files = [p for p in sorted(BUNDLE.rglob("*")) if p.is_file()]
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            zf.write(path, f"{ZIP_PREFIX}/{path.relative_to(BUNDLE).as_posix()}")

    with zipfile.ZipFile(OUTPUT) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise SystemExit(f"Portable ZIP is corrupt: {bad}")

    sha256 = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    size = OUTPUT.stat().st_size
    cleanup_bundle()
    print(f"Portable ZIP: {OUTPUT}")
    print(f"Entries: {len(files)}")
    print(f"Size: {size:,} bytes")
    print(f"SHA256: {sha256}")
    print(f"Removed intermediate bundle: {BUNDLE}")


if __name__ == "__main__":
    sys.exit(main())
