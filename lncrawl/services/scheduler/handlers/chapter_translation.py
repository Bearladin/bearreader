from ....context import ctx
from ....enums import JobType
from ._base import BaseHandler, HandlerException


class ChapterTranslationHandler(BaseHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.CHAPTER_TRANSLATION

    def run(self) -> None:
        chapter_id = self.job.extra.get("chapter_id")
        if not chapter_id:
            raise HandlerException("缺少章节 ID")

        language = self.job.extra.get("language")
        if not language:
            raise HandlerException("未指定目标语言")

        chapter = ctx.chapters.get(chapter_id)
        if not chapter.is_available:
            raise HandlerException("章节没有可翻译的正文")

        if not self.job.is_running:
            self._set_running()

        ctx.translator.translate_chapter(
            chapter=chapter,
            target=language,
            signal=self.signal,
        )
