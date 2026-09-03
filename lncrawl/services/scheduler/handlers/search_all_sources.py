from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler, HandlerException


class SearchAllSourcesHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.SEARCH_ALL_SOURCES

    def run(self) -> None:
        query = self.job.extra.get("query") or ""
        if not query or len(query) < 2:
            raise HandlerException("搜索关键词至少需要 2 个字符")

        added_domains = set()
        if self.job.is_running:
            added_domains = set([job.extra.get("domain") for job in self.children])
        else:
            self._set_running()

        sources = ctx.sources.list(
            include_rejected=False,
            can_search=True,
        )
        domains = [source.domain for source in sources if source.domain not in added_domains]
        if not domains:
            return

        self._set_extra(search_source_total=len(sources))

        domain_usage = ctx.novels.list_domains()
        domains.sort(key=lambda x: domain_usage.get(x) or 0, reverse=True)

        for domain in domains:
            if self.signal.is_set():
                raise AbortedException()
            ctx.jobs.search_single_source(
                self.user,
                query,
                domain,
                parent_id=self.job.id,
            )
