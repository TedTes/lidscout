import unittest

from application.extraction import ExtractionService
from domain.post import RawPost
from shared.errors import ExtractionError


class FakeLLMClient:
    def __init__(self, response: str):
        self.response = response

    def extract_signal_json(self, post: RawPost) -> str:
        return self.response


class ExtractionServiceTests(unittest.TestCase):
    def test_extracts_signal_candidate(self):
        post = RawPost.create(source="reddit", source_id="abc", title="Reporting pain")
        service = ExtractionService(
            FakeLLMClient(
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
        )

        result = service.extract(post)

        self.assertTrue(result.has_signal)
        self.assertIsNotNone(result.signal)
        self.assertEqual(result.post_id, "reddit:abc")
        self.assertEqual(result.signal.post_id, "reddit:abc")
        self.assertEqual(result.signal.pain, "Manual reporting is slow")

    def test_returns_no_signal_result(self):
        post = RawPost.create(source="hackernews", source_id="123")
        service = ExtractionService(FakeLLMClient('{"has_signal": false}'))

        result = service.extract(post)

        self.assertFalse(result.has_signal)
        self.assertIsNone(result.signal)
        self.assertEqual(result.post_id, "hackernews:123")

    def test_raises_extraction_error_for_invalid_json(self):
        post = RawPost.create(source="reddit", source_id="abc")
        service = ExtractionService(FakeLLMClient("not json"))

        with self.assertRaises(ExtractionError):
            service.extract(post)


if __name__ == "__main__":
    unittest.main()
