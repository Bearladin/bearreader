"""Generate and verify the frontend build manifest.

Replaces the old cross-repository provenance (an external frontend repository
and a revision file under ``lncrawl/server/web/version``) with two
deterministic tree digests over files that live in this same repository:

- ``frontend_tree_digest``: digest of the tracked ``frontend/`` source tree;
- ``build_digest``: digest of the embedded build output in
  ``lncrawl/server/web/`` (source-map absolute paths normalized away).

Because both trees are part of the same commit, a release tag pins the
frontend sources and the embedded output together; no commit SHA of this
repository is ever written into a file tracked by that same commit.
"""

import argparse
from fnmatch import fnmatch
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from sync_localized_frontend import tree_digest as build_tree_digest

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
WEB_DIR = REPO_ROOT / "lncrawl" / "server" / "web"
MANIFEST_PATH = REPO_ROOT / "frontend-manifest.json"

# Untracked / build outputs inside frontend/ that must not affect the digest.
FRONTEND_SKIP_PATTERNS = ("node_modules/*", "node_modules", "dist/*", "dist")


def _skipped(relative: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(relative, pattern) or relative == pattern for pattern in patterns)


def frontend_tree_digest(root: Path = FRONTEND_DIR) -> str:
    """Digest of the frontend source tree, LF-normalized, skipping builds."""

    digest = hashlib.sha256()
    files = sorted(
        (
            file
            for file in root.glob("**/*")
            if file.is_file()
            and not _skipped(file.relative_to(root).as_posix(), FRONTEND_SKIP_PATTERNS)
        ),
        key=lambda file: file.relative_to(root).as_posix(),
    )
    for file in files:
        relative = file.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(hashlib.sha256(file.read_bytes().replace(b"\r\n", b"\n")).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def _tool_version(*command: str) -> str:
    if sys.platform == "win32" and command[0] == "yarn":
        command = ("yarn.cmd", *command[1:])
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return "unknown"
    if result.returncode:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _vite_version(frontend_dir: Path = FRONTEND_DIR) -> str:
    package = frontend_dir / "package.json"
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
        version = data.get("devDependencies", {}).get("vite")
    except (OSError, json.JSONDecodeError):
        return "unknown"
    return version or "unknown"


def compute_manifest(
    frontend_dir: Path = FRONTEND_DIR,
    web_dir: Path = WEB_DIR,
) -> dict:
    return {
        "frontend_tree_digest": frontend_tree_digest(frontend_dir),
        "build_digest": build_tree_digest(web_dir),
        "node_version": _tool_version("node", "--version"),
        "yarn_version": _tool_version("yarn", "--version"),
        "vite_version": _vite_version(frontend_dir),
    }


def write_manifest(
    frontend_dir: Path = FRONTEND_DIR,
    web_dir: Path = WEB_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> dict:
    manifest = compute_manifest(frontend_dir, web_dir)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def verify_manifest(
    frontend_dir: Path = FRONTEND_DIR,
    web_dir: Path = WEB_DIR,
    manifest_path: Path = MANIFEST_PATH,
) -> list[str]:
    """Return a list of mismatch descriptions; empty means verified."""

    if not manifest_path.is_file():
        return [f"missing manifest: {manifest_path}"]
    try:
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"manifest is invalid JSON: {error}"]

    actual = compute_manifest(frontend_dir, web_dir)
    mismatches = []
    for key in ("frontend_tree_digest", "build_digest"):
        if recorded.get(key) != actual[key]:
            mismatches.append(
                f"{key}: manifest records {recorded.get(key)!r}, "
                f"current tree computes {actual[key]!r}"
            )
    # 工具版本漂移会让同源码产出不同字节（如 workbox 的 sw.js 随 Node 运行时变化），
    # 所以构建工具链版本本身也是 provenance 的一部分。
    if recorded.get("node_version", "unknown") != "unknown" and (
        recorded.get("node_version") != actual["node_version"]
    ):
        mismatches.append(
            f"node_version: manifest records {recorded.get('node_version')!r}, "
            f"current environment is {actual['node_version']!r}"
        )
    return mismatches


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the manifest file")
    parser.add_argument(
        "--verify", action="store_true", help="Verify the current trees against the manifest"
    )
    args = parser.parse_args()

    if args.write == args.verify:
        parser.error("choose exactly one of --write or --verify")

    if args.write:
        manifest = write_manifest()
        print(f"Wrote {MANIFEST_PATH}")
        for key, value in manifest.items():
            print(f"  {key}: {value}")
        return

    mismatches = verify_manifest()
    if mismatches:
        for mismatch in mismatches:
            print(f"MISMATCH: {mismatch}", file=sys.stderr)
        print(
            "The frontend sources and the embedded build output do not match "
            "frontend-manifest.json. Rebuild and re-sync (see BUILD_AND_RELEASE.md).",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"Verified frontend sources and embedded output against {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
