import unittest

from domain.signal import Signal


class SignalModelTests(unittest.TestCase):
    def test_creates_valid_signal(self):
        signal = Signal.create(
            id=" signal-1 ",
            post_id=" reddit:abc ",
            pain=" Manual reporting is slow ",
            user_type=" founder ",
            job_to_be_done=" understand revenue trends ",
            current_workaround=" spreadsheets ",
            urgency="high",
            severity="medium",
            willingness_to_pay=True,
            category="reporting",
            confidence=0.82,
            competitor_id=" competitor-1 ",
            evidence_url=" https://example.com/reviews ",
            evidence_text=" Customer quote ",
        )

        self.assertEqual(signal.id, "signal-1")
        self.assertEqual(signal.post_id, "reddit:abc")
        self.assertEqual(signal.pain, "Manual reporting is slow")
        self.assertEqual(signal.user_type, "founder")
        self.assertEqual(signal.job_to_be_done, "understand revenue trends")
        self.assertEqual(signal.current_workaround, "spreadsheets")
        self.assertEqual(signal.urgency, "high")
        self.assertEqual(signal.severity, "medium")
        self.assertTrue(signal.willingness_to_pay)
        self.assertEqual(signal.category, "reporting")
        self.assertEqual(signal.confidence, 0.82)
        self.assertEqual(signal.competitor_id, "competitor-1")
        self.assertEqual(signal.evidence_url, "https://example.com/reviews")
        self.assertEqual(signal.evidence_text, "Customer quote")

    def test_rejects_missing_business_meaning(self):
        with self.assertRaises(ValueError):
            Signal.create(id="signal-1", post_id="reddit:abc", pain="")

    def test_rejects_invalid_confidence(self):
        with self.assertRaises(ValueError):
            Signal.create(
                id="signal-1",
                post_id="reddit:abc",
                pain="Reporting is slow",
                confidence=1.5,
            )


if __name__ == "__main__":
    unittest.main()
