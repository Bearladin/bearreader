from ...context import ctx
from ...enums import JobStatus
from ._base import MailNotification


class JobFailureMail(MailNotification):
    @staticmethod
    def can_activate(job) -> bool:
        return job.status == JobStatus.FAILED

    def send(self, user, job) -> None:
        ctx.mail.send_job_report(user, job)
