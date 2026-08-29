from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler


class ChapterBatchHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.CHAPTER_BATCH

    def run(self) -> None:
        chapter_ids = self.job.extra.get("chapter_ids")
        if not chapter_ids:
            return

        added_chapters = set()
        if self.job.is_running:
            added_chapters = set([job.extra.get("chapter_id") for job in self.children])
        else:
            self._set_running()

        for chapter_id in chapter_ids:
            if chapter_id in added_chapters:
                continue

            if self.signal.is_set():
                raise AbortedException()

            ctx.jobs.fetch_chapter(
                self.user,
                chapter_id,
                parent_id=self.job.id,
                novel_title=self.job.extra.get("novel_title"),
            )
