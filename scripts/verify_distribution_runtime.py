import argparse
import asyncio
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable, List
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_ENV = "XIAOXIONG_NOVEL_DATA_PATH"

_FIXTURE = """\
from lncrawl.core import SoupTemplate


class LocalFixtureCrawler(SoupTemplate):
    base_url = ["https://fixture-zh.example/"]
    language = "zh"
"""

_IGNORED_FIXTURE = """\
from lncrawl.core import SoupTemplate


class IgnoredFixtureCrawler(SoupTemplate):
    base_url = ["https://fixture-en.example/"]
    language = "en"
"""

_STALE_FIXTURE = """\
from lncrawl.core import SoupTemplate


class StaleUpgradeCrawler(SoupTemplate):
    base_url = ["https://stale-upgrade.example/"]
    language = "zh"
"""


def _write_fixture(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _verify_stale_bundled_ignored() -> None:
    import shutil
    import time as _time

    from lncrawl.context import ctx
    from lncrawl.server.models import CrawlerIndex
    from lncrawl.services.sources.helper import create_crawler_info, import_crawlers
    from lncrawl.services.sources.service import Sources

    build_root = PROJECT_ROOT / "build"
    build_root.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="xiaoxiong-stale-", dir=build_root) as temporary:
        root = Path(temporary)
        bundled_sources = root / "bundled" / "sources"
        bundled_zh = bundled_sources / "zh"
        bundled_zh.mkdir(parents=True)
        shutil.copy2(PROJECT_ROOT / "sources" / "zh" / "mayiwsk.py", bundled_zh / "mayiwsk.py")
        stale = bundled_zh / "stale_upgrade_fixture.py"
        stale.write_text(_STALE_FIXTURE, encoding="utf-8")

        user_zh = root / "user" / "zh"
        user_zh.mkdir(parents=True)

        mayiwsk_crawler = list(import_crawlers(bundled_zh / "mayiwsk.py", strict=True))[0]
        info = create_crawler_info(mayiwsk_crawler, source_root=bundled_sources)
        index = CrawlerIndex(
            v=int(_time.time()),
            app=None,
            contributors={},
            rejected={},
            supported={url: info.id for url in info.base_urls},
            crawlers={info.id: info},
        )

        saved_local = ctx.config.crawler.local_chinese_sources
        saved_user = ctx.config.crawler.user_chinese_sources
        sources = Sources()
        try:
            ctx.config.crawler.__dict__["local_chinese_sources"] = bundled_zh
            ctx.config.crawler.__dict__["user_chinese_sources"] = user_zh
            sources.load_index(index)
            with sources.registry_snapshot() as registry:
                assert "mayiwsk.com" in registry.sources
                assert all(
                    crawler.__name__ != "StaleUpgradeCrawler"
                    for crawler in registry.crawlers.values()
                )
                assert "stale-upgrade.example" not in registry.sources
        finally:
            sources.close()
            ctx.config.crawler.__dict__["local_chinese_sources"] = saved_local
            ctx.config.crawler.__dict__["user_chinese_sources"] = saved_user


def _verify_registry_leases(sources: Any, closed_error: type[BaseException]) -> None:
    with sources.registry_snapshot() as old_registry:
        old_count = old_registry.store.count()
        assert old_count > 0
        sources.reload_local()
        assert old_registry.retired
        assert old_registry.store.count() == old_count
        assert sources.retired_registry_count == 1

    assert old_registry.closed
    assert sources.retired_registry_count == 0
    try:
        old_registry.store.count()
    except (sqlite3.ProgrammingError, closed_error):
        pass
    else:
        raise AssertionError("Retired registry FTS store remained open after lease release")
    for _ in range(3):
        sources.reload_local()
        assert sources.retired_registry_count == 0


