import unittest

from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.market import Market
from domain.opportunity import Opportunity
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import MonitoredSource, SourceLocator
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryCompetitorRepository,
    InMemoryMarketRepository,
    InMemoryMonitoredSourceRepository,
    InMemoryOpportunityRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemorySourceLocatorRepository,
)


class RepositoryInterfaceTests(unittest.TestCase):
    def test_post_repository_persists_unique_posts(self):
        repository = InMemoryPostRepository()
        post = RawPost.create(source="reddit", source_id="abc", title="Reporting pain")

        saved_count = repository.save_posts([post, post])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.posts["reddit:abc"], post)
        self.assertEqual(repository.get_post("reddit:abc"), post)
        self.assertEqual(repository.list_posts(), [post])

    def test_signal_repository_persists_unique_signals(self):
        repository = InMemorySignalRepository()
        signal = Signal.create(
            id="signal-1",
            post_id="reddit:abc",
            pain="Manual reporting is slow",
        )

        saved_count = repository.save_signals([signal, signal])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.signals["signal-1"], signal)
        self.assertEqual(repository.get_signal("signal-1"), signal)
        self.assertEqual(repository.list_signals(), [signal])
        self.assertTrue(repository.delete_signal("signal-1"))
        self.assertIsNone(repository.get_signal("signal-1"))

    def test_score_repository_persists_unique_scores(self):
        repository = InMemoryScoreRepository()
        score = OpportunityScore(
            signal_id="signal-1",
            total_score=8.0,
            urgency_score=5.0,
            severity_score=3.0,
            willingness_score=5.0,
            confidence_score=4.0,
            reasoning="test",
        )

        saved_count = repository.save_scores([score, score])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.scores["signal-1"], score)
        self.assertEqual(repository.get_score("signal-1"), score)
        self.assertEqual(repository.list_scores(), [score])
        self.assertTrue(repository.delete_score("signal-1"))
        self.assertIsNone(repository.get_score("signal-1"))

    def test_cluster_repository_persists_unique_clusters(self):
        repository = InMemoryClusterRepository()
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="reporting",
            summary="Teams need faster reporting.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=8.0,
        )

        saved_count = repository.save_clusters([cluster, cluster])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.clusters["cluster-1"], cluster)
        self.assertEqual(repository.get_cluster("cluster-1"), cluster)
        self.assertEqual(repository.list_clusters(), [cluster])

    def test_opportunity_repository_persists_unique_opportunities(self):
        repository = InMemoryOpportunityRepository()
        opportunity = Opportunity.create(
            id="opportunity-1",
            cluster_id="cluster-1",
            title="Reduce reporting setup friction",
            target_user="finance teams",
            pain_summary="Finance teams cannot get useful reports quickly.",
            why_it_matters="The cluster has repeated evidence of reporting pain.",
            suggested_wedge="Ship a focused reporting setup assistant.",
            evidence_count=2,
            confidence=0.82,
            evidence_signal_ids=["signal-1", "signal-2"],
        )

        saved_count = repository.save_opportunities([opportunity, opportunity])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.opportunities["opportunity-1"], opportunity)
        self.assertEqual(repository.get_opportunity("opportunity-1"), opportunity)
        self.assertEqual(repository.list_opportunities(), [opportunity])

    def test_market_repository_persists_unique_markets(self):
        repository = InMemoryMarketRepository()
        market = Market.create(
            id="workspace-tools",
            name="Workspace tools",
            target_user="product teams",
        )

        saved_count = repository.save_markets([market, market])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.markets["workspace-tools"], market)
        self.assertEqual(repository.get_market("workspace-tools"), market)
        self.assertEqual(repository.list_markets(), [market])

        updated = Market.create(id="workspace-tools", name="Workspace intelligence")
        self.assertTrue(repository.update_market(updated))
        self.assertEqual(repository.get_market("workspace-tools"), updated)
        self.assertFalse(repository.update_market(Market.create(id="missing", name="Missing")))
        self.assertTrue(repository.delete_market("workspace-tools"))
        self.assertFalse(repository.delete_market("workspace-tools"))

    def test_source_locator_repository_persists_unique_locators(self):
        repository = InMemorySourceLocatorRepository()
        locator = SourceLocator.create(
            id="locator-1",
            locator="https://example.com/reviews",
        )

        saved_count = repository.save_source_locators([locator, locator])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.source_locators["locator-1"], locator)
        self.assertEqual(repository.get_source_locator("locator-1"), locator)
        self.assertEqual(repository.list_source_locators(enabled=True), [locator])

    def test_competitor_repository_persists_unique_competitors(self):
        repository = InMemoryCompetitorRepository()
        competitor = Competitor.create(id="competitor-1", name="Acme CRM")

        saved_count = repository.save_competitors([competitor, competitor])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.competitors["competitor-1"], competitor)
        self.assertEqual(repository.get_competitor("competitor-1"), competitor)
        self.assertEqual(repository.list_competitors(), [competitor])

    def test_monitored_source_repository_filters_sources(self):
        repository = InMemoryMonitoredSourceRepository()
        source = MonitoredSource.create(
            id="source-1",
            competitor_id="competitor-1",
            market_id="market-1",
            locator="https://acme.example/reviews",
        )
        disabled_source = MonitoredSource.create(
            id="source-2",
            competitor_id="competitor-2",
            market_id="market-2",
            locator="https://other.example/reviews",
            enabled=False,
        )

        saved_count = repository.save_monitored_sources(
            [source, source, disabled_source]
        )

        self.assertEqual(saved_count, 2)
        self.assertEqual(repository.get_monitored_source("source-1"), source)
        self.assertEqual(
            repository.list_monitored_sources(competitor_id="competitor-1"),
            [source],
        )
        self.assertEqual(
            repository.list_monitored_sources(market_id="market-1"),
            [source],
        )
        self.assertEqual(repository.list_monitored_sources(enabled=False), [disabled_source])
        updated_source = MonitoredSource.create(
            id="source-1",
            competitor_id="competitor-1",
            market_id="market-1",
            locator="https://acme.example/reviews",
            source_type="forum",
            enabled=False,
            limit=25,
        )
        self.assertTrue(repository.update_monitored_source(updated_source))
        self.assertEqual(repository.get_monitored_source("source-1"), updated_source)


if __name__ == "__main__":
    unittest.main()
