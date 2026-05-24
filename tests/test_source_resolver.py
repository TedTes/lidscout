import unittest

from application.ingestion import SourceResolver
from domain.post import RawPost
from domain.source import SourceInput


class MatchingAdapter:
    def __init__(self):
        self.calls: list[SourceInput] = []

    def can_handle(self, source: SourceInput) -> bool:
        return source.locator == "https://example.com/reviews"

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        self.calls.append(source)
        return [
            RawPost.create(
                source="web",
                source_id=source.locator,
                title="Review page",
            )
        ]


class FailingAdapter(MatchingAdapter):
    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        raise RuntimeError("fetch blocked")


class SourceResolverTests(unittest.TestCase):
    def test_routes_sources_to_matching_adapter(self):
        adapter = MatchingAdapter()
        resolver = SourceResolver([adapter])
        source = SourceInput.create(
            locator="https://example.com/reviews",
        )

        result = resolver.fetch([source])

        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.posts[0].id, "web:https://example.com/reviews")
        self.assertEqual(result.details[0].source, source)
        self.assertEqual(result.details[0].fetched_count, 1)
        self.assertIsNone(result.details[0].error)
        self.assertEqual(adapter.calls, [source])

    def test_counts_unhandled_sources_as_failed(self):
        resolver = SourceResolver([])

        result = resolver.fetch(
            [
                SourceInput.create(
                    locator="https://example.com/reviews",
                )
            ]
        )

        self.assertEqual(result.posts, [])
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.details[0].fetched_count, 0)
        self.assertEqual(result.details[0].error, "No source adapter can handle locator")

    def test_records_adapter_fetch_errors(self):
        resolver = SourceResolver([FailingAdapter()])

        result = resolver.fetch(
            [
                SourceInput.create(
                    locator="https://example.com/reviews",
                )
            ]
        )

        self.assertEqual(result.posts, [])
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.details[0].error, "fetch blocked")


if __name__ == "__main__":
    unittest.main()
