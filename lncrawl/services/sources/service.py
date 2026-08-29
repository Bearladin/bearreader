import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
from threading import Event, Lock, Thread
import traceback
from typing import Dict, List, Optional, Type

from scraper import LAYERS, extract_host

from ...context import ctx
from ...core import Crawler
from ...core.tiers import LEGACY, describe, outranks
from ...exceptions import AbortedException, ServerErrors
from ...server.models import CrawlerIndex, CrawlerInfo, SourceDiagnosis, SourceItem
from ...utils.fts_store import FTSStore
from ...utils.text_tools import normalize
from ...utils.url_tools import normalize_url
from .helper import (
    create_crawler_info,
    create_source_item,
    import_crawlers,
    load_bundled_index,
)
from .tester import run_crawler_test

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class _SourceRegistry:
    index: CrawlerIndex
    rejected: Dict[str, str]
    crawlers: Dict[str, Type[Crawler]]
    info: Dict[str, CrawlerInfo]
    sources: Dict[str, SourceItem]
    store: FTSStore
    readers: int = 0
    retired: bool = False
    closed: bool = False


class _RegistryLease:
    def __init__(self, owner: "Sources", registry: _SourceRegistry) -> None:
        self._owner = owner
        self._registry = registry
        self._released = False

    def __enter__(self) -> _SourceRegistry:
        return self._registry

    def __exit__(self, *_args: object) -> None:
        self.release()

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._owner._release_registry(self._registry)


