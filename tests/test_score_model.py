import unittest

from domain.score import OpportunityScore
from domain.signal import Signal


class OpportunityScoreTests(unittest.TestCase):
    def test_scores_signal_components(self):
        signal = Signal.create(
            id="signal-1",
            post_id="reddit:abc",
            pain="Manual reporting is slow",
            urgency="high",
            severity="medium",
            willingness_to_pay=True,
            confidence=0.8,
        )

        score = OpportunityScore.from_signal(signal)

        self.assertEqual(score.signal_id, "signal-1")
        self.assertEqual(score.urgency_score, 5.0)
        self.assertEqual(score.severity_score, 3.0)
        self.assertEqual(score.willingness_score, 5.0)
        self.assertEqual(score.confidence_score, 4.0)
        self.assertEqual(score.total_score, 17.0)
        self.assertIn("urgency=high", score.reasoning)

    def test_scores_unknown_willingness_as_zero(self):
        signal = Signal.create(
            id="signal-2",
            post_id="hackernews:123",
            pain="Setup is confusing",
            urgency="low",
            severity="low",
            willingness_to_pay=None,
            confidence=0.5,
        )

        score = OpportunityScore.from_signal(signal)

        self.assertEqual(score.willingness_score, 0.0)
        self.assertEqual(score.total_score, 4.5)


if __name__ == "__main__":
    unittest.main()
