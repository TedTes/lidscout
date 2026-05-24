import asyncio
import unittest
from typing import Any

from api.main import app, health_check
from api.routes.signals import (
    CompetitorRequest,
    MarketRequest,
    MonitoredSourceRequest,
    MonitoredSourceUpdateRequest,
    PipelineRunRequest,
    SignalApiDependencies,
    create_competitor,
    create_competitor_source,
    create_market,
    create_market_source,
    delete_signal,
    get_market,
    get_latest_report,
    list_competitor_source_suggestions,
    list_competitor_sources,
    list_competitors,
    list_clusters,
    list_market_competitors,
    list_market_sources,
    list_markets,
    list_market_source_suggestions,
    list_opportunities,
    list_sources,
    list_signals,
    run_pipeline,
    update_source,
)
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.market import Market
from domain.opportunity import Opportunity
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import SourceInput, SourceLocator
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
from infrastructure.email import EmailClient, EmailNotifier
from infrastructure.llm import EmbeddingClient, LLMClient


class FakeSourceAdapter:
    def can_handle(self, source: SourceInput) -> bool:
        return source.locator == "https://example.com/reviews"

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        return [
            RawPost.create(
                source="web",
                source_id="review-page",
                title="Review page",
                body="Manual reporting is slow.",
            )
        ]


