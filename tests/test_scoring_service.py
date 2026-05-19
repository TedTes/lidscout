import unittest

from application.scoring import ScoringService
from domain.score import OpportunityScore
from domain.signal import Signal


class FakeScoreRepository:
    def __init__(self, save_count: int | None = None):
        self.save_count = save_count
        self.saved_scores: list[OpportunityScore] = []

    def save_scores(self, scores: list[OpportunityScore]) -> int:
        self.saved_scores = scores
        return self.save_count if self.save_count is not None else len(scores)


class ScoringServiceTests(unittest.TestCase):
    def test_scores_and_persists_signals(self):
        repository = FakeScoreRepository()
        service = ScoringService(repository)
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:abc",
                pain="Manual reporting is slow",
                urgency="high",
                severity="medium",
                willingness_to_pay=True,
                confidence=0.8,
            ),
            Signal.create(
                id="signal-2",
                post_id="hackernews:123",
                pain="Setup is confusing",
                urgency="low",
                severity="low",
                willingness_to_pay=False,
                confidence=0.5,
            ),
        ]

        result = service.score(signals)

        self.assertEqual(result.scored_count, 2)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.average_score, 5.3)
        self.assertEqual(repository.saved_scores[0].signal_id, "signal-1")
        self.assertEqual(repository.saved_scores[0].total_score, 8.6)

    def test_counts_repository_save_failures(self):
        repository = FakeScoreRepository(save_count=1)
        service = ScoringService(repository)
        signals = [
            Signal.create(id="signal-1", post_id="reddit:abc", pain="One"),
            Signal.create(id="signal-2", post_id="reddit:def", pain="Two"),
        ]

        result = service.score(signals)

        self.assertEqual(result.scored_count, 1)
        self.assertEqual(result.failed_count, 1)


if __name__ == "__main__":
    unittest.main()
