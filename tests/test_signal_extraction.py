import unittest

from api.schemas import InteractionExtractionRequest, PageSourceInput
from application.extraction.interaction_extractor import InteractionExtractorService
from domain.score import severity_for_frequency


class SignalExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_extracts_negative_signals_from_text_source(self):
        request = InteractionExtractionRequest(
            sources=[
                PageSourceInput(
                    source_type="text",
                    label="sample reviews",
                    text=(
                        "Pros: The scheduling view is useful once configured.\n"
                        "Cons: It is expensive for a small team, setup was confusing, "
                        "and reporting is limited.\n"
                        "Overall: Support was slow to respond when our mobile app sync stopped working."
                    ),
                )
            ]
        )

        response = await InteractionExtractorService().extract(request)
        themes = {signal.theme for signal in response.negative_signals}

        self.assertEqual(response.total_sources, 1)
        self.assertGreaterEqual(len(response.negative_comments), 2)
        self.assertIn("pricing complaints", themes)
        self.assertIn("support complaints", themes)

    def test_scores_signal_frequency(self):
        self.assertEqual(severity_for_frequency(1), "low")
        self.assertEqual(severity_for_frequency(2), "medium")
        self.assertEqual(severity_for_frequency(5), "high")


if __name__ == "__main__":
    unittest.main()
