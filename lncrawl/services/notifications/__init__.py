from typing import Dict, Type

from ...context import ctx
from ...core import TaskManager
from ...dao import Job, JobType, NotificationItem, User
from ._base import MailNotification
from .artifact_success import ArtifactSuccessMail
from .job_canceled import JobCanceledMail
from .job_failure import JobFailureMail
from .job_running import JobRunningMail
from .job_success import JobSuccessMail
from .novel_success import NovelSuccessMail

_ALL_NOTIFICATION_ITEMS = frozenset(NotificationItem)


# Evaluated in order on every job state change.
# To add a notification, define a MailNotification subclass and list it here.
NOTIFICATIONS: Dict[NotificationItem, Type[MailNotification]] = {
    NotificationItem.JOB_SUCCESS: JobSuccessMail,
    NotificationItem.JOB_RUNNING: JobRunningMail,
    NotificationItem.JOB_CANCELED: JobCanceledMail,
    NotificationItem.JOB_FAILURE: JobFailureMail,
    NotificationItem.NOVEL_SUCCESS: NovelSuccessMail,
    NotificationItem.ARTIFACT_SUCCESS: ArtifactSuccessMail,
}


class JobNotificationService:
    def __init__(self) -> None:
        self._taskman = TaskManager(5)

    def close(self):
        self._taskman.close()

    def notify(self, user: User, job: Job) -> None:
        """Notify by email for a job state change.

        Resolves which emails to send for the job's current state and updates the job's
        ``email_sent`` bookkeeping. Hands delivery to a background worker so that the job
        runner is never blocked.
        """
        if not user.is_verified or job.type in (
            JobType.IMPORT_EPUB_ANALYZE,
            JobType.IMPORT_EPUB_COMMIT,
        ):
            return

        # ensure this is root job, as email_sent is tracked only on the root
        if job.parent_job_id:
            root = ctx.jobs.get_root(job.id)
            if not root:
                return  # unlikely, but can happen for dangling jobs
            job = root

        # send when notification is enabled and email is not already sent
        email_alerts = user.extra.get("email_alerts") or {}
        email_sent = set(job.extra.get("email_sent") or [])
        for item_value, is_enabled in email_alerts.items():
            if not is_enabled:
                continue
            if isinstance(item_value, str) and item_value.isdigit():
                item_value = int(item_value)
            if not isinstance(item_value, int):
                continue
            if item_value not in _ALL_NOTIFICATION_ITEMS:
                continue
            if item_value in email_sent:
                continue

            item = NotificationItem(item_value)
            if item not in NOTIFICATIONS:
                ctx.logger.warn(f"No handler defined for {item!r}")
                continue

            self._taskman.submit_task(self._deliver, item, user, job)

    @staticmethod
    def _deliver(item: NotificationItem, user: User, job: Job) -> None:
        try:
            handler = NOTIFICATIONS[item]
            if not handler.can_activate(job):
                return

            def _update_extra(extra: dict):
                email_sent = set(extra.get("email_sent") or [])
                email_sent.add(item.value)
                extra["email_sent"] = list(email_sent)

            handler().send(user, job)
            ctx.jobs.update_extra(job, _update_extra)
        except Exception:
            ctx.logger.warn(
                f"Failed to notify {item.name!r} for job {job.id!r}",
                exc_info=ctx.logger.is_debug,
            )
