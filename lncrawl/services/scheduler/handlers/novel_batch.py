from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler


class NovelBatchHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.NOVEL_BATCH or job.type == JobType.FULL_NOVEL_BATCH

    def run(self) -> None:
        urls = self.job.extra.get("urls")
        if not urls:
            return

        added_urls = set()
        if self.job.is_running:
            added_urls = set([job.extra.get("url") for job in self.children])
        else:
            self._set_running()

        for url in urls:
            if url in added_urls:
                continue

            if self.signal.is_set():
                raise AbortedException()

            ctx.jobs.fetch_novel(
                self.user,
                url,
                parent_id=self.job.id,
                full=self.job.type == JobType.FULL_NOVEL_BATCH,
            )
