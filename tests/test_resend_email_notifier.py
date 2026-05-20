import unittest
from unittest.mock import Mock, patch

from infrastructure.email import ResendEmailNotifier


class ResendEmailNotifierTests(unittest.TestCase):
    def test_sends_report_with_resend_payload(self):
        response = Mock()
        response.raise_for_status.return_value = None

        with patch(
            "infrastructure.email.resend_notifier.requests.post",
            return_value=response,
        ) as post:
            notifier = ResendEmailNotifier(
                api_key="resend-key",
                from_email="LidScout <alerts@example.com>",
                timeout_seconds=12,
            )

            notifier.send_report(
                "Weekly Signals",
                "Report body",
                [" founder@example.com "],
            )

        post.assert_called_once()
        call = post.call_args
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer resend-key")
        self.assertEqual(call.kwargs["json"]["from"], "LidScout <alerts@example.com>")
        self.assertEqual(call.kwargs["json"]["to"], ["founder@example.com"])
        self.assertEqual(call.kwargs["json"]["subject"], "Weekly Signals")
        self.assertEqual(call.kwargs["json"]["text"], "Report body")
        self.assertEqual(call.kwargs["timeout"], 12)

    def test_rejects_blank_api_key(self):
        with self.assertRaises(ValueError):
            ResendEmailNotifier(
                api_key=" ",
                from_email="LidScout <alerts@example.com>",
            )

    def test_rejects_blank_from_email(self):
        with self.assertRaises(ValueError):
            ResendEmailNotifier(
                api_key="resend-key",
                from_email=" ",
            )

    def test_rejects_empty_recipients(self):
        notifier = ResendEmailNotifier(
            api_key="resend-key",
            from_email="LidScout <alerts@example.com>",
        )

        with self.assertRaises(ValueError):
            notifier.send_report("Weekly Signals", "Report body", [" "])


if __name__ == "__main__":
    unittest.main()
