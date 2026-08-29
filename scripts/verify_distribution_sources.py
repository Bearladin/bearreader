import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lncrawl.services.sources.helper import import_crawlers, load_source  # noqa: E402
from scripts.build_distribution_sources import validate_sources  # noqa: E402


def verify(output_root: Path) -> None:
    validate_sources(output_root)
    source_root = output_root.absolute() / "sources"
    index = load_source(source_root / "_index.json")
    crawler_count = len(index.crawlers)
    language_dirs = {
        path.parts[1] for path in map(Path, (info.file_path for info in index.crawlers.values()))
    }
    indexed_files = {info.file_path for info in index.crawlers.values()}
    staged_files = {
        f"sources/{file.relative_to(source_root).as_posix()}"
        for file in (source_root / "zh").glob("**/*.py")
        if not file.name.startswith("_")
    }

    assert crawler_count > 0
    assert language_dirs == {"zh"}
    assert all(info.file_path.startswith("sources/zh/") for info in index.crawlers.values())
    assert "https://www.mayiwsk.com/" in index.supported
    assert "https://www.nieba.net/" in index.supported
    assert any(
        info.can_search and "mayiwsk.py" in info.file_path for info in index.crawlers.values()
    )
    assert staged_files == indexed_files

    for file in (source_root / "zh").glob("**/*.py"):
        list(import_crawlers(file, strict=True))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify an offline XiaoXiong Chinese source distribution"
    )
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify(args.output)
    print(f"Verified Chinese source distribution: {args.output}")


if __name__ == "__main__":
    main()
