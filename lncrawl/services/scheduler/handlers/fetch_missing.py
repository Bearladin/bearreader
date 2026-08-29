from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler, HandlerException


class FetchMissingHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.FETCH_MISSING

    def run(self) -> None:
        novel_id = self.job.extra.get("novel_id")
        if not novel_id:
            raise HandlerException("缺少小说 ID")

        added_types = {}
        if self.job.is_running:
            added_types = {job.type: job.id for job in self.children}
        else:
            self._set_running()

        if self.signal.is_set():
            raise AbortedException()

        if JobType.CHAPTER_BATCH not in added_types:
            missing_ids = ctx.chapters.list_ids(novel_id=novel_id, is_crawled=False)
            if not missing_ids:
                return

            novel = ctx.novels.get(novel_id)
            ctx.jobs.fetch_many_chapters(
                self.user,
                *missing_ids,
                parent_id=self.job.id,
                novel_id=novel_id,
                novel_title=novel.title,
            )
