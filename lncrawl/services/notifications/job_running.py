from ...context import ctx
from ...enums import JobStatus
from ._base import MailNotification


class JobRunningMail(MailNotification):
    @staticmethod
    def can_activate(job) -> bool:
        return job.status == JobStatus.RUNNING

    def send(self, user, job) -> None:
        ctx.mail.send_job_report(user, job)
