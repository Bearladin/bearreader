from abc import ABC, abstractmethod

from ...dao import Job, User


class MailNotification(ABC):
    """Base class for a job email notification."""

    @staticmethod
    @abstractmethod
    def can_activate(job: Job) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def send(self, user: User, job: Job) -> None:
        raise NotImplementedError()
