import unittest

from domain.score import calculate_opportunity_score
from domain.signal import Signal


class ScoreFormulaTests(unittest.TestCase):
    def test_calculates_weighted_opportunity_score(self):
        signal = Signal.create(
            id="signal-1",
            post_id="reddit:abc",
            pain="Manual reporting is slow",
            urgency="high",
            severity="medium",
            willingness_to_pay=True,
            confidence=0.8,
        )

        score = calculate_opportunity_score(signal)

        self.assertEqual(score, 8.6)

    def test_clamps_score_to_zero_to_ten_range(self):
        signal = Signal.create(
            id="signal-2",
            post_id="reddit:def",
            pain="Setup is confusing",
            urgency="high",
            severity="high",
            willingness_to_pay=True,
            confidence=1.0,
        )

        score = calculate_opportunity_score(signal)

        self.assertEqual(score, 10.0)


if __name__ == "__main__":
    unittest.main()
