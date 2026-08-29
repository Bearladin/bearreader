from difflib import SequenceMatcher
from typing import List

from ....context import ctx
from ....core import SearchResult
from ....enums import JobType
from ._base import AbortedException, BatchHandler, HandlerException


class SearchSourceHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.SEARCH_SOURCE

    def run(self) -> None:
        domain = self.job.extra.get("domain")
        if not domain:
            raise HandlerException("未指定书源域名")

        query = self.job.extra.get("query") or ""
        if not query or len(query) < 2:
            raise HandlerException("搜索关键词至少需要 2 个字符")

        if not self.job.is_running:
            self._set_running()

        results = self._get_search_results(query, domain)
        if not results:
            return
        if not ctx.tier.search_can_fetch_novel_metadata(self.user):
            return

        for job in self.children:
            if job.type == JobType.NOVEL_BATCH:
                return
        else:
            if self.signal.is_set():
                raise AbortedException()
            ctx.jobs.fetch_many_novels(
                self.user,
                *(item.url for item in results),
                full=False,
                parent_id=self.job.id,
            )

    def _get_search_results(self, query: str, domain: str) -> List[SearchResult]:
        existing = self.job.extra.get("search_results")
        if existing:
            return [SearchResult(**item) for item in self.job.extra["search_results"]]

        # get search results
        results = ctx.crawler.search_novel(
            user_id=self.user.id,
            query=query,
            domain=domain,
            signal=self.signal,
        )
        if not results:
            return []

        self._set_extra(
            search_results=[result.to_dict() for result in results],
        )
        if self.signal.is_set():
            raise AbortedException()

        # aggregate search results in the root job (atomic read-modify-write)
        self._aggregate_results(query, results)
        return results

    def _aggregate_results(self, query: str, results: List[SearchResult]) -> None:
        root = ctx.jobs.get_root(self.job.id)
        if not root or root.id == self.job.id:
            return

        def inject_new_results(extra: dict):
            current = {item["url"]: item for item in extra.get("search_results") or []}
            for item in results:
                current[item["url"]] = item

            combined = list(current.values())
            combined.sort(key=lambda x: -SequenceMatcher(a=x["title"], b=query).ratio())

            extra["search_results"] = combined

        ctx.jobs.update_extra(root.id, inject_new_results)
