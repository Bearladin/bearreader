from ....context import ctx
from ....enums import JobType
from ._base import BaseHandler, HandlerException


class ImageHandler(BaseHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.IMAGE

    def run(self) -> None:
        image_id = self.job.extra.get("image_id")
        if not image_id:
            raise HandlerException("缺少图片 ID")

        if not self.job.is_running:
            self._set_running()

        image = ctx.crawler.fetch_image(
            self.user.id,
            image_id,
            self.signal,
            refresh=(not self.job.parent_job_id),
        )
        if not image.is_available:
            raise HandlerException("下载图片失败")
