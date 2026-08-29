from ....context import ctx
from ....enums import JobType
from ._base import BatchHandler, HandlerException


class ChapterHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.CHAPTER

    def run(self) -> None:
        chapter_id = self.job.extra.get("chapter_id")
        if not chapter_id:
            raise HandlerException("缺少章节 ID")

        added_types = {}
        if self.job.is_running:
            added_types = {job.type: job.id for job in self.children}
        else:
            self._set_running()

        chapter = ctx.crawler.fetch_chapter(
            self.user.id,
            chapter_id,
            self.signal,
            refresh=(not self.job.parent_job_id),
        )
        if not chapter.is_available:
            raise HandlerException("获取章节正文失败")

        if JobType.IMAGE_BATCH not in added_types:
            images = ctx.images.list(chapter_id=chapter.id, is_crawled=False)
            if not images:
                return

            ctx.jobs.fetch_many_images(
                self.user,
                *(image.id for image in images),
                parent_id=self.job.id,
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                novel_id=chapter.novel_id,
                novel_title=self.job.extra.get("novel_title"),
            )
