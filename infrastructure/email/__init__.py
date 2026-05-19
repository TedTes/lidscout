"""Email infrastructure."""
from infrastructure.email.client import EmailClient, EmailSendResult
from infrastructure.email.notifier import EmailNotifier

__all__ = ["EmailClient", "EmailNotifier", "EmailSendResult"]