class Sources:
    def __init__(self) -> None:
        self._signal = Event()
        self._reload_lock = Lock()
        self._registry_lock = Lock()
        self._active_registry: Optional[_SourceRegistry] = None
        self._retired_registries: List[_SourceRegistry] = []

    def _acquire_registry(self) -> _RegistryLease:
        with self._registry_lock:
            registry = self._active_registry
            if registry is None or registry.closed:
                raise ServerErrors.source_not_loaded
            registry.readers += 1
        return _RegistryLease(self, registry)

    def registry_snapshot(self) -> _RegistryLease:
        return self._acquire_registry()

    def _release_registry(self, registry: _SourceRegistry) -> None:
        close_registry: Optional[_SourceRegistry] = None
        with self._registry_lock:
            registry.readers -= 1
            if registry.readers < 0:
                raise RuntimeError("Source registry reader count underflow")
            if registry.retired and registry.readers == 0 and not registry.closed:
                registry.closed = True
                self._retired_registries = [
                    item for item in self._retired_registries if item is not registry
                ]
                close_registry = registry
        if close_registry is not None:
            close_registry.store.close()

    def _retire_registry_locked(self, registry: _SourceRegistry) -> Optional[_SourceRegistry]:
        registry.retired = True
        if registry.readers == 0 and not registry.closed:
            registry.closed = True
            self._retired_registries = [
                item for item in self._retired_registries if item is not registry
            ]
            return registry
        if not registry.closed and not any(item is registry for item in self._retired_registries):
            self._retired_registries.append(registry)
        return None

    @property
    def retired_registry_count(self) -> int:
        with self._registry_lock:
            return len(self._retired_registries)

    @property
    def rejected(self) -> Dict[str, str]:
        with self.registry_snapshot() as registry:
            return dict(registry.rejected)

    @property
    def crawlers(self) -> Dict[str, Type[Crawler]]:
        with self.registry_snapshot() as registry:
            return dict(registry.crawlers)

    @property
    def info(self) -> Dict[str, CrawlerInfo]:
        with self.registry_snapshot() as registry:
            return dict(registry.info)

    @property
    def sources(self) -> Dict[str, SourceItem]:
        with self.registry_snapshot() as registry:
            return dict(registry.sources)

    @property
    def version(self) -> int:
        with self.registry_snapshot() as registry:
            return registry.index.v

    def is_rejected(self, url: str) -> Optional[str]:
        with self.registry_snapshot() as registry:
            return registry.rejected.get(extract_host(url))

    def close(self) -> None:
        self._signal.set()
        close_registries: List[_SourceRegistry] = []
        with self._registry_lock:
            active = self._active_registry
            self._active_registry = None
            registries = [*self._retired_registries]
            self._retired_registries = []
            if active is not None and not any(item is active for item in registries):
                registries.append(active)
            for registry in registries:
                closed = self._retire_registry_locked(registry)
                if closed is not None:
                    close_registries.append(closed)
        for registry in close_registries:
            registry.store.close()

    def ensure_load(self) -> None:
        return

    def load(self) -> None:
        if self._signal.is_set():
            self._signal = Event()
        self.load_index(load_bundled_index())

    def reload_local(self) -> int:
        self.load()
        self.ensure_load()
        logger.info("Reloaded local Chinese sources; remote synchronization is disabled")
        return self.version

    def _add_to_registry(self, registry: _SourceRegistry, crawler: Type[Crawler]) -> None:
        name = crawler.__name__
        crawler_id = getattr(crawler, "__id__")
        crawler_info = registry.index.crawlers.get(crawler_id)
        if crawler_info is None:
            logger.info(f"Found non-indexed local crawler: {name}")
            crawler_info = create_crawler_info(crawler)
            registry.index.crawlers[crawler_id] = crawler_info
            registry.index.supported.update({url: crawler_id for url in crawler_info.base_urls})

        current = registry.crawlers.get(crawler_id)
        if current is not None and not outranks(
            LEGACY,
            crawler_info.version,
            LEGACY,
            registry.info[crawler_id].version,
        ):
            return
        registry.info[crawler_id] = crawler_info
        registry.crawlers[crawler_id] = crawler

        for url in crawler.base_url:
            item = create_source_item(
                url,
                crawler_info,
                registry.rejected,
                LEGACY,
                getattr(crawler, "updated_at", None),
            )
            existing = registry.sources.get(item.domain)
            if existing is not None and not outranks(
                item.tier, item.version, existing.tier, existing.version
            ):
                continue
            registry.sources[item.domain] = item
            registry.store.insert(normalize_url(url), item.domain)

    def _build_local_registry(self, index: CrawlerIndex) -> _SourceRegistry:
        rejected = {extract_host(url): reason for url, reason in index.rejected.items()}
        registry = _SourceRegistry(
            index=index,
            rejected=rejected,
            crawlers={},
            info={},
            sources={},
            store=FTSStore(),
        )
        try:
            # Bundled sources are activated strictly from the filtered index rather than by
            # globbing the directory, so a stale crawler file left behind by an upgrade is
            # never loaded. User Chinese sources remain glob-driven so local additions keep
            # working without rebuilding the index.
            bundled_root = ctx.config.crawler.local_chinese_sources
            for info in index.crawlers.values():
                if self._signal.is_set():
                    raise AbortedException()
                parts = Path(info.file_path).parts
                if len(parts) < 3 or parts[0] != "sources":
                    logger.warning(
                        f"Skipping bundled crawler with unexpected path: {info.file_path}"
                    )
                    continue
                source_file = bundled_root.parent.joinpath(*parts[1:])
                if not source_file.is_file():
                    logger.warning(f"Bundled crawler file missing: {source_file}")
                    continue
                for crawler in import_crawlers(source_file, strict=True):
                    self._add_to_registry(registry, crawler)

            for file in sorted(ctx.config.crawler.user_chinese_sources.glob("**/*.py")):
                if self._signal.is_set():
                    raise AbortedException()
                for crawler in import_crawlers(file, strict=False):
                    self._add_to_registry(registry, crawler)
        except Exception:
            registry.store.close()
            raise
        return registry

    def load_index(self, index: CrawlerIndex) -> None:
        with self._reload_lock:
            registry = self._build_local_registry(index)
            if self._signal.is_set():
                registry.store.close()
                return
            close_registry: Optional[_SourceRegistry] = None
            with self._registry_lock:
                if self._signal.is_set():
                    registry.store.close()
                    return
                previous = self._active_registry
                self._active_registry = registry
                if previous is not None:
                    close_registry = self._retire_registry_locked(previous)
            if close_registry is not None:
                close_registry.store.close()

    def list(
        self,
        query: Optional[str] = None,
        *,
        include_rejected: bool = False,
        can_search: Optional[bool] = None,
        can_login: Optional[bool] = None,
        has_mtl: Optional[bool] = None,
        has_manga: Optional[bool] = None,
    ) -> List[SourceItem]:
        self.ensure_load()
        with self.registry_snapshot() as registry:
            domains = registry.store.search(normalize(query)) if query else None
            if domains is not None and len(domains) == 0:
                return []
            return [
                item
                for item in registry.sources.values()
                if all(
                    [
                        domains is None or item.domain in domains,
                        has_mtl is None or item.has_mtl is has_mtl,
                        has_manga is None or item.has_manga is has_manga,
                        can_login is None or item.can_login is can_login,
                        can_search is None or item.can_search is can_search,
                        include_rejected or not item.is_disabled,
                    ]
                )
            ]

    @staticmethod
    def _get_domain(registry: _SourceRegistry, url: str) -> str:
        host = extract_host(url)
        if not host:
            raise ServerErrors.invalid_url
        if host in registry.rejected:
            raise ServerErrors.host_rejected.with_extra(registry.rejected[host])
        return host

    @staticmethod
    def _get_source(registry: _SourceRegistry, domain: str) -> SourceItem:
        if domain.startswith("www."):
            domain = domain[4:]
        source = registry.sources.get(domain)
        if not source:
            raise ServerErrors.no_crawler.with_extra(domain)
        return source

    def get_domain(self, url: str) -> str:
        with self.registry_snapshot() as registry:
            return self._get_domain(registry, url)

    def get_source(self, domain: str) -> SourceItem:
        self.ensure_load()
        with self.registry_snapshot() as registry:
            return self._get_source(registry, domain)

    def get_info(self, domain: str) -> CrawlerInfo:
        with self.registry_snapshot() as registry:
            source = self._get_source(registry, domain)
            return registry.info[source.crawler_id]

    def diagnose(self, domain: str) -> SourceDiagnosis:
        """Why *domain* is or is not working.

        Reports a rejection rather than refusing on one, unlike every crawl path — a
        rejected host is the one whose diagnosis is most worth reading — and answers
        for a rejected host that has no crawler at all, which is most of them.
        """
        self.ensure_load()
        with self.registry_snapshot() as registry:
            if domain.startswith("www."):
                domain = domain[4:]
            rejected = registry.rejected.get(domain)
            source = registry.sources.get(domain)
            if source is None and rejected is None:
                raise ServerErrors.no_crawler.with_extra(domain)
            url = source.url if source else f"https://{domain}/"

        health = ctx.health.reasons(domain)
        result = SourceDiagnosis(
            domain=domain,
            url=url,
            rejected=rejected,
            is_disabled=source.is_disabled if source else True,
            disable_reason=source.disable_reason if source else rejected,
            health=health,
            samples={reason: ctx.health.samples(domain, reason) for reason in health},
            explain=ctx.scraper.explain(url),
        )

        profile = ctx.scraper.knows(url)
        if profile is None:
            return result

        result.known = True
        result.tier = profile.tier
        result.interval = profile.interval
        result.successes = profile.successes
        result.failures = profile.failures
        result.consecutive_failures = profile.consecutive_failures
        result.has_clearance = profile.clearance_for(url) is not None

        layer = profile.binding
        if layer is not None:
            facts = LAYERS[layer]
            result.binding_layer = int(layer)
            result.binding_layer_name = str(layer)
            result.reads = facts.trait.value
            result.stance = facts.stance.value
            result.summary = facts.summary
        return result

    def get_crawler(self, domain: str) -> Type[Crawler]:
        with self.registry_snapshot() as registry:
            source = self._get_source(registry, domain)
            return registry.crawlers[source.crawler_id]

    def find_crawler(self, url: str) -> Type[Crawler]:
        self.ensure_load()
        with self.registry_snapshot() as registry:
            domain = self._get_domain(registry, url)
            source = self._get_source(registry, domain)
            return registry.crawlers[source.crawler_id]

    def init_crawler(
        self,
        url: str,
        parser: Optional[str] = None,
        timeout: Optional[float] = None,
        probe: bool = False,
    ) -> Crawler:
        with self.registry_snapshot() as registry:
            domain = self._get_domain(registry, url)
            source = self._get_source(registry, domain)
            constructor = registry.crawlers[source.crawler_id]

        # create instance
        ctx.logger.debug(
            f"Creating crawler instance for {url}: {describe(source.tier, source.file_path)}"
        )
        open_session = ctx.scraper.probe if probe else ctx.scraper.open
        crawler = constructor(
            origin=source.url,
            parser=parser,
            scraper=open_session(
                source.url,
                parser=parser,
                rate_limit=constructor.request_rate_limit,
                timeout=timeout,
            ),
        )

        if not crawler.language:
            crawler.language = source.language

        crawler.initialize()
        return crawler

    async def test_source(self, url: str, content: str):
        # WARNING: This function executes arbitrary Python source code directly in the
        # running process. It is intended solely for trusted developer use. Never pass
        # unverified or user-supplied content — doing so is a critical security risk
        # (remote code execution). USE WITH EXTREME CAUTION.
        event = Event()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str] = asyncio.Queue()

        def emit(item: str = "") -> None:
            loop.call_soon_threadsafe(queue.put_nowait, item + "\n")

        def run():
            try:
                run_crawler_test(url, content, emit)
                emit("\nTEST PASSED!")
            except Exception as e:
                emit(f"<!> {repr(e)}\n{traceback.format_exc()}")
                emit("\nTEST FAILED!")
            finally:
                event.set()
                emit("END")

        Thread(target=run, daemon=True).start()

        while True:
            item = await queue.get()
            if event.is_set() and item == "END\n":
                break
            yield item
