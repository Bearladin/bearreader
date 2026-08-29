"""Validate and atomically embed the monorepo frontend build.

The frontend sources live in ``frontend/`` inside this repository. This
script builds them, validates the Chinese-localized output, atomically
replaces ``lncrawl/server/web/`` with the build, and refreshes the
provenance manifest (``frontend-manifest.json``) that ties the frontend
source tree to the embedded output within the same commit.

The embedded directory is generated output — never edit it by hand.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import warnings

DISPLAY_NAME = "BearReader"
REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
WEB_DIR = REPO_ROOT / "lncrawl" / "server" / "web"
ABSOLUTE_SOURCE_MAP_PATH = re.compile(r"^(?:[a-zA-Z]:)?[\\/]")


def _source_map_content_for_digest(content: bytes) -> bytes:
    try:
        source_map = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return content
    if not isinstance(source_map, dict):
        return content

    changed = False
    sources = source_map.get("sources")
    if isinstance(sources, list):
        normalized_sources = []
        for source in sources:
            if isinstance(source, str) and ABSOLUTE_SOURCE_MAP_PATH.match(source):
                # Vite PWA emits its generated service worker beneath a random temp directory.
                normalized_source = source.replace("\\", "/")
                normalized_sources.append(f"<absolute>/{normalized_source.rsplit('/', 1)[-1]}")
                changed = True
            else:
                normalized_sources.append(source)
        source_map["sources"] = normalized_sources

    source_root = source_map.get("sourceRoot")
    if isinstance(source_root, str) and ABSOLUTE_SOURCE_MAP_PATH.match(source_root):
        source_map["sourceRoot"] = "<absolute>"
        changed = True

    if not changed:
        return content
    return json.dumps(source_map, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def tree_digest(root: Path) -> str:
    """Digest of a built frontend tree; source-map machine paths normalized away."""

    digest = hashlib.sha256()
    files = sorted(
        (file for file in root.glob("**/*") if file.is_file()),
        key=lambda file: file.relative_to(root).as_posix(),
    )
    for file in files:
        relative = file.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        if file.suffix == ".map":
            digest.update(_source_map_content_for_digest(file.read_bytes()))
        else:
            with file.open("rb") as content:
                while chunk := content.read(1024 * 1024):
                    digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def build_frontend(frontend_dir: Path = FRONTEND_DIR) -> None:
    yarn = "yarn.cmd" if sys.platform == "win32" else "yarn"
    try:
        result = subprocess.run(
            [yarn, "build"],
            cwd=frontend_dir,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        raise ValueError(f"Frontend yarn build could not start: {error}") from error
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"Frontend yarn build failed: {message}")


def validate_frontend(source: Path) -> str:
    """Validate a built frontend tree and return its normalized digest."""

    source = source.resolve()
    if not source.is_dir():
        raise ValueError(f"Frontend dist directory does not exist: {source}")

    index_file = source / "index.html"
    manifest_file = source / "manifest.webmanifest"
    assets_dir = source / "assets"
    missing = [str(path) for path in (index_file, manifest_file, assets_dir) if not path.exists()]
    if missing:
        raise ValueError(f"Frontend dist is missing required paths: {', '.join(missing)}")
    if not assets_dir.is_dir():
        raise ValueError(f"Frontend assets path is not a directory: {assets_dir}")

    index_html = index_file.read_text(encoding="utf-8")
    if not re.search(r'<html\b[^>]*\blang=["\']zh-CN["\']', index_html):
        raise ValueError('Frontend index.html must declare lang="zh-CN"')
    title = re.search(r"<title>\s*(.*?)\s*</title>", index_html, re.IGNORECASE | re.DOTALL)
    if title is None or not re.match(
        rf"{re.escape(DISPLAY_NAME)}(?: v\d+\.\d+\.\d+)?", title.group(1).strip()
    ):
        raise ValueError(f"Frontend index.html title must be {DISPLAY_NAME}")

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Frontend manifest is invalid JSON: {error}") from error
    if not isinstance(manifest, dict):
        raise ValueError("Frontend manifest must be a JSON object")
    if manifest.get("name") != DISPLAY_NAME:
        raise ValueError(f"Frontend manifest name must be {DISPLAY_NAME}")
    if manifest.get("lang") != "zh-CN":
        raise ValueError("Frontend manifest language must be zh-CN")

    for name in ("PRIVACY_POLICY.html", "TERMS_OF_SERVICE.html"):
        legal_file = source / name
        if not legal_file.is_file():
            raise ValueError(f"Frontend is missing Chinese legal document: {legal_file}")
        content = legal_file.read_text(encoding="utf-8")
        if DISPLAY_NAME not in content or not re.search(r"[\u4e00-\u9fff]", content):
            raise ValueError(f"Frontend legal document is not localized: {legal_file}")

    return tree_digest(source)


def sync_localized_frontend(
    destination: Path = WEB_DIR,
    frontend_dir: Path = FRONTEND_DIR,
) -> None:
    import frontend_manifest

    frontend_dir = frontend_dir.resolve()
    source = (frontend_dir / "dist").resolve()
    destination = destination.resolve()
    build_frontend(frontend_dir)
    source_digest = validate_frontend(source)

    parent = destination.parent
    staging = parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    backup = parent / f".{destination.name}.backup-{uuid.uuid4().hex}"
    replaced = False
    installed = False
    committed = False
    try:
        shutil.copytree(source, staging)
        if validate_frontend(staging) != source_digest:
            raise ValueError("Staged frontend digest does not match the built dist")

        if destination.exists():
            destination.replace(backup)
            replaced = True
        staging.replace(destination)
        installed = True
        if validate_frontend(destination) != source_digest:
            raise ValueError("Embedded frontend digest does not match the built dist")
        frontend_manifest.write_manifest(
            frontend_dir=frontend_dir,
            web_dir=destination,
            manifest_path=frontend_dir.parent / "frontend-manifest.json",
        )
        committed = True
    except Exception:
        if not committed:
            if installed and destination.exists():
                shutil.rmtree(destination)
            if staging.exists():
                shutil.rmtree(staging)
            if replaced and backup.exists() and not destination.exists():
                backup.replace(destination)
        raise

    if backup.exists():
        try:
            shutil.rmtree(backup)
        except OSError as error:
            warnings.warn(
                f"Localized frontend was installed, but backup cleanup failed at {backup}: {error}. "
                "The new frontend remains installed; no rollback was attempted and any remaining "
                "backup was left in place for inspection.",
                RuntimeWarning,
                stacklevel=2,
            )


def validate_only() -> None:
    import frontend_manifest

    validate_frontend(WEB_DIR)
    mismatches = frontend_manifest.verify_manifest()
    if mismatches:
        raise ValueError("; ".join(mismatches))


def compare_built_to_embedded() -> None:
    """Compare a caller-built frontend/dist against the embedded web directory."""

    built = validate_frontend(FRONTEND_DIR / "dist")
    embedded = validate_frontend(WEB_DIR)
    if built != embedded:
        detail = _tree_diff(FRONTEND_DIR / "dist", WEB_DIR)
        raise ValueError(
            "Embedded frontend does not match the freshly built dist "
            f"(built {built}, embedded {embedded})"
            + (f"; first differences: {detail}" if detail else "")
        )


def _tree_diff(left: Path, right: Path, limit: int = 10) -> list:
    names = sorted(
        {
            p.relative_to(root).as_posix()
            for root in (left, right)
            for p in root.glob("**/*")
            if p.is_file()
        }
    )
    differences = []
    for name in names:
        left_file, right_file = left / name, right / name
        if not left_file.is_file() or not right_file.is_file():
            differences.append(f"{name}: present only on one side")
        elif left_file.read_bytes().replace(b"\r\n", b"\n") != right_file.read_bytes().replace(
            b"\r\n", b"\n"
        ):
            differences.append(f"{name}: content differs")
        if len(differences) >= limit:
            break
    return differences


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the monorepo frontend and atomically embed it into lncrawl/server/web"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the embedded frontend and the provenance manifest",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare an already-built frontend/dist against the embedded web directory",
    )
    args = parser.parse_args()

    if args.validate_only and args.compare:
        parser.error("choose either --validate-only or --compare, not both")

    try:
        if args.validate_only:
            validate_only()
            action = "Validated"
        elif args.compare:
            compare_built_to_embedded()
            action = "Compared"
        else:
            sync_localized_frontend()
            action = "Embedded"
    except ValueError as error:
        parser.error(str(error))

    print(f"{action} localized frontend from {FRONTEND_DIR}")


if __name__ == "__main__":
    main()
