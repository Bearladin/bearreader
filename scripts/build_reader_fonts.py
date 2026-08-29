#!/usr/bin/env python
"""Build the two self-hosted XiaoXiong reader webfonts.

Source fonts are pinned, checksum-verified, and kept under the ignored
``res/fonts-src`` directory. Generated WOFF2 files are written to the monorepo
localized frontend repository and use neutral family names because subsetting
creates modified versions of the upstream fonts.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import unicodedata
import urllib.request

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "res" / "fonts-src"
MANIFEST_PATH = ROOT / "res" / "reader-fonts.json"
DEFAULT_FRONTEND_ROOT = ROOT / "frontend"


@dataclass(frozen=True)
class FontSpec:
    key: str
    source_name: str
    source_url: str
    source_sha256: str
    upstream_name: str
    upstream_version: str
    family_name: str
    postscript_name: str
    output_name: str
    license_name: str


FONT_SPECS = (
    FontSpec(
        key="kai",
        source_name="LXGWWenKaiGBScreen-v1.522.ttf",
        source_url=(
            "https://github.com/lxgw/LxgwWenKai-Screen/releases/download/"
            "v1.522/LXGWWenKaiGBScreen.ttf"
        ),
        source_sha256="23ec023913e1851925eb94462c4b0ccd1d78bb89533745aaa8cc682ccd339dc0",
        upstream_name="LXGW WenKai GB Screen",
        upstream_version="1.522",
        family_name="XiaoXiong Reader Kai",
        postscript_name="XiaoXiongReaderKai-Regular",
        output_name="XiaoXiongReaderKai-Regular.woff2",
        license_name="LICENSE-XIAOXIONG-READER-KAI-OFL.txt",
    ),
    FontSpec(
        key="serif",
        source_name="NotoSerifCJKsc-Regular-2.003.otf",
        source_url=(
            "https://raw.githubusercontent.com/notofonts/noto-cjk/Serif2.003/"
            "Serif/OTF/SimplifiedChinese/NotoSerifCJKsc-Regular.otf"
        ),
        source_sha256="2a2eae2628df83556c54018c41e20fa532c1b862c5256ae8b3f23feb918d12ca",
        upstream_name="Noto Serif CJK SC",
        upstream_version="2.003",
        family_name="XiaoXiong Reader Serif",
        postscript_name="XiaoXiongReaderSerif-Regular",
        output_name="XiaoXiongReaderSerif-Regular.woff2",
        license_name="LICENSE-XIAOXIONG-READER-SERIF-OFL.txt",
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gbk_codepoints() -> set[int]:
    """Return every printable Unicode scalar encoded by Python's GBK codec."""
    codepoints = set(range(0x20, 0x7F))
    for lead in range(0x81, 0xFF):
        for trail in range(0x40, 0xFF):
            if trail == 0x7F:
                continue
            try:
                text = bytes((lead, trail)).decode("gbk", errors="strict")
            except UnicodeDecodeError:
                continue
            if len(text) == 1 and unicodedata.category(text) != "Cc":
                codepoints.add(ord(text))
    return codepoints


