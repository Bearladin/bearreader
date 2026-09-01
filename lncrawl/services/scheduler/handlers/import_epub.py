from ....context import ctx
from ....enums import JobType
from ....exceptions import AbortedException
from ....services.epub_import import EpubImportError
from ._base import BaseHandler, HandlerException


class EpubAnalyzeHandler(BaseHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.IMPORT_EPUB_ANALYZE

    def run(self) -> None:
        session_id = self.job.extra.get("import_session_id")
        if not session_id:
            raise HandlerException("缺少 EPUB 导入会话")
        if self.signal.is_set():
            raise AbortedException()
        if not self.job.is_running:
            self._set_running()

        def on_phase(phase: str) -> None:
            if self.signal.is_set():
                raise AbortedException()
            self._set_extra(phase=phase)
            self._increment()

        try:
            ctx.epub_import.analyze_session(session_id, self.signal, on_phase)
            self._set_extra(phase="分析完成")
        except AbortedException:
            ctx.epub_import.cancel_by_job(session_id)
            raise
        except EpubImportError as error:
            ctx.epub_import.fail_session(session_id, error.user_message)
            raise HandlerException(error.user_message) from error
        except Exception:
            ctx.epub_import.fail_session(session_id, "这个 EPUB 文件无法导入。")
            raise


class EpubCommitHandler(BaseHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.IMPORT_EPUB_COMMIT

    def run(self) -> None:
        session_id = self.job.extra.get("import_session_id")
        if not session_id:
            raise HandlerException("缺少 EPUB 导入会话")
        if self.signal.is_set():
            raise AbortedException()
        if not self.job.is_running:
            self._set_running()
        try:
            novel_id = ctx.epub_import.commit_session(
                session_id,
                str(self.job.extra.get("novel_title") or ""),
                str(self.job.extra.get("authors") or ""),
                self.signal,
            )
            self._set_extra(novel_id=novel_id, phase="导入完成")
        except AbortedException:
            ctx.epub_import.cancel_by_job(session_id)
            raise
        except EpubImportError as error:
            ctx.epub_import.fail_session(session_id, error.user_message)
            raise HandlerException(error.user_message) from error
        except Exception:
            ctx.epub_import.fail_session(session_id, "导入 EPUB 失败。")
            raise
