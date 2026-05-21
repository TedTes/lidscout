import unittest

from domain.source import SourceLocator


class SourceLocatorTests(unittest.TestCase):
    def test_creates_normalized_source_locator(self):
        locator = SourceLocator.create(
            locator=" https://example.com/reviews ",
            limit=10,
            options={"section": "reviews"},
        )

        self.assertTrue(locator.id.startswith("source-locator-"))
        self.assertEqual(locator.locator, "https://example.com/reviews")
        self.assertTrue(locator.enabled)
        self.assertEqual(locator.limit, 10)
        self.assertEqual(locator.options, {"section": "reviews"})

    def test_converts_to_source_input(self):
        locator = SourceLocator.create(
            locator="https://example.com/reviews",
            enabled=False,
            limit=5,
        )

        source_input = locator.to_source_input()

        self.assertEqual(source_input.locator, "https://example.com/reviews")
        self.assertEqual(source_input.limit, 5)


if __name__ == "__main__":
    unittest.main()
