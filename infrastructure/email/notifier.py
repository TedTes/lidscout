"""Email notification boundary."""
from abc import ABC, abstractmethod


class EmailNotifier(ABC):
    """Sends signal reports to recipients."""

    @abstractmethod
    def send_report(self, subject: str, body: str, recipients: list[str]) -> None:
        """Send a report email."""
        raise NotImplementedError
