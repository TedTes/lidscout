import asyncio
import unittest
from typing import Any

from fastapi import HTTPException

from api.main import app, health_check
from api.routes.signals import (
    AgentFeedbackRequest,
    AgentPreferencesRequest,
    CompetitorRequest,
    MarketRequest,
    MarketUpdateRequest,
    MonitoredSourceRequest,
    MonitoredSourceUpdateRequest,
    PipelineRunRequest,
    SignalApiDependencies,
    create_competitor,
    create_competitor_source,
    create_market,
    create_market_competitor,
    create_market_source,
    create_opportunity_feedback,
    delete_market,
    delete_signal,
    get_market_agent_cold_start,
    get_market_agent_preferences,
    get_market,
    get_latest_report,
    list_competitor_source_suggestions,
    list_competitor_sources,
    list_competitors,
    list_clusters,
    list_market_competitors,
    list_market_agent_feedback,
    list_market_sources,
    list_markets,
    list_market_source_suggestions,
    list_opportunities,
    list_pipeline_runs,
    list_sources,
    list_signals,
    run_pipeline,
    update_source,
    update_market,
    update_market_agent_preferences,
)
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.market import Market
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import SourceHealth, SourceInput, SourceLocator
from infrastructure.db import (
    InMemoryAgentFeedbackRepository,
    InMemoryClusterRepository,
    InMemoryCompetitorRepository,
    InMemoryMarketRepository,
    InMemoryMonitoredSourceRepository,
    InMemoryOpportunityRepository,
    InMemoryPipelineRunMetricsRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemorySourceHealthRepository,
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
        self.assertIn("/markets/{market_id}/agent/cold-start", paths)
        self.assertIn("/markets/{market_id}/agent/preferences", paths)
        self.assertIn("/markets/{market_id}/agent/feedback", paths)
        self.assertIn("/opportunities/{opportunity_id}/feedback", paths)
        self.assertIn("/reports/latest", paths)
        self.assertIn("/pipeline/run", paths)
        self.assertIn("/pipeline/runs", paths)
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

    def test_market_opportunities_are_ranked_by_agent_feedback(self):
        signal_repository = InMemorySignalRepository()
        signal_repository.save_signals(
            [
                Signal.create(
                    id="signal-low",
                    post_id="reddit:low",
                    pain="Calendar sync fails",
                    market_id="workspace-tools",
                ),
                Signal.create(
                    id="signal-high",
                    post_id="reddit:high",
                    pain="Templates are hard to find",
                    market_id="workspace-tools",
                ),
            ]
        )
        opportunity_repository = InMemoryOpportunityRepository()
        opportunity_repository.save_opportunities(
            [
                Opportunity.create(
                    id="opportunity-saved",
                    cluster_id="cluster-low",
                    title="Calendar reliability",
                    target_user="admins",
                    pain_summary="Calendar sync fails.",
                    why_it_matters="It blocks adoption.",
                    suggested_wedge="Build reliable sync recovery.",
                    evidence_count=1,
                    confidence=0.6,
                    evidence_signal_ids=["signal-low"],
                ),
                Opportunity.create(
                    id="opportunity-baseline",
                    cluster_id="cluster-high",
                    title="Template discovery",
                    target_user="admins",
                    pain_summary="Templates are hard to find.",
                    why_it_matters="It slows setup.",
                    suggested_wedge="Build better template search.",
                    evidence_count=1,
                    confidence=0.8,
                    evidence_signal_ids=["signal-high"],
                ),
            ]
        )
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="workspace-tools", name="Workspace tools")]
        )
        dependencies = self._dependencies(
            market_repository=market_repository,
            signal_repository=signal_repository,
            opportunity_repository=opportunity_repository,
        )
        asyncio.run(
            create_opportunity_feedback(
                "opportunity-saved",
                AgentFeedbackRequest(
                    market_id="workspace-tools",
                    action="save",
                ),
                dependencies,
            )
        )

        response = asyncio.run(
            list_opportunities(dependencies, market_id="workspace-tools")
        )

        self.assertEqual(response["opportunities"][0]["id"], "opportunity-saved")

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

    def test_updates_market(self):
        dependencies = self._dependencies()
        dependencies.market_repository.save_markets(
            [
                Market.create(
                    id="workspace-tools",
                    name="Workspace tools",
                    description="Old description",
                    target_user="product teams",
                )
            ]
        )

        updated = asyncio.run(
            update_market(
                "workspace-tools",
                MarketUpdateRequest(name="Workspace intelligence"),
                dependencies,
            )
        )
        loaded = dependencies.market_repository.get_market("workspace-tools")

        self.assertEqual(updated["name"], "Workspace intelligence")
        self.assertEqual(updated["description"], "Old description")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Workspace intelligence")

    def test_deletes_market(self):
        dependencies = self._dependencies()
        dependencies.market_repository.save_markets(
            [Market.create(id="workspace-tools", name="Workspace tools")]
        )

        deleted = asyncio.run(delete_market("workspace-tools", dependencies))

        self.assertEqual(deleted, {"id": "workspace-tools", "deleted": True})
        self.assertIsNone(dependencies.market_repository.get_market("workspace-tools"))

    def test_gets_market_agent_cold_start_plan(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="devtools", name="Developer tools")]
        )
        dependencies = self._dependencies(market_repository=market_repository)

        response = asyncio.run(get_market_agent_cold_start("devtools", dependencies))

        self.assertEqual(response["status"], "setup_needed")
        self.assertEqual(response["brief"]["niche_name"], "Developer tools")
        self.assertIn("add_companies", response["next_actions"])
        self.assertIn("add_sources", response["next_actions"])
        self.assertGreater(response["suggested_source_count"], 0)

    def test_updates_market_agent_preferences(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="devtools", name="Developer tools")]
        )
        dependencies = self._dependencies(market_repository=market_repository)

        updated = asyncio.run(
            update_market_agent_preferences(
                "devtools",
                AgentPreferencesRequest(
                    preferred_source_families=["technical_forum", "reviews"],
                    ignored_themes=["pricing"],
                    extra_instructions="Prioritize enterprise buyer pain.",
                ),
                dependencies,
            )
        )
        loaded = asyncio.run(get_market_agent_preferences("devtools", dependencies))

        self.assertEqual(
            updated["preferred_source_families"],
            ["technical_forum", "reviews"],
        )
        self.assertEqual(loaded["ignored_themes"], ["pricing"])
        self.assertEqual(
            loaded["extra_instructions"],
            "Prioritize enterprise buyer pain.",
        )

    def test_creates_opportunity_feedback(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="devtools", name="Developer tools")]
        )
        opportunity_repository = InMemoryOpportunityRepository()
        opportunity_repository.save_opportunities([self._opportunity()])
        dependencies = self._dependencies(
            market_repository=market_repository,
            opportunity_repository=opportunity_repository,
        )

        created = asyncio.run(
            create_opportunity_feedback(
                "opportunity-1",
                AgentFeedbackRequest(
                    market_id="devtools",
                    action="save",
                    reason="Relevant to current roadmap.",
                ),
                dependencies,
            )
        )
        listed = asyncio.run(list_market_agent_feedback("devtools", dependencies))

        self.assertEqual(created["action"], "save")
        self.assertEqual(created["opportunity_id"], "opportunity-1")
        self.assertEqual(listed["feedback"][0]["reason"], "Relevant to current roadmap.")

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
        self.assertEqual(sources["summary"]["source_count"], 1)
        self.assertEqual(sources["summary"]["active_count"], 1)

    def test_creates_market_competitor_from_market_route(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="workspace-tools", name="Workspace tools")]
        )
        competitor_repository = InMemoryCompetitorRepository()
        dependencies = self._dependencies(
            market_repository=market_repository,
            competitor_repository=competitor_repository,
        )

        created = asyncio.run(
            create_market_competitor(
                "workspace-tools",
                CompetitorRequest(
                    id="notion",
                    name="Notion",
                    website="https://www.notion.so",
                ),
                dependencies,
            )
        )
        competitors = asyncio.run(
            list_market_competitors("workspace-tools", dependencies)
        )

        self.assertEqual(created["market_id"], "workspace-tools")
        self.assertEqual(competitors["competitors"][0]["id"], "notion")

    def test_rejects_market_competitor_when_request_market_conflicts(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="workspace-tools", name="Workspace tools")]
        )
        dependencies = self._dependencies(market_repository=market_repository)

        with self.assertRaises(HTTPException) as exc:
            asyncio.run(
                create_market_competitor(
                    "workspace-tools",
                    CompetitorRequest(
                        id="notion",
                        name="Notion",
                        market_id="finance-tools",
                    ),
                    dependencies,
                )
            )

        self.assertEqual(exc.exception.status_code, 400)

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
        competitor_repository = InMemoryCompetitorRepository()
        competitor_repository.save_competitors(
            [
                Competitor.create(
                    id="supabase",
                    name="Supabase",
                    category="devtools",
                    market_id="ai-devtools",
                )
            ]
        )
        monitored_source_repository = InMemoryMonitoredSourceRepository()
        dependencies = self._dependencies(
            market_repository=market_repository,
            competitor_repository=competitor_repository,
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
        company_suggestion = next(
            suggestion
            for suggestion in response["suggestions"]
            if suggestion["locator"] == "https://www.g2.com/search?query=Supabase"
        )
        self.assertEqual(company_suggestion["competitor_id"], "supabase")
        self.assertEqual(company_suggestion["market_id"], "ai-devtools")

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
                    options={"source_family": "reviews"},
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
                    options={"source_family": "reviews"},
                ),
                dependencies,
            )
        )

        all_sources = asyncio.run(list_sources(dependencies=dependencies))
        enabled_sources = asyncio.run(list_sources(enabled=True, dependencies=dependencies))

        self.assertEqual(len(all_sources["sources"]), 2)
        self.assertEqual(all_sources["summary"]["source_count"], 2)
        self.assertEqual(all_sources["summary"]["active_count"], 1)
        self.assertEqual(all_sources["summary"]["disabled_count"], 1)
        self.assertEqual(all_sources["summary"]["company_count"], 2)
        self.assertEqual(
            all_sources["summary"]["by_family"][0],
            {
                "source_family": "reviews",
                "source_count": 2,
                "active_count": 1,
                "error_count": 0,
                "company_count": 2,
            },
        )
        self.assertEqual(len(enabled_sources["sources"]), 1)
        self.assertEqual(enabled_sources["sources"][0]["competitor_id"], "competitor-1")

    def test_lists_sources_with_health_snapshot(self):
        competitor_repository = InMemoryCompetitorRepository()
        competitor_repository.save_competitors(
            [Competitor.create(id="competitor-1", name="Acme CRM")]
        )
        monitored_source_repository = InMemoryMonitoredSourceRepository()
        source_health_repository = InMemorySourceHealthRepository()
        dependencies = self._dependencies(
            competitor_repository=competitor_repository,
            monitored_source_repository=monitored_source_repository,
            source_health_repository=source_health_repository,
        )
        created = asyncio.run(
            create_competitor_source(
                "competitor-1",
                MonitoredSourceRequest(
                    locator="https://acme.example/reviews",
                    source_type="reviews",
                ),
                dependencies,
            )
        )
        source_health_repository.save_source_health(
            SourceHealth.create(
                monitored_source_id=created["id"],
                total_runs=2,
                success_count=1,
                failure_count=1,
                posts_fetched_count=10,
                relevant_posts_count=4,
                extracted_signals_count=2,
                last_status="failing",
                last_error="Blocked",
            )
        )

        response = asyncio.run(list_sources(dependencies=dependencies))

        health = response["sources"][0]["health"]
        self.assertEqual(health["last_status"], "failing")
        self.assertEqual(health["failure_count"], 1)
        self.assertEqual(health["fetch_success_rate"], 0.5)
        self.assertEqual(health["relevance_yield_rate"], 0.4)

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

    def test_lists_recent_pipeline_runs(self):
        metrics_repository = InMemoryPipelineRunMetricsRepository()
        metrics_repository.save_pipeline_run_metrics(
            PipelineRunMetrics.create(
                id="run-old",
                fetched_count=1,
                fetch_failed_count=0,
                rule_filtered_count=0,
                llm_filtered_count=0,
                relevance_failed_count=0,
                extraction_attempted_count=1,
                extracted_count=1,
                no_signal_count=0,
                extraction_failed_count=0,
                signal_inserted_count=1,
                scored_count=1,
                scoring_failed_count=0,
                average_score=6.5,
                embedding_failed_count=0,
                clustered_count=1,
                cluster_inserted_count=1,
                opportunity_synthesized_count=1,
                opportunity_inserted_count=1,
                opportunity_failed_count=0,
                email_sent=True,
            )
        )
        metrics_repository.save_pipeline_run_metrics(
            PipelineRunMetrics.create(
                id="run-new",
                fetched_count=2,
                fetch_failed_count=0,
                rule_filtered_count=1,
                llm_filtered_count=0,
                relevance_failed_count=0,
                extraction_attempted_count=1,
                extracted_count=1,
                no_signal_count=0,
                extraction_failed_count=0,
                signal_inserted_count=1,
                scored_count=1,
                scoring_failed_count=0,
                average_score=7.5,
                embedding_failed_count=0,
                clustered_count=1,
                cluster_inserted_count=1,
                opportunity_synthesized_count=1,
                opportunity_inserted_count=1,
                opportunity_failed_count=0,
                email_sent=False,
                email_error="Forbidden",
            )
        )
        dependencies = self._dependencies(
            pipeline_run_metrics_repository=metrics_repository,
        )

        response = asyncio.run(list_pipeline_runs(dependencies, limit=1))

        self.assertEqual(len(response["runs"]), 1)
        self.assertEqual(response["runs"][0]["id"], "run-new")
        self.assertEqual(response["runs"][0]["fetched_count"], 2)
        self.assertEqual(response["runs"][0]["email_error"], "Forbidden")

    def _dependencies(
        self,
        *,
        post_repository=None,
        signal_repository=None,
        score_repository=None,
        cluster_repository=None,
        opportunity_repository=None,
        pipeline_run_metrics_repository=None,
        agent_feedback_repository=None,
        competitor_repository=None,
        market_repository=None,
        monitored_source_repository=None,
        source_health_repository=None,
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
            pipeline_run_metrics_repository=(
                pipeline_run_metrics_repository
                or InMemoryPipelineRunMetricsRepository()
            ),
            agent_feedback_repository=(
                agent_feedback_repository or InMemoryAgentFeedbackRepository()
            ),
            competitor_repository=competitor_repository or InMemoryCompetitorRepository(),
            market_repository=market_repository or InMemoryMarketRepository(),
            monitored_source_repository=(
                monitored_source_repository or InMemoryMonitoredSourceRepository()
            ),
            source_health_repository=(
                source_health_repository or InMemorySourceHealthRepository()
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
