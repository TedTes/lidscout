import unittest

from application.extraction import ExtractionService
from domain.post import RawPost
from infrastructure.llm import MockLLMClient
from shared.errors import ExtractionError


class ExtractionServiceTests(unittest.TestCase):
    def test_extracts_signal_candidate(self):
        post = RawPost.create(source="reddit", source_id="abc", title="Reporting pain")
        llm_client = MockLLMClient(
            """
            {
              "has_signal": true,
              "is_about_competitor": true,
              "competitor_match_reason": "The post describes the competitor's reporting workflow pain.",
              "signal": {
                "pain": "Manual reporting is slow",
                "user_type": "founder",
                "job_to_be_done": "understand revenue trends",
                "current_workaround": "spreadsheets",
                "urgency": 5,
                "severity": 3,
                "willingness_to_pay": 5,
                "category": "reporting",
                "confidence": 0.9
              }
            }
            """
        )
        service = ExtractionService(llm_client)

        result = service.extract(post)

        self.assertTrue(result.has_signal)
        self.assertIsNotNone(result.signal)
        self.assertEqual(result.post_id, "reddit:abc")
        self.assertEqual(result.signal.post_id, "reddit:abc")
        self.assertEqual(result.signal.pain, "Manual reporting is slow")
        self.assertEqual(result.signal.urgency, "high")
        self.assertEqual(result.signal.severity, "medium")
        self.assertIs(result.signal.willingness_to_pay, True)
        self.assertEqual(len(llm_client.calls), 1)
        self.assertIn("competitor customer complaint", llm_client.calls[0][0])
        self.assertIn("title: Reporting pain", llm_client.calls[0][1])
        self.assertIsNotNone(llm_client.calls[0][2])

    def test_returns_no_signal_result(self):
        post = RawPost.create(source="hackernews", source_id="123")
        service = ExtractionService(
            MockLLMClient(
                """
                {
                  "has_signal": false,
                  "is_about_competitor": false,
                  "competitor_match_reason": null,
                  "signal": null
                }
                """
            )
        )

        result = service.extract(post)

        self.assertFalse(result.has_signal)
        self.assertIsNone(result.signal)
        self.assertEqual(result.post_id, "hackernews:123")

    def test_rejects_signal_unrelated_to_competitor_context(self):
        post = RawPost.create(
            source="web_json",
            source_id="abc",
            title="SyncBank saves money",
            body="SyncBank is cheaper than Rows.",
            metadata={
                "competitor_id": "notion",
                "competitor_name": "Notion",
                "competitor_domain": "notion.so",
            },
        )
        service = ExtractionService(
            MockLLMClient(
                """
                {
                  "has_signal": true,
                  "is_about_competitor": false,
                  "competitor_match_reason": "This discusses SyncBank and Rows, not Notion.",
                  "signal": {
                    "pain": "Rows is expensive",
                    "user_type": null,
                    "job_to_be_done": null,
                    "current_workaround": null,
                    "urgency": 3,
                    "severity": 3,
                    "willingness_to_pay": 2,
                    "category": "finance tools",
                    "confidence": 0.8
                  }
                }
                """
            )
        )

        result = service.extract(post)

        self.assertFalse(result.has_signal)
        self.assertIsNone(result.signal)

    def test_raises_extraction_error_for_invalid_json(self):
        post = RawPost.create(source="reddit", source_id="abc")
        service = ExtractionService(MockLLMClient("not json"))

        with self.assertRaises(ExtractionError):
            service.extract(post)


if __name__ == "__main__":
    unittest.main()
