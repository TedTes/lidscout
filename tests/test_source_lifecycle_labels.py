import unittest
from datetime import UTC, datetime

from api.routes.signals import _serialize_niche_source
from domain.niche import NicheSource


class SourceLifecycleLabelTests(unittest.TestCase):
    def test_labels_unscanned_enabled_sources_as_candidates(self):
        source = NicheSource.create(
            id="source-1",
            niche_id="niche-1",
            locator="https://example.com",
            source_type="hackernews_search",
            source_family="technical_forum",
            is_gate_free=True,
        )

        payload = _serialize_niche_source(source)

        self.assertEqual(payload["lifecycle"], "candidate")
        self.assertIn("first scan", payload["lifecycle_reason"])

    def test_labels_proxy_sources_as_needing_proxy(self):
        source = NicheSource.create(
            id="source-1",
            niche_id="niche-1",
            locator="https://www.g2.com/search?query=example",
            source_type="g2",
            source_family="reviews",
            is_gate_free=False,
            requires_proxy=True,
        )

        payload = _serialize_niche_source(source)

        self.assertFalse(payload["enabled"])
        self.assertEqual(payload["lifecycle"], "needs_proxy")

    def test_labels_failing_and_verified_sources(self):
        failing = NicheSource.create(
            id="source-1",
            niche_id="niche-1",
            locator="https://example.com",
            source_type="hackernews_search",
            source_family="technical_forum",
            is_gate_free=True,
            health_status="failing",
            last_error="blocked",
        )
        verified = NicheSource.create(
            id="source-2",
            niche_id="niche-1",
            locator="https://github.com/example/project/issues",
            source_type="github_issues",
            source_family="technical_forum",
            is_gate_free=True,
            buyer_voice_verified=True,
            last_scanned_at=datetime(2026, 6, 2, tzinfo=UTC),
        )

        self.assertEqual(_serialize_niche_source(failing)["lifecycle"], "failing")
        self.assertEqual(_serialize_niche_source(verified)["lifecycle"], "verified")


if __name__ == "__main__":
    unittest.main()
