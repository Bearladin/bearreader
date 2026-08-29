from ....context import ctx
from ....enums import JobType
from ._base import AbortedException, BatchHandler, HandlerException


class NovelTranslationBatchHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return (
            job.type == JobType.NOVEL_TRANSLATION_BATCH
            or job.type == JobType.FULL_NOVEL_TRANSLATION_BATCH
        )

    def run(self) -> None:
        novel_ids = self.job.extra.get("novel_ids")
        if not novel_ids:
            return

        language = self.job.extra.get("language")
        if not language:
            raise HandlerException("未指定目标语言")

        added_novel_ids = set()
        if self.job.is_running:
            added_novel_ids = set([job.extra.get("novel_id") for job in self.children])
        else:
            self._set_running()

        for novel_id in novel_ids:
            if novel_id in added_novel_ids:
                continue

            if self.signal.is_set():
                raise AbortedException()

            ctx.jobs.translate_novel(
                self.user,
                novel_id,
                language,
                parent_id=self.job.id,
                full=self.job.type == JobType.FULL_NOVEL_TRANSLATION_BATCH,
            )
