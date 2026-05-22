from pathlib import Path
import unittest

from application.extraction import RuleBasedRelevanceFilter
from application.extraction.relevance_eval import (
    evaluate_relevance_filter,
    load_labeled_relevance_examples,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "relevance_eval.json"


class RelevanceEvalTests(unittest.TestCase):
    def test_loads_labeled_relevance_examples(self):
        examples = load_labeled_relevance_examples(FIXTURE_PATH)

        self.assertGreaterEqual(len(examples), 6)
        self.assertEqual(examples[0].id, "acme-export-pain")
        self.assertTrue(examples[0].expected_relevant)

    def test_evaluates_rule_filter_against_fixture(self):
        examples = load_labeled_relevance_examples(FIXTURE_PATH)

        report = evaluate_relevance_filter(
            RuleBasedRelevanceFilter(),
            examples,
        )

        self.assertEqual(report.total, len(examples))
        self.assertGreaterEqual(report.precision, 0.8)
        self.assertGreaterEqual(report.recall, 0.8)
        self.assertEqual(report.mistakes, [])


if __name__ == "__main__":
    unittest.main()
