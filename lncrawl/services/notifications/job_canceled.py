from ...context import ctx
from ...enums import JobStatus
from ._base import MailNotification


class JobCanceledMail(MailNotification):
    @staticmethod
    def can_activate(job) -> bool:
        return job.status == JobStatus.CANCELED

    def send(self, user, job) -> None:
        ctx.mail.send_job_report(user, job)
