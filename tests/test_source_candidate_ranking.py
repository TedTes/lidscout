import unittest

from application.source_suggestions import rank_source_candidates
from domain.source import SourceCandidate


class SourceCandidateRankingTests(unittest.TestCase):
    def test_ranks_new_valid_high_score_candidates_first(self):
        monitored = self._candidate(
            label="Already monitored",
            already_monitored=True,
            rank_score=0.95,
        )
        invalid = self._candidate(
            label="Invalid",
            rank_score=0.99,
            validation_status="invalid",
            validation_error="bad url",
        )
        lower_score = self._candidate(label="Lower score", rank_score=0.5)
        higher_score = self._candidate(label="Higher score", rank_score=0.8)

        ranked = rank_source_candidates(
            [monitored, invalid, lower_score, higher_score]
        )

        self.assertEqual(
            [candidate.label for candidate in ranked],
            ["Higher score", "Lower score", "Invalid", "Already monitored"],
        )

    def test_uses_source_family_as_tiebreaker(self):
        website = self._candidate(
            label="Website",
            source_family="owned_site",
            rank_score=0.5,
        )
        reviews = self._candidate(
            label="Reviews",
            source_family="reviews",
            rank_score=0.5,
        )

        ranked = rank_source_candidates([website, reviews])

        self.assertEqual(
            [candidate.label for candidate in ranked],
            ["Reviews", "Website"],
        )

    def _candidate(
        self,
        *,
        label: str,
        source_family: str = "reviews",
        already_monitored: bool = False,
        rank_score: float = 0.0,
        validation_status: str = "valid",
        validation_error: str | None = None,
    ) -> SourceCandidate:
        return SourceCandidate.create(
            locator=f"https://example.com/{label.lower().replace(' ', '-')}",
            source_type="review_search",
            label=label,
            rationale="Find evidence.",
            source_family=source_family,
            already_monitored=already_monitored,
            rank_score=rank_score,
            validation_status=validation_status,
            validation_error=validation_error,
        )


if __name__ == "__main__":
    unittest.main()
