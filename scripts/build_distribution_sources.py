import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
from typing import Dict, Iterable, List, Optional, Set, Tuple, Type

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# A directory the builder created and owns. Deleting an existing output directory is
# only allowed when this marker is present, so an arbitrary unrelated directory that
# happens to sit under build/ is never recursively removed.
OUTPUT_MARKER = ".xiaoxiong-distribution-output"
BUILD_ROOT = PROJECT_ROOT / "build"

from scraper import extract_host  # noqa: E402

from lncrawl.core import Crawler  # noqa: E402
from lncrawl.server.models import CrawlerIndex, CrawlerInfo  # noqa: E402
from lncrawl.services.sources.helper import (  # noqa: E402
    create_crawler_info,
    import_crawlers,
    load_source,
    save_source,
)


def _strict_import(file: Path) -> List[Type[Crawler]]:
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return list(import_crawlers(file, strict=True))
    finally:
        sys.dont_write_bytecode = previous


def _committed_timestamp(file: Path, source_root: Path) -> int:
    try:
        repository_root = source_root.parent
        relative_file = file.relative_to(repository_root)
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository_root),
                "log",
                "-1",
                "--format=%ct",
                "--",
                str(relative_file),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        timestamp = result.stdout.strip()
        if result.returncode == 0 and timestamp.isdigit():
            return int(timestamp)
    except (OSError, ValueError):
        pass
    return int(file.stat().st_mtime)


def _historical_info(crawler: CrawlerInfo, previous: CrawlerIndex) -> Optional[CrawlerInfo]:
    if crawler.id in previous.crawlers:
        return previous.crawlers[crawler.id]
    return next(
        (info for info in previous.crawlers.values() if info.file_path == crawler.file_path),
        None,
    )


def _retained_rejections(rejected_file: Path, retained_hosts: Set[str]) -> Dict[str, str]:
    if not rejected_file.is_file():
        return {}
    rejected = json.loads(rejected_file.read_text(encoding="utf-8"))
    if not isinstance(rejected, dict):
        raise ValueError(f"Rejected source file is not an object: {rejected_file}")
    return {
        str(url): str(reason)
        for url, reason in rejected.items()
        if extract_host(str(url)) in retained_hosts
    }


def _copy_sources(source_root: Path, staged_sources: Path) -> List[Path]:
    source_init = source_root / "__init__.py"
    if not source_init.is_file():
        raise ValueError(f"Missing sources package file: {source_init}")

    shutil.copy2(source_init, staged_sources / "__init__.py")
    source_files = sorted((source_root / "zh").glob("**/*.py"))
    if not source_files:
        raise ValueError(f"No Chinese source files found in {source_root / 'zh'}")

    for file in source_files:
        destination = staged_sources / file.relative_to(source_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, destination)
    return source_files


def _normalized_info(
    files: Iterable[Path], source_root: Path, previous: CrawlerIndex
) -> Dict[str, CrawlerInfo]:
    crawlers: Dict[str, CrawlerInfo] = {}
    for file in files:
        for crawler in _strict_import(file):
            info = create_crawler_info(crawler, source_root=source_root)
            if info.id in crawlers:
                raise ValueError(f"Duplicate crawler ID {info.id}: {info.file_path}")

            historical = _historical_info(info, previous)
            if historical is None:
                info.version = _committed_timestamp(file, source_root)
                info.total_commits = 1
                info.contributors = []
            else:
                info.version = historical.version
                info.total_commits = historical.total_commits
                info.contributors = historical.contributors
            crawlers[info.id] = info
            crawlers[info.id] = info
    if not crawlers:
        raise ValueError(f"No crawler classes found in {source_root / 'zh'}")
    return crawlers


def _supported_urls(crawlers: Iterable[CrawlerInfo]) -> Dict[str, str]:
    supported: Dict[str, str] = {}
    for info in crawlers:
        for url in info.base_urls:
            existing = supported.get(url)
            if existing is not None and existing != info.id:
                raise ValueError(f"Conflicting base URL {url}: {existing} and {info.id}")
            supported[url] = info.id
    return supported


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_build_paths(
    source_root: Path,
    output_root: Path,
    metadata_index: Path,
) -> Tuple[Path, Path, Path]:
    source_root = source_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    metadata_index = metadata_index.expanduser().resolve()

    if _is_within(output_root, source_root) or _is_within(source_root, output_root):
        raise ValueError(
            "Distribution source output must not equal, contain, or be contained by the source "
            f"root: source={source_root}, output={output_root}"
        )
    if _is_within(metadata_index, output_root):
        raise ValueError(
            "Distribution source metadata must not be inside the output directory because "
            f"building replaces that directory: metadata={metadata_index}, output={output_root}"
        )

    build_root = BUILD_ROOT.resolve()
    if output_root == build_root or not _is_within(output_root, build_root):
        raise ValueError(
            "Distribution source output must be inside the repository build directory and "
            f"not the build root itself: output={output_root}, build={build_root}"
        )
    return source_root, output_root, metadata_index


def _remove_managed_output(output_root: Path) -> None:
    if not output_root.exists():
        return
    marker = output_root / OUTPUT_MARKER
    if not marker.is_file():
        raise ValueError(
            f"Refusing to replace an unmanaged directory {output_root}. The output directory "
            f"must be a managed XiaoXiong distribution output (containing {OUTPUT_MARKER})."
        )
    shutil.rmtree(output_root)


