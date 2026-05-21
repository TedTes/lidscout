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
              "signal": {
                "pain": "Manual reporting is slow",
                "user_type": "founder",
                "job_to_be_done": "understand revenue trends",
                "current_workaround": "spreadsheets",
                "urgency": "high",
                "severity": "medium",
                "willingness_to_pay": true,
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
        self.assertEqual(len(llm_client.calls), 1)
        self.assertIn("competitor customer complaint", llm_client.calls[0][0])
        self.assertIn("title: Reporting pain", llm_client.calls[0][1])

    def test_returns_no_signal_result(self):
        post = RawPost.create(source="hackernews", source_id="123")
        service = ExtractionService(MockLLMClient('{"has_signal": false}'))

        result = service.extract(post)

        self.assertFalse(result.has_signal)
        self.assertIsNone(result.signal)
        self.assertEqual(result.post_id, "hackernews:123")

    def test_raises_extraction_error_for_invalid_json(self):
        post = RawPost.create(source="reddit", source_id="abc")
        service = ExtractionService(MockLLMClient("not json"))

        with self.assertRaises(ExtractionError):
            service.extract(post)


if __name__ == "__main__":
    unittest.main()