class FakeLLMClient(LLMClient):
    def generate_structured_response(
        self,
        prompt: str,
        post_content: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        return """
        {
          "has_signal": true,
          "is_about_competitor": true,
          "competitor_match_reason": null,
          "signal": {
            "pain": "Manual reporting is slow",
            "user_type": null,
            "job_to_be_done": null,
            "current_workaround": null,
            "urgency": 5,
            "severity": 3,
            "willingness_to_pay": 5,
            "category": "reporting",
            "confidence": 0.8
          }
        }
        """


class FakeEmbeddingClient(EmbeddingClient):
    def _generate_embedding(self, signal_text: str) -> list[float]:
        return [1.0, 0.0]


class FakeEmailNotifier(EmailNotifier):
    def send_report(self, subject: str, body: str, recipients: list[str]) -> None:
        return None


class SignalApiRouteTests(unittest.TestCase):
    def test_registers_signal_routes(self):
        paths = {route.path for route in app.routes}

        self.assertIn("/signals", paths)
        self.assertIn("/signals/{signal_id}", paths)
        self.assertIn("/clusters", paths)
        self.assertIn("/opportunities", paths)
        self.assertIn("/markets", paths)
        self.assertIn("/markets/{market_id}", paths)
        self.assertIn("/markets/{market_id}/competitors", paths)
        self.assertIn("/markets/{market_id}/sources", paths)
        self.assertIn("/markets/{market_id}/source-suggestions", paths)
        self.assertIn("/reports/latest", paths)
        self.assertIn("/pipeline/run", paths)
        self.assertIn("/competitors", paths)
        self.assertIn("/competitors/{competitor_id}/sources", paths)
        self.assertIn("/competitors/{competitor_id}/source-suggestions", paths)
        self.assertIn("/sources", paths)
        self.assertIn("/sources/{source_id}", paths)
        self.assertIn("/health", paths)

    def test_health_check_response(self):
        response = asyncio.run(health_check())

        self.assertEqual(response["status"], "healthy")
        self.assertEqual(response["service"], "lidscout-api")

    def test_lists_signals(self):
        signal_repository = InMemorySignalRepository()
        competitor_repository = InMemoryCompetitorRepository()
        market_repository = InMemoryMarketRepository()
        competitor_repository.save_competitors(
            [Competitor.create(id="competitor-1", name="Acme CRM")]
        )
        market_repository.save_markets(
            [Market.create(id="market-1", name="CRM tools")]
        )
        signal_repository.save_signals(
            [
                Signal.create(
                    id="signal-1",
                    post_id="reddit:r1",
                    pain="Manual reporting is slow",
                    category="reporting",
                    confidence=0.8,
                    competitor_id="competitor-1",
                    market_id="market-1",
                )
            ]
        )
        dependencies = self._dependencies(
            signal_repository=signal_repository,
            competitor_repository=competitor_repository,
            market_repository=market_repository,
        )

        response = asyncio.run(list_signals(dependencies))

        self.assertEqual(response["signals"][0]["id"], "signal-1")
        self.assertEqual(response["signals"][0]["pain"], "Manual reporting is slow")
        self.assertEqual(response["signals"][0]["competitor_name"], "Acme CRM")
        self.assertEqual(response["signals"][0]["market_name"], "CRM tools")

    def test_deletes_signal_and_score(self):
        signal_repository = InMemorySignalRepository()
        score_repository = InMemoryScoreRepository()
        signal = Signal.create(
            id="signal-1",
            post_id="reddit:r1",
            pain="Manual reporting is slow",
        )
        signal_repository.save_signals([signal])
        score_repository.save_scores([OpportunityScore.from_signal(signal)])
        dependencies = self._dependencies(
            signal_repository=signal_repository,
            score_repository=score_repository,
        )

        response = asyncio.run(delete_signal("signal-1", dependencies))

        self.assertEqual(response, {"id": "signal-1", "deleted": True})
        self.assertIsNone(signal_repository.get_signal("signal-1"))
        self.assertIsNone(score_repository.get_score("signal-1"))

    def test_lists_clusters(self):
        cluster_repository = InMemoryClusterRepository()
        cluster_repository.save_clusters([self._cluster()])
        dependencies = self._dependencies(cluster_repository=cluster_repository)

        response = asyncio.run(list_clusters(dependencies))

        self.assertEqual(response["clusters"][0]["id"], "cluster-1")
        self.assertEqual(response["clusters"][0]["theme"], "reporting")
        self.assertEqual(response["clusters"][0]["company_ids"], [])

    def test_cluster_response_includes_company_breadth(self):
        competitor_repository = InMemoryCompetitorRepository()
        competitor_repository.save_competitors(
            [
                Competitor.create(
                    id="competitor-1",
                    name="Acme CRM",
                    market_id="market-1",
                ),
                Competitor.create(
                    id="competitor-2",
                    name="Beta CRM",
                    market_id="market-1",
                ),
            ]
        )
        signal_repository = InMemorySignalRepository()
        signal_repository.save_signals(
            [
                Signal.create(
                    id="signal-1",
                    post_id="reddit:r1",
                    pain="Reports are slow",
                    competitor_id="competitor-1",
                    market_id="market-1",
                )
            ]
        )
        cluster_repository = InMemoryClusterRepository()
        cluster_repository.save_clusters([self._cluster()])
        dependencies = self._dependencies(
            competitor_repository=competitor_repository,
            signal_repository=signal_repository,
            cluster_repository=cluster_repository,
        )

        response = asyncio.run(list_clusters(dependencies, market_id="market-1"))

        cluster = response["clusters"][0]
        self.assertEqual(cluster["company_ids"], ["competitor-1"])
        self.assertEqual(cluster["company_names"], ["Acme CRM"])
        self.assertEqual(cluster["company_count"], 1)
        self.assertEqual(cluster["market_company_count"], 2)

    def test_gets_latest_report(self):
        cluster_repository = InMemoryClusterRepository()
        opportunity_repository = InMemoryOpportunityRepository()
        cluster_repository.save_clusters([self._cluster()])
        opportunity_repository.save_opportunities([self._opportunity()])
        dependencies = self._dependencies(
            cluster_repository=cluster_repository,
            opportunity_repository=opportunity_repository,
        )

        response = asyncio.run(get_latest_report(dependencies))

        self.assertEqual(response["title"], "LidScout Market Signal Report")
        self.assertEqual(response["top_clusters"][0]["id"], "cluster-1")
        self.assertEqual(
            response["recommended_opportunities"][0]["id"],
            "opportunity-1",
        )

    def test_gets_market_scoped_report_title(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="workspace-tools", name="Workspace Tools")]
        )
        dependencies = self._dependencies(market_repository=market_repository)

        response = asyncio.run(
            get_latest_report(dependencies, market_id="workspace-tools")
        )

        self.assertEqual(response["title"], "Workspace Tools Market Gap Report")

    def test_lists_opportunities(self):
        opportunity_repository = InMemoryOpportunityRepository()
        opportunity_repository.save_opportunities([self._opportunity()])
        dependencies = self._dependencies(
            opportunity_repository=opportunity_repository,
        )

        response = asyncio.run(list_opportunities(dependencies))

        self.assertEqual(response["opportunities"][0]["id"], "opportunity-1")
        self.assertEqual(
            response["opportunities"][0]["suggested_wedge"],
            "Build a reporting setup assistant.",
        )

    def test_market_scoped_reads_do_not_mix_markets(self):
        signal_repository = InMemorySignalRepository()
        signal_repository.save_signals(
            [
                Signal.create(
                    id="signal-workspace",
                    post_id="reddit:workspace",
                    pain="Workspace reports are slow",
                    competitor_id="competitor-workspace",
                    market_id="workspace-tools",
                ),
                Signal.create(
                    id="signal-finance",
                    post_id="reddit:finance",
                    pain="Finance exports are slow",
                    competitor_id="competitor-finance",
                    market_id="finance-tools",
                ),
            ]
        )
        cluster_repository = InMemoryClusterRepository()
        cluster_repository.save_clusters(
            [
                SignalCluster.create(
                    id="cluster-workspace",
                    theme="workspace reporting",
                    summary="Workspace teams need faster reports.",
                    signal_ids=["signal-workspace"],
                    frequency=1,
                    average_score=7.0,
                ),
                SignalCluster.create(
                    id="cluster-finance",
                    theme="finance exports",
                    summary="Finance teams need faster exports.",
                    signal_ids=["signal-finance"],
                    frequency=1,
                    average_score=8.0,
                ),
            ]
        )
        opportunity_repository = InMemoryOpportunityRepository()
        opportunity_repository.save_opportunities(
            [
                Opportunity.create(
                    id="opportunity-workspace",
                    cluster_id="cluster-workspace",
                    title="Workspace reporting assistant",
                    target_user="workspace teams",
                    pain_summary="Workspace reports are slow.",
                    why_it_matters="Reporting blocks planning.",
                    suggested_wedge="Build a faster reporting workflow.",
                    evidence_count=1,
                    confidence=0.8,
                    evidence_signal_ids=["signal-workspace"],
                ),
                Opportunity.create(
                    id="opportunity-finance",
                    cluster_id="cluster-finance",
                    title="Finance export assistant",
                    target_user="finance teams",
                    pain_summary="Finance exports are slow.",
                    why_it_matters="Exports block close workflows.",
                    suggested_wedge="Build a better export workflow.",
                    evidence_count=1,
                    confidence=0.7,
                    evidence_signal_ids=["signal-finance"],
                ),
            ]
        )
        dependencies = self._dependencies(
            signal_repository=signal_repository,
            cluster_repository=cluster_repository,
            opportunity_repository=opportunity_repository,
        )

        signals = asyncio.run(list_signals(dependencies, market_id="workspace-tools"))
        clusters = asyncio.run(list_clusters(dependencies, market_id="workspace-tools"))
        opportunities = asyncio.run(
            list_opportunities(dependencies, market_id="workspace-tools")
        )
        report = asyncio.run(get_latest_report(dependencies, market_id="workspace-tools"))

        self.assertEqual(
            [signal["id"] for signal in signals["signals"]],
            ["signal-workspace"],
        )
        self.assertEqual(
            [cluster["id"] for cluster in clusters["clusters"]],
            ["cluster-workspace"],
        )
        self.assertEqual(
            [opportunity["id"] for opportunity in opportunities["opportunities"]],
            ["opportunity-workspace"],
        )
        self.assertEqual(
            [cluster["id"] for cluster in report["top_clusters"]],
            ["cluster-workspace"],
        )

    def test_creates_and_lists_competitors(self):
        dependencies = self._dependencies()

        created = asyncio.run(
            create_competitor(
                CompetitorRequest(
                    id="competitor-1",
                    name="Acme CRM",
                    website="https://acme.example",
                    category="crm",
                ),
                dependencies,
            )
        )
        response = asyncio.run(list_competitors(dependencies))

        self.assertEqual(created["id"], "competitor-1")
        self.assertEqual(response["competitors"][0]["name"], "Acme CRM")

    def test_creates_and_lists_markets(self):
        dependencies = self._dependencies()

        created = asyncio.run(
            create_market(
                MarketRequest(
                    id="workspace-tools",
                    name="Workspace tools",
                    target_user="product teams",
                ),
                dependencies,
            )
        )
        listed = asyncio.run(list_markets(dependencies))
        loaded = asyncio.run(get_market("workspace-tools", dependencies))

        self.assertEqual(created["id"], "workspace-tools")
        self.assertEqual(listed["markets"][0]["name"], "Workspace tools")
        self.assertEqual(loaded["target_user"], "product teams")

    def test_lists_market_competitors_and_sources(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="workspace-tools", name="Workspace tools")]
        )
        competitor_repository = InMemoryCompetitorRepository()
        competitor_repository.save_competitors(
            [
                Competitor.create(
                    id="competitor-1",
                    name="Acme CRM",
                    market_id="workspace-tools",
                )
            ]
        )
        dependencies = self._dependencies(
            market_repository=market_repository,
            competitor_repository=competitor_repository,
        )

        source = asyncio.run(
            create_market_source(
                "workspace-tools",
                MonitoredSourceRequest(locator="https://example.com/reviews"),
                dependencies,
            )
        )
        competitors = asyncio.run(
            list_market_competitors("workspace-tools", dependencies)
        )
        sources = asyncio.run(list_market_sources("workspace-tools", dependencies))

        self.assertEqual(competitors["competitors"][0]["id"], "competitor-1")
        self.assertEqual(source["market_id"], "workspace-tools")
        self.assertEqual(sources["sources"][0]["market_id"], "workspace-tools")

    def test_creates_and_lists_competitor_sources(self):
        competitor_repository = InMemoryCompetitorRepository()
        competitor_repository.save_competitors(
            [Competitor.create(id="competitor-1", name="Acme CRM")]
        )
        dependencies = self._dependencies(competitor_repository=competitor_repository)

        created = asyncio.run(
            create_competitor_source(
                "competitor-1",
                MonitoredSourceRequest(
                    locator="https://acme.example/reviews",
                    source_type="reviews",
                    limit=10,
                ),
                dependencies,
            )
        )
        response = asyncio.run(list_competitor_sources("competitor-1", dependencies))

        self.assertEqual(created["competitor_id"], "competitor-1")
        self.assertEqual(response["sources"][0]["locator"], "https://acme.example/reviews")
        self.assertEqual(response["sources"][0]["competitor_name"], "Acme CRM")
        self.assertEqual(response["sources"][0]["source_family"], None)

    def test_lists_competitor_source_suggestions(self):
        competitor_repository = InMemoryCompetitorRepository()
        monitored_source_repository = InMemoryMonitoredSourceRepository()
        competitor_repository.save_competitors(
            [
                Competitor.create(
                    id="notion",
                    name="Notion",
                    website="https://www.notion.so",
                )
            ]
        )
        existing_source = asyncio.run(
            create_competitor_source(
                "notion",
                MonitoredSourceRequest(
                    locator="https://www.reddit.com/search.json?q=Notion&sort=new",
                    source_type="reddit_search",
                ),
                self._dependencies(
                    competitor_repository=competitor_repository,
                    monitored_source_repository=monitored_source_repository,
                ),
            )
        )
        dependencies = self._dependencies(
            competitor_repository=competitor_repository,
            monitored_source_repository=monitored_source_repository,
        )

        response = asyncio.run(
            list_competitor_source_suggestions("notion", dependencies)
        )

        self.assertGreaterEqual(len(response["suggestions"]), 6)
        self.assertIn(
            "https://www.g2.com/search?query=Notion",
            [suggestion["locator"] for suggestion in response["suggestions"]],
        )
        existing = next(
            suggestion
            for suggestion in response["suggestions"]
            if suggestion["locator"] == existing_source["locator"]
        )
        self.assertTrue(existing["already_monitored"])

    def test_lists_market_source_suggestions(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="ai-devtools", name="AI Devtools")]
        )
        monitored_source_repository = InMemoryMonitoredSourceRepository()
        dependencies = self._dependencies(
            market_repository=market_repository,
            monitored_source_repository=monitored_source_repository,
        )

        response = asyncio.run(
            list_market_source_suggestions("ai-devtools", dependencies)
        )

        self.assertIn(
            "https://www.reddit.com/search.json?q=AI+Devtools&sort=new",
            [suggestion["locator"] for suggestion in response["suggestions"]],
        )
        self.assertIn(
            "source_family",
            response["suggestions"][0],
        )

    def test_lists_sources_across_competitors(self):
        competitor_repository = InMemoryCompetitorRepository()
        competitor_repository.save_competitors(
            [
                Competitor.create(id="competitor-1", name="Acme CRM"),
                Competitor.create(id="competitor-2", name="Other CRM"),
            ]
        )
        monitored_source_repository = InMemoryMonitoredSourceRepository()
        dependencies = self._dependencies(
            competitor_repository=competitor_repository,
            monitored_source_repository=monitored_source_repository,
        )

        asyncio.run(
            create_competitor_source(
                "competitor-1",
                MonitoredSourceRequest(
                    locator="https://acme.example/reviews",
                    source_type="reviews",
                ),
                dependencies,
            )
        )
        asyncio.run(
            create_competitor_source(
                "competitor-2",
                MonitoredSourceRequest(
                    locator="https://other.example/reviews",
                    source_type="reviews",
                    enabled=False,
                ),
                dependencies,
            )
        )

        all_sources = asyncio.run(list_sources(dependencies=dependencies))
        enabled_sources = asyncio.run(list_sources(enabled=True, dependencies=dependencies))

        self.assertEqual(len(all_sources["sources"]), 2)
        self.assertEqual(len(enabled_sources["sources"]), 1)
        self.assertEqual(enabled_sources["sources"][0]["competitor_id"], "competitor-1")

    def test_updates_monitored_source(self):
        competitor_repository = InMemoryCompetitorRepository()
        competitor_repository.save_competitors(
            [Competitor.create(id="competitor-1", name="Acme CRM")]
        )
        dependencies = self._dependencies(competitor_repository=competitor_repository)
        created = asyncio.run(
            create_competitor_source(
                "competitor-1",
                MonitoredSourceRequest(
                    locator="https://acme.example/reviews",
                    source_type="reviews",
                    limit=10,
                ),
                dependencies,
            )
        )

        updated = asyncio.run(
            update_source(
                created["id"],
                MonitoredSourceUpdateRequest(
                    source_type="forum",
                    enabled=False,
                    limit=25,
                    options={"section": "support"},
                ),
                dependencies,
            )
        )

        self.assertEqual(updated["source_type"], "forum")
        self.assertFalse(updated["enabled"])
        self.assertEqual(updated["limit"], 25)
        self.assertEqual(updated["options"], {"section": "support"})
        self.assertEqual(
            dependencies.monitored_source_repository.get_monitored_source(
                created["id"]
            ).source_type,
            "forum",
        )

    def test_runs_pipeline_with_sources(self):
        signal_repository = InMemorySignalRepository()
        cluster_repository = InMemoryClusterRepository()
        opportunity_repository = InMemoryOpportunityRepository()
        dependencies = self._dependencies(
            signal_repository=signal_repository,
            cluster_repository=cluster_repository,
            opportunity_repository=opportunity_repository,
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )

        response = asyncio.run(
            run_pipeline(
                PipelineRunRequest(
                    recipient="founder@example.com",
                    sources=[
                        {
                            "locator": "https://example.com/reviews",
                            "limit": 1,
                        }
                    ],
                ),
                dependencies,
            )
        )

        self.assertEqual(response["fetched_count"], 1)
        self.assertEqual(response["extracted_count"], 1)
        self.assertEqual(response["clustered_count"], 1)
        self.assertEqual(
            response["opportunity_synthesis"],
            {
                "synthesized_count": 1,
                "inserted_count": 1,
                "failed_count": 0,
            },
        )
        self.assertTrue(response["email"]["sent"])
        self.assertEqual(signal_repository.list_signals()[0].pain, "Manual reporting is slow")
        self.assertEqual(cluster_repository.get_cluster("cluster-1").theme, "reporting")
        self.assertIsNotNone(
            opportunity_repository.get_opportunity("opportunity-cluster-1")
        )

    def test_runs_pipeline_with_configured_source_locators(self):
        source_locator_repository = InMemorySourceLocatorRepository()
        source_locator_repository.save_source_locators(
            [
                SourceLocator.create(
                    id="locator-1",
                    locator="https://example.com/reviews",
                )
            ]
        )
        dependencies = self._dependencies(
            source_locator_repository=source_locator_repository,
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )

        response = asyncio.run(
            run_pipeline(
                PipelineRunRequest(
                    recipient="founder@example.com",
                    sources=[],
                ),
                dependencies,
            )
        )

        self.assertEqual(response["fetched_count"], 1)
        self.assertEqual(response["extracted_count"], 1)

    def _dependencies(
        self,
        *,
        post_repository=None,
        signal_repository=None,
        score_repository=None,
        cluster_repository=None,
        opportunity_repository=None,
        competitor_repository=None,
        market_repository=None,
        monitored_source_repository=None,
        source_locator_repository=None,
        source_adapters=None,
        llm_client=None,
        embedding_client=None,
        email_client=None,
    ) -> SignalApiDependencies:
        return SignalApiDependencies(
            post_repository=post_repository or InMemoryPostRepository(),
            signal_repository=signal_repository or InMemorySignalRepository(),
            score_repository=score_repository or InMemoryScoreRepository(),
            cluster_repository=cluster_repository or InMemoryClusterRepository(),
            opportunity_repository=(
                opportunity_repository or InMemoryOpportunityRepository()
            ),
            competitor_repository=competitor_repository or InMemoryCompetitorRepository(),
            market_repository=market_repository or InMemoryMarketRepository(),
            monitored_source_repository=(
                monitored_source_repository or InMemoryMonitoredSourceRepository()
            ),
            source_locator_repository=(
                source_locator_repository or InMemorySourceLocatorRepository()
            ),
            source_adapters=source_adapters or [],
            llm_client=llm_client,
            embedding_client=embedding_client,
            email_client=email_client,
        )

    @staticmethod
    def _cluster() -> SignalCluster:
        return SignalCluster.create(
            id="cluster-1",
            theme="reporting",
            summary="Teams need faster reports.",
            signal_ids=["signal-1"],
            frequency=2,
            average_score=8.4,
            top_examples=["Manual reporting is slow."],
        )

    @staticmethod
    def _opportunity() -> Opportunity:
        return Opportunity.create(
            id="opportunity-1",
            cluster_id="cluster-1",
            title="Improve recurring reports",
            target_user="finance teams",
            pain_summary="Teams need faster reports.",
            why_it_matters="Repeated evidence with strong scores.",
            suggested_wedge="Build a reporting setup assistant.",
            evidence_count=2,
            confidence=0.84,
            evidence_signal_ids=["signal-1"],
        )


if __name__ == "__main__":
    unittest.main()
