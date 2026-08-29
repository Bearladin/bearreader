from ....context import ctx
from ....enums import JobType, OutputFormat
from ._base import AbortedException, BaseHandler, HandlerException

_ALL_OUTPUT_FORMATS = frozenset(OutputFormat)


class ArtifactHandler(BaseHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.ARTIFACT

    def run(self) -> None:
        novel_id = self.job.extra.get("novel_id")
        if not novel_id:
            raise HandlerException("缺少小说 ID")

        format = self.job.extra.get("format")
        if not format:
            raise HandlerException("未指定导出格式")

        language = self.job.extra.get("language")
        volume = self.job.extra.get("volume")

        if format not in _ALL_OUTPUT_FORMATS:
            raise HandlerException(f"不支持的导出格式：{format}")

        if not self.job.is_running:
            self._set_running()

        novel_title = self.job.extra.get("novel_title")
        if not novel_title:
            novel_title = ctx.novels.get(novel_id).title

        epub = None
        if format in ctx.binder.depends_on_epub:
            if not self.job.depends_on:
                raise HandlerException(f"找不到 {format} 所需的前置任务")
            epub = ctx.artifacts.get_epub(self.job.depends_on)

        if self.signal.is_set():
            raise AbortedException()

        artifact = ctx.binder.make_artifact(
            format=format,
            novel_id=novel_id,
            novel_title=novel_title,
            job_id=self.job.id,
            user_id=self.user.id,
            epub=epub,
            language=language,
            volume=volume,
            signal=self.signal,
        )
        if not artifact.is_available:
            raise HandlerException("生成导出文件失败")

        self._set_extra(artifact_id=artifact.id, novel_title=novel_title)
