from ....context import ctx
from ....enums import JobType, OutputFormat
from ._base import AbortedException, BatchHandler, HandlerException


class NovelTranslationHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.NOVEL_TRANSLATION or job.type == JobType.FULL_NOVEL_TRANSLATION

    def run(self) -> None:
        novel_id = self.job.extra.get("novel_id")
        if not novel_id:
            raise HandlerException("缺少小说 ID")

        language = self.job.extra.get("language")
        if not language:
            raise HandlerException("未指定目标语言")

        added_types = {}
        if self.job.is_running:
            added_types = {job.type: job.id for job in self.children}
        else:
            self._set_running()

        novel = ctx.novels.get(novel_id)
        ctx.translator.translate_novel(novel, language, self.signal)

        if self.job.type != JobType.FULL_NOVEL_TRANSLATION:
            return

        if self.signal.is_set():
            raise AbortedException()

        if JobType.VOLUME_TRANSLATION_BATCH not in added_types:
            volumes = ctx.volumes.list(novel_id=novel_id)
            if not volumes:
                return
            job = ctx.jobs.translate_many_volumes(
                self.user,
                *(volume.id for volume in volumes),
                language=language,
                parent_id=self.job.id,
                novel_id=novel_id,
                novel_title=novel.title,
            )
            added_types[job.type] = job.id

        if JobType.VOLUME_TRANSLATION_BATCH not in added_types:
            return

        if self.signal.is_set():
            raise AbortedException()

        if JobType.ARTIFACT not in added_types:
            ctx.jobs.make_artifact(
                self.user,
                novel.id,
                OutputFormat.epub,
                language=language,
                parent_id=self.job.id,
                novel_title=novel.title,
                depends_on=added_types[JobType.VOLUME_TRANSLATION_BATCH],
            )
