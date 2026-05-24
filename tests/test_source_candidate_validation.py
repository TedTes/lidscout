import unittest

from application.source_suggestions import validate_source_candidate
from domain.source import SourceCandidate


class SourceCandidateValidationTests(unittest.TestCase):
    def test_marks_http_candidate_valid(self):
        candidate = SourceCandidate.create(
            locator="https://example.com/reviews",
            source_type="review_search",
            label="Reviews",
            rationale="Find reviews.",
            source_family="reviews",
            competitor_id="notion",
            competitor_name="Notion",
            market_id="workspace-tools",
            market_name="Workspace tools",
        )

        validated = validate_source_candidate(candidate)

        self.assertEqual(validated.validation_status, "valid")
        self.assertIsNone(validated.validation_error)
        self.assertEqual(validated.competitor_id, "notion")
        self.assertEqual(validated.competitor_name, "Notion")
        self.assertEqual(validated.market_id, "workspace-tools")
        self.assertEqual(validated.market_name, "Workspace tools")

    def test_marks_non_http_candidate_invalid(self):
        candidate = SourceCandidate.create(
            locator="not-a-url",
            source_type="review_search",
            label="Reviews",
            rationale="Find reviews.",
            source_family="reviews",
            template_id="broken-template",
            rank_score=0.7,
        )

        validated = validate_source_candidate(candidate)

        self.assertEqual(validated.validation_status, "invalid")
        self.assertEqual(
            validated.validation_error,
            "locator must be an http or https URL",
        )
        self.assertEqual(validated.template_id, "broken-template")
        self.assertEqual(validated.rank_score, 0.7)


if __name__ == "__main__":
    unittest.main()
