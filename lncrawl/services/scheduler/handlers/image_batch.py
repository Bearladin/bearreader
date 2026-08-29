from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler


class ImageBatchHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.IMAGE_BATCH

    def run(self) -> None:
        image_ids = self.job.extra.get("image_ids")
        if not image_ids:
            return

        added_images = set()
        if self.job.is_running:
            added_images = set([job.extra.get("image_id") for job in self.children])
        else:
            self._set_running()

        for image_id in image_ids:
            if image_id in added_images:
                continue

            if self.signal.is_set():
                raise AbortedException()

            ctx.jobs.fetch_image(
                self.user,
                image_id,
                parent_id=self.job.id,
                novel_id=self.job.extra.get("novel_id"),
                novel_title=self.job.extra.get("novel_title"),
                chapter_id=self.job.extra.get("chapter_id"),
                chapter_title=self.job.extra.get("chapter_title"),
            )