def build_sources(
    source_root: Path,
    output_root: Path,
    metadata_index: Path,
) -> CrawlerIndex:
    source_root, output_root, metadata_index = _validate_build_paths(
        source_root,
        output_root,
        metadata_index,
    )
    if not (source_root / "zh").is_dir():
        raise ValueError(f"Chinese source directory does not exist: {source_root / 'zh'}")
    if not metadata_index.is_file():
        raise ValueError(f"Source metadata index does not exist: {metadata_index}")

    previous = load_source(metadata_index)
    source_files = sorted((source_root / "zh").glob("**/*.py"))
    crawlers = _normalized_info(source_files, source_root, previous)
    supported = _supported_urls(crawlers.values())
    retained_hosts = {extract_host(url) for url in supported}
    rejected = _retained_rejections(source_root / "_rejected.json", retained_hosts)
    contributors = {
        name: details
        for name, details in previous.contributors.items()
        if any(name in info.contributors for info in crawlers.values())
    }
    index = CrawlerIndex(
        v=int(time.time()),
        app=None,
        contributors=contributors,
        rejected=dict(sorted(rejected.items())),
        supported=dict(sorted(supported.items())),
        crawlers=dict(sorted(crawlers.items())),
    )

    _remove_managed_output(output_root)
    output_root.mkdir(parents=True)
    (output_root / OUTPUT_MARKER).write_text(
        "Managed XiaoXiong distribution output.\n",
        encoding="utf-8",
    )
    staged_sources = output_root / "sources"
    staged_sources.mkdir(parents=True)
    _copy_sources(source_root, staged_sources)
    save_source(staged_sources / "_index.json", index)
    (staged_sources / "_rejected.json").write_text(
        json.dumps(index.rejected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validate_sources(output_root)
    return index


def _reject_duplicate_keys(pairs: List[Tuple[str, object]]) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key in staged index: {key}")
        result[key] = value
    return result


def _source_path(output_root: Path, file_path: str) -> Path:
    portable_path = PurePosixPath(file_path)
    if (
        len(portable_path.parts) < 3
        or portable_path.parts[0] != "sources"
        or portable_path.parts[1] != "zh"
    ):
        raise ValueError(f"Index path is outside sources/zh/: {file_path}")
    return output_root.joinpath(*portable_path.parts)


def validate_sources(output_root: Path) -> None:
    output_root = output_root.absolute()
    source_root = output_root / "sources"
    index_file = source_root / "_index.json"
    if not index_file.is_file():
        raise ValueError(f"Missing staged source index: {index_file}")
    if not source_root.is_dir():
        raise ValueError(f"Missing staged sources directory: {source_root}")

    language_dirs = {
        child.name
        for child in source_root.iterdir()
        if child.is_dir() and not child.name.startswith("_")
    }
    if language_dirs != {"zh"}:
        raise ValueError(f"Staged source languages must be only zh, found: {sorted(language_dirs)}")

    raw_index = json.loads(
        index_file.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    index = CrawlerIndex.model_validate(raw_index)
    if not index.crawlers:
        raise ValueError("Staged index contains zero crawlers")

    imported: Dict[str, CrawlerInfo] = {}
    indexed_files: Set[str] = set()
    for crawler_id, info in index.crawlers.items():
        if crawler_id != info.id:
            raise ValueError(f"Crawler index key does not match crawler ID: {crawler_id}")
        source_file = _source_path(output_root, info.file_path)
        if not source_file.is_file():
            raise ValueError(f"Index references a missing crawler file: {info.file_path}")
        indexed_files.add(info.file_path)

    source_files = sorted((source_root / "zh").glob("**/*.py"))
    for source_file in source_files:
        for crawler in _strict_import(source_file):
            info = create_crawler_info(crawler, source_root=source_root)
            if info.id in imported:
                raise ValueError(f"Duplicate staged crawler ID {info.id}: {info.file_path}")
            imported[info.id] = info

    if not imported:
        raise ValueError("Staged source files contain zero crawlers")
    missing = set(imported).difference(index.crawlers)
    extra = set(index.crawlers).difference(imported)
    if missing or extra:
        raise ValueError(
            f"Staged crawler index differs from files; missing={sorted(missing)}, extra={sorted(extra)}"
        )

    staged_files = {
        f"sources/{file.relative_to(source_root).as_posix()}"
        for file in source_files
        if not file.name.startswith("_")
    }
    if staged_files != indexed_files:
        raise ValueError(
            f"Staged files differ from indexed files; staged={sorted(staged_files)}, "
            f"indexed={sorted(indexed_files)}"
        )

    expected_supported = _supported_urls(imported.values())
    if index.supported != expected_supported:
        raise ValueError("Staged supported URLs do not match imported crawlers")
    retained_hosts = {extract_host(url) for url in expected_supported}
    invalid_rejections = [url for url in index.rejected if extract_host(url) not in retained_hosts]
    if invalid_rejections:
        raise ValueError(
            f"Staged rejected URLs do not belong to retained sources: {invalid_rejections}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build an offline XiaoXiong Chinese source distribution"
    )
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "sources")
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_root = args.source.resolve()
    metadata_index = args.metadata or source_root / "_index.json"
    index = build_sources(source_root, args.output, metadata_index)
    print(
        f"Built {len(index.crawlers)} Chinese crawlers and "
        f"{len(index.supported)} supported URLs in {args.output}"
    )


if __name__ == "__main__":
    main()