def download_source(spec: FontSpec, source: Path) -> None:
    source.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {spec.upstream_name} {spec.upstream_version}...")
    with tempfile.NamedTemporaryFile(
        dir=source.parent, prefix=f".{source.name}.", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        urllib.request.urlretrieve(spec.source_url, temporary_path)
        temporary_path.replace(source)
    finally:
        temporary_path.unlink(missing_ok=True)


def verify_source(spec: FontSpec, source: Path, download: bool) -> None:
    if not source.is_file():
        if not download:
            raise RuntimeError(
                f"Missing {source}; rerun with --download or place the pinned source there"
            )
        download_source(spec, source)
    actual = sha256(source)
    if actual != spec.source_sha256:
        raise RuntimeError(
            f"Checksum mismatch for {source.name}: expected {spec.source_sha256}, got {actual}"
        )


def rename_font(font: TTFont, spec: FontSpec) -> None:
    name_table = font["name"]
    replacements = {
        1: spec.family_name,
        2: "Regular",
        3: f"{spec.family_name}; {spec.upstream_version}; {spec.postscript_name}",
        4: spec.family_name,
        6: spec.postscript_name,
        16: spec.family_name,
        17: "Regular",
    }
    for record in list(name_table.names):
        replacement = replacements.get(record.nameID)
        if replacement is not None:
            name_table.setName(
                replacement,
                record.nameID,
                record.platformID,
                record.platEncID,
                record.langID,
            )

    if "CFF " in font:
        cff = font["CFF "].cff
        cff.fontNames = [spec.postscript_name]
        top_dict = cff.topDictIndex[0]
        top_dict.FamilyName = spec.family_name
        top_dict.FullName = spec.family_name


def build_font(
    spec: FontSpec, source: Path, output: Path, requested: set[int]
) -> dict[str, object]:
    font = TTFont(source)
    source_cmap = set((font.getBestCmap() or {}).keys())
    present = requested & source_cmap
    missing = requested - source_cmap
    missing_han = {
        codepoint
        for codepoint in missing
        if unicodedata.name(chr(codepoint), "").startswith("CJK UNIFIED IDEOGRAPH")
    }
    if missing_han:
        raise RuntimeError(
            f"{spec.upstream_name} is missing {len(missing_han)} requested GBK Han characters"
        )

    options = Options()
    options.canonical_order = True
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14, 16, 17]
    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=sorted(present))
    subsetter.subset(font)
    rename_font(font, spec)
    font.flavor = "woff2"

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        font.save(temporary)
        temporary.replace(output)
    finally:
        font.close()
        temporary.unlink(missing_ok=True)

    rebuilt = TTFont(output)
    output_cmap = set((rebuilt.getBestCmap() or {}).keys())
    family = rebuilt["name"].getDebugName(1)
    postscript = rebuilt["name"].getDebugName(6)
    rebuilt.close()
    if not present <= output_cmap:
        raise RuntimeError(f"Output coverage check failed for {output.name}")
    if family != spec.family_name or postscript != spec.postscript_name:
        raise RuntimeError(f"Neutral name check failed for {output.name}")

    missing_labels = [f"U+{codepoint:04X}" for codepoint in sorted(missing)]
    result: dict[str, object] = {
        "key": spec.key,
        "upstream_name": spec.upstream_name,
        "upstream_version": spec.upstream_version,
        "source_url": spec.source_url,
        "source_sha256": spec.source_sha256,
        "family_name": spec.family_name,
        "postscript_name": spec.postscript_name,
        "output_name": spec.output_name,
        "output_sha256": sha256(output),
        "output_bytes": output.stat().st_size,
        "requested_codepoints": len(requested),
        "included_codepoints": len(present),
        "missing_non_han_codepoints": missing_labels,
        "license_file": spec.license_name,
    }
    print(
        f"Built {output.name}: {output.stat().st_size:,} bytes, "
        f"{len(present):,}/{len(requested):,} requested codepoints"
    )
    if missing_labels:
        print(f"  Missing non-Han codepoints (system fallback applies): {missing_labels}")
    return result


def check_outputs(output_dir: Path, manifest: dict[str, object]) -> None:
    entries = manifest.get("fonts")
    if not isinstance(entries, list):
        raise RuntimeError("Reader font manifest has no fonts list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Reader font manifest contains an invalid entry")
        output = output_dir / str(entry["output_name"])
        if not output.is_file():
            raise RuntimeError(f"Missing generated font: {output}")
        actual = sha256(output)
        if actual != entry["output_sha256"]:
            raise RuntimeError(f"Generated font checksum mismatch: {output}")
        font = TTFont(output, lazy=True)
        family = font["name"].getDebugName(1)
        font.close()
        if family != entry["family_name"]:
            raise RuntimeError(f"Generated font family mismatch: {output}")
        print(f"Verified {output.name}: {output.stat().st_size:,} bytes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frontend-root",
        type=Path,
        default=DEFAULT_FRONTEND_ROOT,
        help="Path to the monorepo frontend directory",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download missing pinned source fonts into the ignored source directory",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify existing generated fonts against the checked-in manifest",
    )
    args = parser.parse_args()

    frontend_root = args.frontend_root.resolve()
    if not (frontend_root / "package.json").is_file():
        raise RuntimeError(f"Not the monorepo frontend directory: {frontend_root}")
    output_dir = frontend_root / "src" / "assets" / "fonts"

    if args.check:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf8"))
        check_outputs(output_dir, manifest)
        return 0

    requested = gbk_codepoints()
    print(f"Printable GBK codepoints: {len(requested):,}")
    results: list[dict[str, object]] = []
    for spec in FONT_SPECS:
        source = SOURCE_DIR / spec.source_name
        verify_source(spec, source, args.download)
        results.append(build_font(spec, source, output_dir / spec.output_name, requested))

    manifest = {
        "schema_version": 1,
        "character_set": "Python 3.11 GBK printable repertoire",
        "fonts": results,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(f"Wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
