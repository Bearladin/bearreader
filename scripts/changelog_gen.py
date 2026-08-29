"""Sync CHANGELOG.md with the GitHub Releases of the project.

Fetches every published release via the `gh` CLI, normalises the release body
into Keep a Changelog style, and merges them into CHANGELOG.md. Versions that
already exist in CHANGELOG.md are kept verbatim (so hand-curated entries are
preserved); only missing versions are injected. Entries are sorted by semantic
version, newest first.

Usage:
    uv run python scripts/changelog_gen.py            # update CHANGELOG.md
    uv run python scripts/changelog_gen.py --check     # print without writing
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

REPO = "lncrawl/lightnovel-crawler"
ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"

HEADER = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
"""

VERSION_HEADING = re.compile(r"^## \[(?P<ver>[^\]]+)\](?:\s*-\s*(?P<date>.+))?\s*$")


def run_gh(args: List[str]) -> str:
    """Run a gh command and return stdout, exiting on failure."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(f"gh command failed: gh {' '.join(args)}")
    return result.stdout


def fetch_releases() -> List[dict]:
    """Fetch all published releases (paginated) sorted newest first."""
    raw = run_gh(
        [
            "api",
            f"repos/{REPO}/releases",
            "--paginate",
            "-q",
            ".[] | {tag: .tag_name, date: .published_at, draft: .draft, "
            "prerelease: .prerelease, body: .body, url: .html_url}",
        ]
    )
    releases = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return [r for r in releases if not r.get("draft")]


def version_key(ver: str) -> Tuple[int, ...]:
    """Sort key from a version string like '4.10.0' -> (4, 10, 0)."""
    parts = re.findall(r"\d+", ver)
    return tuple(int(p) for p in parts) if parts else (0,)


def clean_body(body: str) -> str:
    """Normalise a GitHub release body into changelog section content.

    - drops the redundant "## What's Changed" wrapper heading
    - removes the auto-generated "New Contributors" and "Full Changelog" footer
    - demotes stray level-1/level-2 headings to level-3 so version headers
      (level-2) stay the document's section markers
    """
    if not body:
        return ""

    text = body.replace("\r\n", "\n").strip()

    # Drop everything from the auto-generated footer onward.
    text = re.split(r"^#+\s*New Contributors\b", text, maxsplit=1, flags=re.M)[0]
    text = re.split(r"^\*\*Full Changelog\*\*", text, maxsplit=1, flags=re.M)[0]

    src = text.split("\n")
    lines: List[str] = []
    i = 0
    while i < len(src):
        line = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""

        # Convert Setext headings ("Title\n----" / "Title\n====") to level-3.
        if (
            line.strip()
            and re.match(r"^[=-]{2,}\s*$", nxt)
            and not line.lstrip().startswith(("-", "*", "#"))
        ):
            lines.append(f"### {line.strip()}")
            i += 2
            continue

        # Drop the redundant wrapper heading entirely.
        if re.match(r"^#+\s*What's Changed\s*$", line):
            i += 1
            continue

        # Demote level-1/level-2 headings to level-3 (## is reserved for versions).
        m = re.match(r"^(#{1,2})\s+(.*)$", line)
        if m:
            line = f"### {m.group(2).strip()}"
        lines.append(line)
        i += 1

    return "\n".join(lines).strip()


def parse_existing(content: str) -> Tuple[str, "Dict[str, str]"]:
    """Split CHANGELOG into (header, {version: full_block_text})."""
    blocks: Dict[str, str] = {}
    matches = list(VERSION_HEADING.finditer(content))
    if not matches:
        return content.rstrip() + "\n", blocks

    header = content[: matches[0].start()].rstrip() + "\n"
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        ver = m.group("ver").strip().lstrip("vV")
        block = content[m.start() : end].strip()
        # Drop trailing reference-link definitions (regenerated on write).
        block = re.sub(r"(?m)^\[[^\]]+\]:\s*http\S+\s*$", "", block).strip()
        blocks[ver] = block
    return header, blocks


def make_block(ver: str, date: Optional[str], body: str, url: str) -> Optional[str]:
    """Render a single version block, or None if the release has no notes."""
    content = clean_body(body)
    if not content:
        return None
    day = date.split("T")[0] if date else ""
    heading = f"## [{ver}]" + (f" - {day}" if day else "")
    return f"{heading}\n\n{content}"


def build_changelog() -> str:
    releases = fetch_releases()
    _, existing = (
        parse_existing(CHANGELOG.read_text(encoding="utf-8"))
        if CHANGELOG.exists()
        else (HEADER, {})
    )

    # Keep curated entries verbatim, but drop stale "no release notes" placeholders.
    blocks: Dict[str, str] = {v: b for v, b in existing.items() if "_No release notes" not in b}
    for rel in releases:
        ver = rel["tag"].strip().lstrip("vV")
        if ver in blocks:
            continue  # already documented — don't overwrite curated text
        block = make_block(ver, rel.get("date"), rel.get("body") or "", rel.get("url", ""))
        if block is not None:  # skip releases with no notes
            blocks[ver] = block

    ordered = sorted(blocks, key=version_key, reverse=True)
    body = "\n\n".join(blocks[v] for v in ordered)
    links = build_links(ordered)
    return f"{HEADER}\n{body}\n\n{links}\n"


def build_links(ordered: List[str]) -> str:
    """Build reference-link definitions: each version compares to its predecessor."""
    lines: List[str] = []
    for i, ver in enumerate(ordered):
        if i + 1 < len(ordered):
            prev = ordered[i + 1]
            url = f"https://github.com/{REPO}/compare/v{prev}...v{ver}"
        else:  # oldest entry has no predecessor — point at its own tag
            url = f"https://github.com/{REPO}/releases/tag/v{ver}"
        lines.append(f"[{ver}]: {url}")
    return "\n".join(lines)


def main() -> None:
    check = "--check" in sys.argv
    output = build_changelog()
    if check:
        sys.stdout.write(output)
        return
    CHANGELOG.write_text(output, encoding="utf-8")
    versions = output.count("\n## [")
    print(
        f"Wrote {CHANGELOG.relative_to(ROOT)} with {versions} version entries "
        f"({datetime.now():%Y-%m-%d %H:%M})."
    )


if __name__ == "__main__":
    main()
