import unittest

from pydantic import ValidationError

from application.extraction.extraction_schema import validate_signal_candidate


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


if __name__ == "__main__":
    unittest.main()
