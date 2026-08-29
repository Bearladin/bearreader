from ...context import ctx
from ...enums import JobStatus, JobType
from ._base import MailNotification


class NovelSuccessMail(MailNotification):
    @staticmethod
    def can_activate(job) -> bool:
        if job.status != JobStatus.SUCCESS:
            return False
        if job.type not in (JobType.FULL_NOVEL, JobType.NOVEL):
            return False
        return True

    def send(self, user, job) -> None:
        ctx.mail.send_full_novel_job_success(user, job)