def verify() -> None:
    build_root = PROJECT_ROOT / "build"
    build_root.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="xiaoxiong-runtime-", dir=build_root) as temporary:
        data_dir = Path(temporary) / "XiaoXiongNovel"
        previous = os.environ.get(DATA_ENV)
        os.environ[DATA_ENV] = str(data_dir)
        try:
            from lncrawl.context import ctx
            from lncrawl.exceptions import AbortedException, ServerError, ServerErrors
            from lncrawl.server.api.admin import update as update_sources_route
            from lncrawl.services.github import GitHubService
            from lncrawl.services.sources.helper import load_source
            from scripts.build_distribution_sources import build_sources as build_offline_index

            def english_source_url() -> str:
                index = load_source(PROJECT_ROOT / "sources" / "_index.json")
                for info in index.crawlers.values():
                    if info.file_path.startswith("sources/en/"):
                        return info.base_urls[0]
                raise AssertionError("The repository index has no English source fixture")

            def assert_no_crawler(url: str) -> None:
                try:
                    ctx.sources.find_crawler(url)
                except ServerError as error:
                    assert error.detail == ServerErrors.no_crawler.detail
                else:
                    raise AssertionError(f"Expected no-crawler error for {url}")

            def assert_host_rejected(action: Callable[[], Any]) -> None:
                try:
                    action()
                except ServerError as error:
                    assert error.detail == ServerErrors.host_rejected.detail
                else:
                    raise AssertionError("Rejected host unexpectedly loaded an active crawler")

            def assert_rejected_leyuedu() -> None:
                url = "https://tw.27k.net/"
                reason = "Domain now hosts an unrelated service"
                assert ctx.sources.is_rejected(url) == reason
                with ctx.sources.registry_snapshot() as registry:
                    source = registry.sources.get("tw.27k.net")
                    assert source is not None
                    assert source.is_disabled
                    assert source.disable_reason == reason
                    assert registry.crawlers[source.crawler_id].__name__ == "LeYueDu"
                assert all(source.domain != "tw.27k.net" for source in ctx.sources.list())
                assert_host_rejected(lambda: ctx.sources.find_crawler(url))
                assert_host_rejected(lambda: ctx.sources.init_crawler(url))

            ctx.config.load()

            # Build a complete offline index and point the runtime at it. This mirrors the
            # frozen bundle, which packages the offline-built index including mayiwsk/nieba;
            # the repository's committed index is stale and must not drive bundled loading.
            distribution_output = Path(temporary) / "distribution"
            build_offline_index(
                source_root=PROJECT_ROOT / "sources",
                output_root=distribution_output,
                metadata_index=PROJECT_ROOT / "sources" / "_index.json",
            )
            ctx.config.crawler.__dict__["local_index_file"] = (
                distribution_output / "sources" / "_index.json"
            )

            _write_fixture(ctx.config.crawler.user_chinese_sources / "fixture_zh.py", _FIXTURE)
            _write_fixture(
                ctx.config.crawler.user_sources / "en" / "fixture_en.py",
                _IGNORED_FIXTURE,
            )

            remote_calls: List[tuple[tuple[Any, ...], dict[str, Any]]] = []

            def fail_on_remote_source_fetch(*args: Any, **kwargs: Any) -> None:
                remote_calls.append((args, kwargs))
                raise AssertionError("Runtime attempted to fetch an online source index")

            try:
                with patch.object(
                    GitHubService,
                    "fetch_online_source",
                    fail_on_remote_source_fetch,
                    create=True,
                ):
                    ctx.sources.load()
                    with ctx.sources.registry_snapshot() as registry:
                        assert all(
                            info.file_path.startswith("sources/zh/")
                            for info in registry.info.values()
                        )
                        assert registry.sources["mayiwsk.com"].can_search
                        assert registry.sources["nieba.net"].file_path.endswith("nieba.py")
                        assert registry.sources["fixture-zh.example"].file_path.endswith(
                            "fixture_zh.py"
                        )
                        assert "fixture-en.example" not in registry.sources

                    assert_no_crawler(english_source_url())
                    assert_no_crawler("https://unknown.invalid/")
                    assert_rejected_leyuedu()

                    _write_fixture(
                        ctx.config.crawler.user_chinese_sources / "broken_fixture.py",
                        "raise RuntimeError('broken local source')\n",
                    )
                    ctx.sources.reload_local()
                    assert ctx.sources.get_source("fixture-zh.example").file_path.endswith(
                        "fixture_zh.py"
                    )
                    _verify_registry_leases(ctx.sources, AbortedException)

                    original_reload = ctx.sources.reload_local
                    reload_calls: List[None] = []

                    def record_reload() -> int:
                        reload_calls.append(None)
                        return original_reload()

                    ctx.sources.reload_local = record_reload
                    try:
                        assert asyncio.run(update_sources_route()) == ctx.sources.version
                    finally:
                        ctx.sources.reload_local = original_reload
                    assert len(reload_calls) == 1

                assert not remote_calls

                _verify_stale_bundled_ignored()
            finally:
                ctx.sources.close()
        finally:
            if previous is None:
                os.environ.pop(DATA_ENV, None)
            else:
                os.environ[DATA_ENV] = previous


def probe_existing_override() -> None:
    build_root = PROJECT_ROOT / "build"
    build_root.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="xiaoxiong-runtime-sentinel-", dir=build_root) as temporary:
        sentinel_dir = Path(temporary) / "caller-override"
        sentinel_dir.mkdir()
        sentinel = sentinel_dir / "must-survive.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        environment = os.environ.copy()
        environment[DATA_ENV] = str(sentinel_dir)
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--run"],
            cwd=PROJECT_ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            output = (result.stdout + result.stderr).strip()
            raise AssertionError(f"Runtime verifier subprocess failed: {output}")
        assert sentinel.read_text(encoding="utf-8") == "preserve"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the local XiaoXiong Chinese source runtime"
    )
    parser.add_argument("--run", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.run:
        verify()
    else:
        probe_existing_override()
        print("Verified local Chinese source runtime without touching caller data paths")


if __name__ == "__main__":
    main()
