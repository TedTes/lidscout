from datetime import UTC, datetime
import unittest

from application.reporting import MarketSignalReport
from domain.cluster import SignalCluster
from infrastructure.email import EmailClient, EmailNotifier, EmailSendResult


class FakeEmailNotifier(EmailNotifier):
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[tuple[str, str, list[str]]] = []

    def send_report(self, subject: str, body: str, recipients: list[str]) -> None:
        self.calls.append((subject, body, recipients))
        if self.error:
            raise self.error


class EmailClientTests(unittest.TestCase):
    def test_formats_and_sends_market_signal_report(self):
        notifier = FakeEmailNotifier()
        client = EmailClient(notifier)
        report = self._report()

        result = client.send_report(report, " founder@example.com ")

        self.assertIsInstance(result, EmailSendResult)
        self.assertTrue(result.sent)
        self.assertEqual(result.recipient, "founder@example.com")
        self.assertEqual(result.subject, "Weekly Signals")
        self.assertIsNone(result.error)
        self.assertEqual(len(notifier.calls), 1)
        subject, body, recipients = notifier.calls[0]
        self.assertEqual(subject, "Weekly Signals")
        self.assertEqual(recipients, ["founder@example.com"])
        self.assertIn("Generated at: 2026-05-19T12:00:00+00:00", body)
        self.assertIn("- reporting (score 8.4, frequency 3): Teams need faster reports.", body)
        self.assertIn("- Teams need faster reports.", body)
        self.assertIn("- reporting: Teams need faster reports.", body)

    def test_returns_failed_result_when_notifier_fails(self):
        notifier = FakeEmailNotifier(error=RuntimeError("smtp failed"))
        client = EmailClient(notifier)

        result = client.send_report(self._report(), "founder@example.com")

        self.assertFalse(result.sent)
        self.assertEqual(result.error, "smtp failed")

    def test_rejects_empty_recipient(self):
        client = EmailClient(FakeEmailNotifier())

        with self.assertRaises(ValueError):
            client.send_report(self._report(), "   ")

    @staticmethod
    def _report() -> MarketSignalReport:
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="reporting",
            summary="Teams need faster reports.",
            signal_ids=["signal-1"],
            frequency=3,
            average_score=8.4,
            top_examples=["Manual reporting is slow."],
        )
        return MarketSignalReport(
            title="Weekly Signals",
            generated_at=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
            top_clusters=[cluster],
            emerging_pains=["Teams need faster reports."],
            recommended_opportunities=["reporting: Teams need faster reports."],
        )


if __name__ == "__main__":
    unittest.main()
