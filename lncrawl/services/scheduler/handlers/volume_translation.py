from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler, HandlerException


class VolumeTranslationHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.VOLUME_TRANSLATION

    def run(self) -> None:
        volume_id = self.job.extra.get("volume_id")
        if not volume_id:
            raise HandlerException("缺少分卷 ID")

        language = self.job.extra.get("language")
        if not language:
            raise HandlerException("未指定目标语言")

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

            ctx.jobs.translate_chapter(
                self.user,
                chapter_id,
                language=language,
                parent_id=self.job.id,
                novel_title=self.job.extra.get("novel_title"),
            )

        volume = ctx.volumes.get(volume_id)
        ctx.translator.translate_volume(volume, language, self.signal)
