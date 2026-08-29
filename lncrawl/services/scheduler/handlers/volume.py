from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler, HandlerException


class VolumeHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.VOLUME

    child_key = "chapter_id"
    empty_done = False

    def run(self) -> None:
        volume_id = self.job.extra.get("volume_id")
        if not volume_id:
            raise HandlerException("缺少分卷 ID")

        added_chapters = set()
        if self.job.is_running:
            added_chapters = set([job.extra.get("chapter_id") for job in self.children])
        else:
            self._set_running()

        chapter_ids = ctx.chapters.list_ids(volume_id=volume_id)
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
