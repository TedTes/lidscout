"""Email infrastructure."""
from infrastructure.email.client import EmailClient, EmailSendResult
from infrastructure.email.notifier import EmailNotifier
from infrastructure.email.resend_notifier import ResendEmailNotifier

__all__ = [
    "EmailClient",
    "EmailNotifier",
    "EmailSendResult",
    "ResendEmailNotifier",
]
