"""Resend email notifier."""
import requests

from infrastructure.email.notifier import EmailNotifier


class ResendEmailNotifier(EmailNotifier):
    """Sends report emails through Resend."""

    endpoint = "https://api.resend.com/emails"

    def __init__(
        self,
        *,
        api_key: str,
        from_email: str,
        timeout_seconds: int = 30,
    ):
        cleaned_key = api_key.strip()
        cleaned_from = from_email.strip()
        if not cleaned_key:
            raise ValueError("api_key is required")
        if not cleaned_from:
            raise ValueError("from_email is required")
        self.api_key = cleaned_key
        self.from_email = cleaned_from
        self.timeout_seconds = timeout_seconds

    def send_report(self, subject: str, body: str, recipients: list[str]) -> None:
        normalized_recipients = [
            recipient.strip()
            for recipient in recipients
            if recipient.strip()
        ]
        if not normalized_recipients:
            raise ValueError("recipients are required")

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": self.from_email,
                "to": normalized_recipients,
                "subject": subject,
                "text": body,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
