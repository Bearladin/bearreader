from ....context import ctx
from ....enums import JobType, OutputFormat
from ._base import AbortedException, BatchHandler, HandlerException


class NovelHandler(BatchHandler):
    @staticmethod
    def can_activate(job) -> bool:
        return job.type == JobType.NOVEL or job.type == JobType.FULL_NOVEL

    def run(self) -> None:
        url = self.job.extra.get("url")
        if not url:
            raise HandlerException("缺少小说 URL")

        added_types = {}
        if self.job.is_running:
            added_types = {job.type: job.id for job in self.children}
        else:
            self._set_running()

        novel = ctx.crawler.fetch_novel(
            user_id=self.user.id,
            url=url,
            signal=self.signal,
        )
        self._set_extra(novel_id=novel.id)

        if self.job.type != JobType.FULL_NOVEL:
            return

        if self.signal.is_set():
            raise AbortedException()

        if JobType.VOLUME_BATCH not in added_types:
            volumes = ctx.volumes.list(novel_id=novel.id)
            if not volumes:
                return

            job = ctx.jobs.fetch_many_volumes(
                self.user,
                *(volume.id for volume in volumes),
                parent_id=self.job.id,
                novel_id=novel.id,
                novel_title=novel.title,
            )
            added_types[job.type] = job.id

        if self.signal.is_set():
            raise AbortedException()

        if JobType.ARTIFACT not in added_types:
            ctx.jobs.make_artifact(
                self.user,
                novel.id,
                OutputFormat.epub,
                parent_id=self.job.id,
                novel_title=novel.title,
                depends_on=added_types[JobType.VOLUME_BATCH],
            )
