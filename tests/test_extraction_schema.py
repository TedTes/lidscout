import unittest

from pydantic import ValidationError

from application.extraction.extraction_schema import (
    SIGNAL_EXTRACTION_RESPONSE_SCHEMA,
    validate_extraction_response,
    validate_signal_candidate,
)


class ExtractionSchemaTests(unittest.TestCase):
    def test_validates_signal_candidate(self):
        candidate = validate_signal_candidate(
            {
                "pain": "Manual reporting is slow",
                "user_type": "founder",
                "job_to_be_done": "understand revenue trends",
                "current_workaround": "spreadsheets",
                "urgency": 5,
                "severity": 4,
                "willingness_to_pay": 3,
                "category": "reporting",
                "confidence": 0.82,
            }
        )

        self.assertEqual(candidate.pain, "Manual reporting is slow")
        self.assertEqual(candidate.urgency, 5)
        self.assertEqual(candidate.severity, 4)
        self.assertEqual(candidate.willingness_to_pay, 3)
        self.assertEqual(candidate.confidence, 0.82)

    def test_rejects_out_of_range_fields(self):
        with self.assertRaises(ValidationError):
            validate_signal_candidate(
                {
                    "pain": "Manual reporting is slow",
                    "urgency": 6,
                    "severity": 4,
                    "willingness_to_pay": 3,
                    "confidence": 0.82,
                }
            )

    def test_rejects_empty_pain(self):
        with self.assertRaises(ValidationError):
            validate_signal_candidate(
                {
                    "pain": " ",
                    "urgency": 5,
                    "severity": 4,
                    "willingness_to_pay": 3,
                    "confidence": 0.82,
                }
            )

    def test_rejects_invalid_confidence(self):
        with self.assertRaises(ValidationError):
            validate_signal_candidate(
                {
                    "pain": "Manual reporting is slow",
                    "urgency": 5,
                    "severity": 4,
                    "willingness_to_pay": 3,
                    "confidence": 1.1,
                }
            )

    def test_validates_extraction_response_with_signal(self):
        candidate = validate_extraction_response(
            {
                "has_signal": True,
                "is_about_competitor": True,
                "competitor_match_reason": "The post is about the monitored competitor.",
                "signal": {
                    "pain": "Manual reporting is slow",
                    "urgency": 5,
                    "severity": 4,
                    "willingness_to_pay": 3,
                    "confidence": 0.82,
                },
            }
        )

        self.assertTrue(candidate.has_signal)
        self.assertTrue(candidate.is_about_competitor)
        self.assertIsNotNone(candidate.signal)
        self.assertEqual(candidate.signal.pain, "Manual reporting is slow")

    def test_validates_extraction_response_without_signal(self):
        candidate = validate_extraction_response(
            {
                "has_signal": False,
                "is_about_competitor": False,
                "competitor_match_reason": None,
                "signal": None,
            }
        )

        self.assertFalse(candidate.has_signal)
        self.assertIsNone(candidate.signal)

    def test_response_schema_requires_envelope_fields(self):
        self.assertEqual(
            SIGNAL_EXTRACTION_RESPONSE_SCHEMA["required"],
            [
                "has_signal",
                "is_about_competitor",
                "competitor_match_reason",
                "signal",
            ],
        )


if __name__ == "__main__":
    unittest.main()
