from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler, HandlerException


class VolumeTranslationBatchHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.VOLUME_TRANSLATION_BATCH

    def run(self) -> None:
        volume_ids = self.job.extra.get("volume_ids")
        if not volume_ids:
            return

        language = self.job.extra.get("language")
        if not language:
            raise HandlerException("未指定目标语言")

        added_volumes = set()
        if self.job.is_running:
            added_volumes = set([job.extra.get("volume_id") for job in self.children])
        else:
            self._set_running()

        for volume_id in volume_ids:
            if volume_id in added_volumes:
                continue

            if self.signal.is_set():
                raise AbortedException()

            ctx.jobs.translate_volume(
                self.user,
                volume_id,
                language,
                parent_id=self.job.id,
                novel_title=self.job.extra.get("novel_title"),
            )
