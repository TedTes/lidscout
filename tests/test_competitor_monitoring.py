import unittest

from domain.competitor import Competitor
from domain.source import MonitoredSource


class CompetitorMonitoringTests(unittest.TestCase):
    def test_creates_competitor(self):
        competitor = Competitor.create(
            id="competitor-1",
            name="Acme CRM",
            website="https://acme.example",
            category="crm",
            market_id="workspace-tools",
        )

        self.assertEqual(competitor.id, "competitor-1")
        self.assertEqual(competitor.name, "Acme CRM")
        self.assertEqual(competitor.website, "https://acme.example")
        self.assertEqual(competitor.category, "crm")
        self.assertEqual(competitor.market_id, "workspace-tools")
        self.assertIsNotNone(competitor.created_at)

    def test_creates_monitored_source_with_pipeline_context(self):
        source = MonitoredSource.create(
            id="source-1",
            competitor_id="competitor-1",
            market_id="workspace-tools",
            locator="https://acme.example/reviews",
            source_type="reviews",
            limit=10,
        )

        source_input = source.to_source_input()

        self.assertEqual(source.competitor_id, "competitor-1")
        self.assertEqual(source.market_id, "workspace-tools")
        self.assertEqual(source.locator, "https://acme.example/reviews")
        self.assertEqual(source.source_type, "reviews")
        self.assertEqual(source_input.options["competitor_id"], "competitor-1")
        self.assertEqual(source_input.options["market_id"], "workspace-tools")
        self.assertEqual(source_input.options["monitored_source_id"], "source-1")
        self.assertEqual(source_input.options["source_type"], "reviews")

    def test_creates_market_scoped_monitored_source(self):
        source = MonitoredSource.create(
            id="source-1",
            market_id="workspace-tools",
            locator="https://example.com/reviews",
        )

        self.assertIsNone(source.competitor_id)
        self.assertEqual(source.market_id, "workspace-tools")
        self.assertEqual(
            source.to_source_input().options["market_id"],
            "workspace-tools",
        )

    def test_rejects_monitored_source_without_scope(self):
        with self.assertRaises(ValueError):
            MonitoredSource.create(locator="https://example.com/reviews")

    def test_rejects_non_url_monitored_source_locator(self):
        with self.assertRaises(ValueError):
            MonitoredSource.create(
                competitor_id="competitor-1",
                locator="garbage",
            )


if __name__ == "__main__":
    unittest.main()
