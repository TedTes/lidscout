"""Email client for sending market signal reports."""
from dataclasses import dataclass

from application.reporting import MarketSignalReport
from infrastructure.email.notifier import EmailNotifier


@dataclass(frozen=True)
class EmailSendResult:
    """Result returned after attempting to send a report email."""

    recipient: str
    subject: str
    sent: bool
    error: str | None = None


class EmailClient:
    """Formats and sends market signal reports."""

    def __init__(self, notifier: EmailNotifier):
        self.notifier = notifier

    def send_report(self, report: MarketSignalReport, recipient: str) -> EmailSendResult:
        normalized_recipient = recipient.strip()
        if not normalized_recipient:
            raise ValueError("recipient is required")

        subject = report.title
        body = self._format_report(report)

        try:
            self.notifier.send_report(subject, body, [normalized_recipient])
        except Exception as exc:
            return EmailSendResult(
                recipient=normalized_recipient,
                subject=subject,
                sent=False,
                error=str(exc),
            )

        return EmailSendResult(
            recipient=normalized_recipient,
            subject=subject,
            sent=True,
        )

    @staticmethod
    def _format_report(report: MarketSignalReport) -> str:
        sections = [
            report.title,
            f"Generated at: {report.generated_at.isoformat()}",
            "",
            "Top clusters",
            *_format_cluster_lines(report),
            "",
            "Emerging pains",
            *_format_lines(report.emerging_pains),
            "",
            "Recommended opportunities",
            *_format_lines(report.recommended_opportunities),
        ]
        return "\n".join(sections)


def _format_cluster_lines(report: MarketSignalReport) -> list[str]:
    if not report.top_clusters:
        return ["- None"]

    return [
        (
            f"- {cluster.theme} "
            f"(score {cluster.average_score}, frequency {cluster.frequency}): "
            f"{cluster.summary}"
        )
        for cluster in report.top_clusters
    ]


def _format_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- None"]
    return [f"- {value}" for value in values]
