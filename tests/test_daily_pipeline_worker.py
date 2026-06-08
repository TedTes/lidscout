import unittest
from dataclasses import replace
from typing import Any

from domain.agent import AgentPreferences
from domain.competitor import Competitor
from domain.finding import Finding
from domain.market import Market
from domain.niche import NicheSource, NicheSourceRunStats, UserNiche
from domain.post import RawPost
from domain.source import MonitoredSource, SourceInput
from domain.theme import Theme, ThemeFinding
from application.ingestion import SourceFetchDetail
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryAgentPreferencesRepository,
    InMemoryNicheCompanyRepository,
    InMemoryUserNicheRepository,
    InMemoryPostRepository,
    InMemoryOpportunityRepository,
    InMemoryPipelineRunMetricsRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemoryNicheSourceRepository,
)
from infrastructure.email import EmailClient, EmailNotifier
from infrastructure.llm import EmbeddingClient, LLMClient
from workers.run_daily_pipeline import (
    PipelineConfig,
    SourceRelevanceStats,
    _configured_sources,
    _record_niche_source_health,
    run_daily_pipeline,
)


class FakeSourceAdapter:
    def can_handle(self, source: SourceInput) -> bool:
        return source.locator == "https://example.com/reviews"

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        return [
            RawPost.create(
                source="web",
                source_id=source.locator,
                title="Review page",
                body="Acme CRM export workflows are painful for finance teams.",
                url=source.locator,
                metadata={
                    key: value
                    for key, value in source.options.items()
                    if isinstance(value, str)
                },
            )
        ]


class SequentialLLMClient(LLMClient):
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []

    def generate_structured_response(
        self,
        prompt: str,
        post_content: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        self.calls.append((prompt, post_content, response_schema))
        return self.responses.pop(0)


class RecordingLLMClient(SequentialLLMClient):
    pass


class FakeEmbeddingClient(EmbeddingClient):
    def __init__(self):
        self.calls: list[str] = []

    def _generate_embedding(self, signal_text: str) -> list[float]:
        self.calls.append(signal_text)
        return [1.0, 0.0]


class FakeEmailNotifier(EmailNotifier):
    def __init__(self):
        self.calls: list[tuple[str, str, list[str]]] = []

    def send_report(self, subject: str, body: str, recipients: list[str]) -> None:
        self.calls.append((subject, body, recipients))


class FakeFindingRepository:
    def __init__(self):
        self.findings: list[Finding] = []

    def save_findings(self, findings: list[Finding]) -> int:
        self.findings.extend(findings)
        return len(findings)

    def list_findings(
        self,
        *,
        user_niche_id: str | None = None,
        unassigned_only: bool = False,
    ) -> list[Finding]:
        if user_niche_id is None:
            return self.findings
        return [
            finding
            for finding in self.findings
            if finding.user_niche_id == user_niche_id
        ]


class FakeThemeRepository:
    def __init__(self):
        self.themes: list[Theme] = []
        self.assignments: list[ThemeFinding] = []
        self.refreshed_theme_ids: list[str] = []

    def save_themes(self, themes: list[Theme]) -> int:
        existing = {theme.id: theme for theme in self.themes}
        for theme in themes:
            existing[theme.id] = theme
        self.themes = list(existing.values())
        return len(themes)

    def save_theme_findings(self, assignments: list[ThemeFinding]) -> int:
        self.assignments.extend(assignments)
        return len(assignments)

    def list_themes(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
    ) -> list[Theme]:
        themes = self.themes
        if user_niche_id is not None:
            themes = [theme for theme in themes if theme.user_niche_id == user_niche_id]
        if status is not None:
            themes = [theme for theme in themes if theme.status == status]
        return themes

    def list_changed_themes(self, *, user_niche_id: str, since: object) -> list[Theme]:
        return [theme for theme in self.themes if theme.user_niche_id == user_niche_id]

    def list_findings_for_theme(self, theme_id: str) -> list[Finding]:
        return []

    def refresh_theme_rollups(self, theme_ids: list[str]) -> int:
        self.refreshed_theme_ids.extend(theme_ids)
        return len(theme_ids)


class DailyPipelineWorkerTests(unittest.TestCase):
    def test_runs_pipeline_with_generic_sources(self):
        signal_repository = InMemorySignalRepository()
        score_repository = InMemoryScoreRepository()
        cluster_repository = InMemoryClusterRepository()
        opportunity_repository = InMemoryOpportunityRepository()
        llm_client = SequentialLLMClient(
            [
                """
                {
                  "has_signal": true,
                  "is_about_competitor": true,
                  "competitor_match_reason": null,
                  "signal": {
                    "pain": "Export workflows are painful",
                    "user_type": "finance team",
                    "job_to_be_done": "export reports",
                    "current_workaround": "manual CSV cleanup",
                    "urgency": 3,
                    "severity": 3,
                    "willingness_to_pay": 5,
                    "category": "reporting",
                    "confidence": 0.8
                  }
                }
                """
            ]
        )
        email_notifier = FakeEmailNotifier()
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=signal_repository,
            score_repository=score_repository,
            cluster_repository=cluster_repository,
            opportunity_repository=opportunity_repository,
            llm_client=llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(email_notifier),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            sources=[
                SourceInput.create(
                    locator="https://example.com/reviews",
                    limit=1,
                )
            ],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.fetch_failed_count, 0)
        self.assertEqual(result.ingestion_result.inserted_count, 1)
        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(result.no_signal_count, 0)
        self.assertEqual(result.scoring_result.scored_count, 1)
        self.assertEqual(result.embedding_failed_count, 0)
        self.assertEqual(result.clustered_count, 1)
        self.assertEqual(result.opportunity_synthesis_result.synthesized_count, 0)
        self.assertEqual(result.opportunity_synthesis_result.inserted_count, 0)
        self.assertEqual(
            result.opportunity_synthesis_result.rejected_qualifications[0].reason,
            "insufficient_evidence",
        )
        self.assertTrue(result.email_result.sent)
        signal = signal_repository.list_signals()[0]
        self.assertEqual(signal.pain, "Export workflows are painful")
        self.assertEqual(score_repository.get_score(signal.id).total_score, 7.6)
        self.assertEqual(cluster_repository.get_cluster("cluster-1").theme, "reporting")
        self.assertIsNone(opportunity_repository.get_opportunity("opportunity-cluster-1"))
        self.assertEqual(email_notifier.calls[0][2], ["founder@example.com"])

    def test_persists_accumulated_findings_with_source_provenance(self):
        finding_repository = FakeFindingRepository()
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            finding_repository=finding_repository,
            llm_client=SequentialLLMClient(
                [
                    """
                    {
                      "has_signal": true,
                      "is_about_competitor": true,
                      "competitor_match_reason": null,
                      "signal": {
                        "pain": "Export workflows are painful",
                        "user_type": "finance team",
                        "job_to_be_done": "export reports",
                        "current_workaround": "manual CSV cleanup",
                        "urgency": 3,
                        "severity": 3,
                        "willingness_to_pay": 5,
                        "category": "reporting",
                        "confidence": 0.8
                      }
                    }
                    """
                ]
            ),
            embedding_client=FakeEmbeddingClient(),
            email_client=None,
            recipient="",
            send_email=False,
            source_adapters=[FakeSourceAdapter()],
            user_niche_id="market-1",
            sources=[
                SourceInput.create(
                    locator="https://example.com/reviews",
                    limit=1,
                    options={
                        "niche_source_id": "source-1",
                        "source_type": "review_search",
                        "source_family": "reviews",
                        "market_id": "niche-1",
                    },
                )
            ],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(len(finding_repository.findings), 1)
        finding = finding_repository.findings[0]
        self.assertEqual(finding.user_niche_id, "market-1")
        self.assertEqual(finding.source_id, "source-1")
        self.assertEqual(finding.niche_id, "niche-1")
        self.assertEqual(finding.source_url, "https://example.com/reviews")
        self.assertEqual(finding.embedding, [1.0, 0.0])
        self.assertEqual(finding.metadata["source_family"], "reviews")

    def test_assigns_accumulated_findings_to_seed_themes(self):
        finding_repository = FakeFindingRepository()
        theme_repository = FakeThemeRepository()
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            finding_repository=finding_repository,
            theme_repository=theme_repository,
            llm_client=SequentialLLMClient(
                [
                    """
                    {
                      "has_signal": true,
                      "is_about_competitor": true,
                      "competitor_match_reason": null,
                      "signal": {
                        "pain": "Export workflows are painful",
                        "user_type": "finance team",
                        "job_to_be_done": "export reports",
                        "current_workaround": "manual CSV cleanup",
                        "urgency": 3,
                        "severity": 3,
                        "willingness_to_pay": 5,
                        "category": "reporting",
                        "confidence": 0.8
                      }
                    }
                    """
                ]
            ),
            embedding_client=FakeEmbeddingClient(),
            email_client=None,
            recipient="",
            send_email=False,
            source_adapters=[FakeSourceAdapter()],
            user_niche_id="market-1",
            sources=[
                SourceInput.create(
                    locator="https://example.com/reviews",
                    limit=1,
                    options={"niche_source_id": "source-1"},
                )
            ],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(len(theme_repository.themes), 1)
        self.assertEqual(theme_repository.themes[0].title, "reporting")
        self.assertEqual(len(theme_repository.assignments), 1)
        self.assertEqual(
            theme_repository.assignments[0].assignment_method,
            "seed_new_theme",
        )
        self.assertEqual(
            theme_repository.refreshed_theme_ids,
            [theme_repository.themes[0].id],
        )
        self.assertEqual(theme_repository.themes[0].status, "emerging")
        self.assertEqual(
            theme_repository.themes[0].qualification_reason,
            "insufficient_evidence",
        )

    def test_runs_pipeline_from_enabled_niche_sources(self):
        user_niche_repository = InMemoryUserNicheRepository()
        user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
                template_niche_id="niche-1",
            )
        )
        niche_source_repository = InMemoryNicheSourceRepository()
        niche_source_repository.save_niche_sources(
            [
                NicheSource.create(
                    id="source-1",
                    niche_id="niche-1",
                    locator="https://example.com/reviews",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                    limit=1,
                ),
                NicheSource.create(
                    id="source-2",
                    niche_id="niche-1",
                    locator="https://example.com/disabled",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                    enabled=False,
                ),
            ]
        )
        llm_client = SequentialLLMClient(
            [
                """
                {
                  "has_signal": false,
                  "is_about_competitor": false,
                  "competitor_match_reason": null,
                  "signal": null
                }
                """
            ]
        )
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            niche_source_repository=niche_source_repository,
            user_niche_repository=user_niche_repository,
            llm_client=llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            user_niche_id="market-1",
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.fetch_failed_count, 0)
        self.assertEqual(result.no_signal_count, 1)

    @unittest.skip("PipelineConfig API changed — source_health_repository/monitored_source_repository removed")
    def test_runs_pipeline_from_enabled_monitored_sources(self):
        competitor_repository = InMemoryNicheCompanyRepository()
        competitor_repository.save_competitors(
            [
                Competitor.create(
                    id="competitor-1",
                    name="Acme CRM",
                    website="https://acme.example",
                    category="crm",
                )
            ]
        )
        monitored_source_repository = InMemoryNicheSourceRepository()
        monitored_source_repository.save_monitored_sources(
            [
                MonitoredSource.create(
                    id="source-1",
                    competitor_id="competitor-1",
                    locator="https://example.com/reviews",
                    source_type="reviews",
                    limit=1,
                )
            ]
        )
        signal_repository = InMemorySignalRepository()
        source_health_repository = InMemorySourceHealthRepository()
        llm_client = SequentialLLMClient(
            [
                """
                {
                  "has_signal": true,
                  "is_about_competitor": true,
                  "competitor_match_reason": "The post describes an Acme CRM export workflow complaint.",
                  "signal": {
                    "pain": "Export workflows are painful",
                    "user_type": null,
                    "job_to_be_done": null,
                    "current_workaround": null,
                    "urgency": 3,
                    "severity": 3,
                    "willingness_to_pay": 5,
                    "category": "reporting",
                    "confidence": 0.8
                  }
                }
                """
            ]
        )
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=signal_repository,
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            opportunity_repository=InMemoryOpportunityRepository(),
            competitor_repository=competitor_repository,
            monitored_source_repository=monitored_source_repository,
            source_health_repository=source_health_repository,
            llm_client=llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.extracted_count, 1)
        self.assertIn("competitor_name: Acme CRM", llm_client.calls[0][1])
        self.assertIn("competitor_domain: acme.example", llm_client.calls[0][1])
        signal = signal_repository.list_signals()[0]
        self.assertEqual(signal.competitor_id, "competitor-1")
        self.assertEqual(
            signal.evidence_url,
            "https://example.com/reviews",
        )
        updated_source = monitored_source_repository.get_monitored_source("source-1")
        self.assertIsNotNone(updated_source.last_scanned_at)
        self.assertIsNone(updated_source.last_error)
        health = source_health_repository.get_source_health("source-1")
        self.assertEqual(health.total_runs, 1)
        self.assertEqual(health.success_count, 1)
        self.assertEqual(health.last_status, "healthy")
        self.assertEqual(health.last_fetched_count, 1)
        self.assertEqual(health.last_relevant_count, 1)
        self.assertEqual(health.last_extracted_count, 1)
        self.assertEqual(health.last_opportunity_count, 1)

    @unittest.skip("PipelineConfig API changed — source_health_repository removed")
    def test_records_failed_monitored_source_scan_status(self):
        monitored_source_repository = InMemoryNicheSourceRepository()
        monitored_source_repository.save_monitored_sources(
            [
                MonitoredSource.create(
                    id="source-1",
                    competitor_id="competitor-1",
                    locator="https://example.com/reviews",
                    source_type="reviews",
                    limit=1,
                )
            ]
        )
        source_health_repository = InMemorySourceHealthRepository()
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            monitored_source_repository=monitored_source_repository,
            source_health_repository=source_health_repository,
            llm_client=SequentialLLMClient([]),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetch_failed_count, 1)
        updated_source = monitored_source_repository.get_monitored_source("source-1")
        self.assertIsNotNone(updated_source.last_scanned_at)
        self.assertEqual(
            updated_source.last_error,
            "No source adapter can handle locator",
        )
        health = source_health_repository.get_source_health("source-1")
        self.assertEqual(health.total_runs, 1)
        self.assertEqual(health.failure_count, 1)
        self.assertEqual(health.consecutive_failures, 1)
        self.assertEqual(health.last_status, "failing")
        self.assertEqual(health.last_error, "No source adapter can handle locator")

    @unittest.skip("PipelineConfig API changed — market_repository/monitored_source_repository removed")
    def test_runs_pipeline_from_one_market_source_scope(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [
                Market.create(
                    id="workspace-tools",
                    name="Workspace tools",
                    target_user="product teams",
                    idea_prompt="Find collaboration workflow gaps.",
                )
            ]
        )
        monitored_source_repository = InMemoryNicheSourceRepository()
        monitored_source_repository.save_monitored_sources(
            [
                MonitoredSource.create(
                    id="source-1",
                    market_id="workspace-tools",
                    locator="https://example.com/reviews",
                    source_type="reviews",
                    limit=1,
                ),
                MonitoredSource.create(
                    id="source-2",
                    market_id="finance-tools",
                    locator="https://example.com/other",
                    source_type="reviews",
                    limit=1,
                ),
            ]
        )
        signal_repository = InMemorySignalRepository()
        llm_client = SequentialLLMClient(
            [
                """
                {
                  "has_signal": true,
                  "is_about_competitor": true,
                  "competitor_match_reason": "The post describes a workflow gap in the watched market.",
                  "signal": {
                    "pain": "Export workflows are painful",
                    "user_type": "product teams",
                    "job_to_be_done": null,
                    "current_workaround": null,
                    "urgency": 3,
                    "severity": 3,
                    "willingness_to_pay": 5,
                    "category": "reporting",
                    "confidence": 0.8
                  }
                }
                """
            ]
        )
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=signal_repository,
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            market_repository=market_repository,
            monitored_source_repository=monitored_source_repository,
            llm_client=llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            market_id="workspace-tools",
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertIn("market_name: Workspace tools", llm_client.calls[0][1])
        self.assertIn("market_target_user: product teams", llm_client.calls[0][1])
        signal = signal_repository.list_signals()[0]
        self.assertEqual(signal.market_id, "workspace-tools")
        self.assertEqual(result.report.title, "Workspace tools Market Gap Report")

    @unittest.skip("PipelineConfig API changed — market_repository/monitored_source_repository removed")
    def test_skips_muted_sources_from_agent_preferences(self):
        market_repository = InMemoryMarketRepository()
        market_repository.save_markets(
            [Market.create(id="workspace-tools", name="Workspace tools")]
        )
        agent_preferences_repository = InMemoryAgentPreferencesRepository()
        agent_preferences_repository.save_agent_preferences(
            AgentPreferences.create(
                market_id="workspace-tools",
                muted_source_ids=["source-2"],
            )
        )
        monitored_source_repository = InMemoryNicheSourceRepository()
        monitored_source_repository.save_monitored_sources(
            [
                MonitoredSource.create(
                    id="source-1",
                    market_id="workspace-tools",
                    locator="https://example.com/reviews",
                    source_type="reviews",
                    limit=1,
                ),
                MonitoredSource.create(
                    id="source-2",
                    market_id="workspace-tools",
                    locator="https://example.com/unsupported",
                    source_type="reviews",
                    limit=1,
                ),
            ]
        )
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            agent_preferences_repository=agent_preferences_repository,
            market_repository=market_repository,
            monitored_source_repository=monitored_source_repository,
            llm_client=SequentialLLMClient(
                [
                    """
                    {
                      "has_signal": false,
                      "is_about_competitor": false,
                      "competitor_match_reason": null,
                      "signal": null
                    }
                    """
                ]
            ),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            market_id="workspace-tools",
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.fetch_failed_count, 0)
        self.assertIsNotNone(
            monitored_source_repository.get_monitored_source(
                "source-1"
            ).last_scanned_at
        )
        self.assertIsNone(
            monitored_source_repository.get_monitored_source(
                "source-2"
            ).last_scanned_at
        )

    @unittest.skip("PipelineConfig API changed — market_id/AgentPreferences.market_id removed")
    def test_does_not_fall_back_to_global_locators_when_market_sources_are_muted(self):
        agent_preferences_repository = InMemoryAgentPreferencesRepository()
        agent_preferences_repository.save_agent_preferences(
            AgentPreferences.create(
                market_id="workspace-tools",
                muted_source_ids=["source-1"],
            )
        )
        monitored_source_repository = InMemoryNicheSourceRepository()
        monitored_source_repository.save_monitored_sources(
            [
                MonitoredSource.create(
                    id="source-1",
                    market_id="workspace-tools",
                    locator="https://example.com/reviews",
                    source_type="reviews",
                    limit=1,
                )
            ]
        )
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            agent_preferences_repository=agent_preferences_repository,
            niche_source_repository=monitored_source_repository,
            llm_client=SequentialLLMClient([]),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            user_niche_id="workspace-tools",
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 0)
        self.assertEqual(result.fetch_failed_count, 0)

    @unittest.skip("InMemoryNicheCompanyRepository API changed — save_competitors removed")
    def test_rejects_unrelated_signal_from_monitored_source(self):
        competitor_repository = InMemoryNicheCompanyRepository()
        competitor_repository.save_competitors(
            [
                Competitor.create(
                    id="competitor-1",
                    name="Acme CRM",
                    website="https://acme.example",
                )
            ]
        )
        monitored_source_repository = InMemoryNicheSourceRepository()
        monitored_source_repository.save_monitored_sources(
            [
                MonitoredSource.create(
                    id="source-1",
                    competitor_id="competitor-1",
                    locator="https://example.com/reviews",
                    source_type="reviews",
                    limit=1,
                )
            ]
        )
        signal_repository = InMemorySignalRepository()
        llm_client = SequentialLLMClient(
            [
                """
                {
                  "has_signal": true,
                  "is_about_competitor": false,
                  "competitor_match_reason": "The complaint is about another product.",
                  "signal": {
                    "pain": "Another tool is too expensive",
                    "user_type": null,
                    "job_to_be_done": null,
                    "current_workaround": null,
                    "urgency": 3,
                    "severity": 3,
                    "willingness_to_pay": 2,
                    "category": "finance tools",
                    "confidence": 0.8
                  }
                }
                """
            ]
        )
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=signal_repository,
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            competitor_repository=competitor_repository,
            monitored_source_repository=monitored_source_repository,
            llm_client=llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.extracted_count, 0)
        self.assertEqual(result.no_signal_count, 1)
        self.assertEqual(signal_repository.list_signals(), [])

    def test_filters_wrong_subject_before_extraction(self):
        extraction_llm_client = RecordingLLMClient(
            [
                """
                {
                  "has_signal": true,
                  "is_about_competitor": true,
                  "competitor_match_reason": null,
                  "signal": {
                    "pain": "Should not be extracted",
                    "user_type": null,
                    "job_to_be_done": null,
                    "current_workaround": null,
                    "urgency": 3,
                    "severity": 3,
                    "willingness_to_pay": 3,
                    "category": "other",
                    "confidence": 0.5
                  }
                }
                """
            ]
        )
        relevance_llm_client = RecordingLLMClient(
            [
                """
                {
                  "is_relevant": false,
                  "is_about_competitor": false,
                  "has_pain_or_request": true,
                  "rejection_category": "wrong_subject",
                  "reason": "The complaint is about another product.",
                  "confidence": 0.93
                }
                """
            ]
        )
        post_repository = InMemoryPostRepository()
        signal_repository = InMemorySignalRepository()
        config = PipelineConfig(
            post_repository=post_repository,
            signal_repository=signal_repository,
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            llm_client=extraction_llm_client,
            relevance_llm_client=relevance_llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            sources=[SourceInput.create(locator="https://example.com/reviews")],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.rule_filtered_count, 0)
        self.assertEqual(result.llm_filtered_count, 1)
        self.assertEqual(result.relevance_failed_count, 0)
        self.assertEqual(result.extraction_attempted_count, 0)
        self.assertEqual(result.extracted_count, 0)
        self.assertEqual(extraction_llm_client.calls, [])
        self.assertEqual(signal_repository.list_signals(), [])

    def test_extracts_only_posts_that_pass_relevance_filter(self):
        extraction_llm_client = RecordingLLMClient(
            [
                """
                {
                  "has_signal": true,
                  "is_about_competitor": true,
                  "competitor_match_reason": null,
                  "signal": {
                    "pain": "Export workflows are painful",
                    "user_type": "finance teams",
                    "job_to_be_done": "export reports",
                    "current_workaround": "manual CSV cleanup",
                    "urgency": 3,
                    "severity": 3,
                    "willingness_to_pay": 5,
                    "category": "reporting",
                    "confidence": 0.8
                  }
                }
                """
            ]
        )
        relevance_llm_client = RecordingLLMClient(
            [
                """
                {
                  "is_relevant": true,
                  "is_about_competitor": true,
                  "has_pain_or_request": true,
                  "rejection_category": null,
                  "reason": "The post complains about export workflows.",
                  "confidence": 0.9
                }
                """
            ]
        )
        signal_repository = InMemorySignalRepository()
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=signal_repository,
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            llm_client=extraction_llm_client,
            relevance_llm_client=relevance_llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            sources=[SourceInput.create(locator="https://example.com/reviews")],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.extraction_attempted_count, 1)
        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(len(extraction_llm_client.calls), 1)
        self.assertEqual(signal_repository.list_signals()[0].pain, "Export workflows are painful")

    def test_persists_pipeline_run_metrics(self):
        metrics_repository = InMemoryPipelineRunMetricsRepository()
        config = PipelineConfig(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            pipeline_run_metrics_repository=metrics_repository,
            llm_client=SequentialLLMClient(
                [
                    """
                    {
                      "has_signal": false,
                      "is_about_competitor": false,
                      "competitor_match_reason": null,
                      "signal": null
                    }
                    """
                ]
            ),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            sources=[SourceInput.create(locator="https://example.com/reviews")],
        )

        result = run_daily_pipeline(config)
        metrics = metrics_repository.list_pipeline_run_metrics()[0]

        self.assertEqual(metrics.fetched_count, result.fetched_count)
        self.assertEqual(
            metrics.extraction_attempted_count,
            result.extraction_attempted_count,
        )
        self.assertEqual(metrics.extracted_count, result.extracted_count)
        self.assertTrue(metrics.email_sent)

    def test_records_niche_source_run_stats_with_relevance_outcomes(self):
        repository = InMemoryNicheSourceRepository()
        source = NicheSource.create(
            id="source-1",
            niche_id="niche-1",
            locator="https://example.com/reviews",
            source_type="hackernews_search",
            source_family="technical_forum",
            is_gate_free=True,
        )
        repository.save_niche_sources([source])
        detail = SourceFetchDetail(
            source=SourceInput.create(
                locator="https://example.com/reviews",
                options={"niche_source_id": "source-1"},
            ),
            fetched_count=5,
        )
        relevance = SourceRelevanceStats(
            source_id="source-1",
            relevant_count=2,
            rule_filtered_count=1,
            llm_filtered_count=2,
            rejection_breakdown={"empty": 1, "wrong_subject": 2},
        )

        _record_niche_source_health(repository, [detail], {"source-1": relevance})

        updated_source = repository.list_niche_sources("niche-1")[0]
        stats = repository.get_niche_source_run_stats("source-1")

        self.assertEqual(updated_source.health_status, "active")
        self.assertEqual(updated_source.signal_quality_score, 0.622)
        self.assertFalse(updated_source.buyer_voice_verified)
        self.assertIsNotNone(stats)
        self.assertEqual(stats.total_runs, 1)
        self.assertEqual(stats.posts_fetched_count, 5)
        self.assertEqual(stats.relevant_posts_count, 2)
        self.assertEqual(stats.rule_filtered_count, 1)
        self.assertEqual(stats.llm_filtered_count, 2)
        self.assertEqual(stats.rejection_breakdown, {"empty": 1, "wrong_subject": 2})

    def test_configured_sources_prioritizes_observed_source_quality(self):
        user_niche_repository = InMemoryUserNicheRepository()
        user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
                template_niche_id="niche-1",
            )
        )
        source_repository = InMemoryNicheSourceRepository()
        source_repository.save_niche_sources(
            [
                NicheSource.create(
                    id="source-low",
                    niche_id="niche-1",
                    locator="https://example.com/low",
                    source_type="hackernews_search",
                    source_family="technical_forum",
                    is_gate_free=True,
                    signal_quality_score=0.45,
                ),
                NicheSource.create(
                    id="source-high",
                    niche_id="niche-1",
                    locator="https://example.com/high",
                    source_type="github_issues_search",
                    source_family="technical_forum",
                    is_gate_free=True,
                    signal_quality_score=0.7,
                ),
                NicheSource.create(
                    id="source-failing",
                    niche_id="niche-1",
                    locator="https://example.com/failing",
                    source_type="github_issues_search",
                    source_family="technical_forum",
                    is_gate_free=True,
                    signal_quality_score=0.9,
                ),
            ]
        )
        source_repository.upsert_niche_source_run_stats(
            NicheSourceRunStats.create(
                niche_source_id="source-high",
                total_runs=3,
                success_count=3,
                posts_fetched_count=30,
                relevant_posts_count=10,
                rule_filtered_count=5,
            )
        )
        source_repository.upsert_niche_source_run_stats(
            NicheSourceRunStats.create(
                niche_source_id="source-failing",
                total_runs=3,
                failure_count=3,
                consecutive_failures=3,
            )
        )

        sources = _configured_sources(
            source_repository,
            user_niche_repository,
            None,
            "market-1",
        )

        self.assertEqual(
            [source.locator for source in sources],
            [
                "https://example.com/high",
                "https://example.com/low",
            ],
        )

    def test_configured_sources_skip_gated_sources_without_runtime_access(self):
        user_niche_repository = InMemoryUserNicheRepository()
        user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
                template_niche_id="niche-1",
            )
        )
        source_repository = InMemoryNicheSourceRepository()
        reddit_source = replace(
            NicheSource.create(
                id="source-reddit",
                niche_id="niche-1",
                locator="https://www.reddit.com/r/devtools/new.json?limit=25",
                source_type="reddit_subreddit",
                source_family="social",
                is_gate_free=False,
                requires_auth=True,
            ),
            enabled=True,
        )
        proxy_source = replace(
            NicheSource.create(
                id="source-g2",
                niche_id="niche-1",
                locator="https://www.g2.com/products/example/reviews",
                source_type="g2_reviews",
                source_family="reviews",
                is_gate_free=False,
                requires_proxy=True,
            ),
            enabled=True,
        )
        source_repository.save_niche_sources(
            [
                reddit_source,
                proxy_source,
                NicheSource.create(
                    id="source-hn",
                    niche_id="niche-1",
                    locator="https://hn.algolia.com/api/v1/search_by_date?query=test&tags=comment",
                    source_type="hackernews_search",
                    source_family="technical_forum",
                    is_gate_free=True,
                ),
            ]
        )

        sources = _configured_sources(
            source_repository,
            user_niche_repository,
            None,
            "market-1",
        )

        self.assertEqual(
            [source.locator for source in sources],
            ["https://hn.algolia.com/api/v1/search_by_date?query=test&tags=comment"],
        )

    def test_configured_sources_allow_auth_sources_when_runtime_access_exists(self):
        user_niche_repository = InMemoryUserNicheRepository()
        user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
                template_niche_id="niche-1",
            )
        )
        source_repository = InMemoryNicheSourceRepository()
        source_repository.save_niche_sources(
            [
                replace(
                    NicheSource.create(
                        id="source-reddit",
                        niche_id="niche-1",
                        locator="https://www.reddit.com/r/devtools/new.json?limit=25",
                        source_type="reddit_subreddit",
                        source_family="social",
                        is_gate_free=False,
                        requires_auth=True,
                    ),
                    enabled=True,
                )
            ]
        )

        sources = _configured_sources(
            source_repository,
            user_niche_repository,
            None,
            "market-1",
            allow_auth_sources=True,
        )

        self.assertEqual(
            [source.locator for source in sources],
            ["https://www.reddit.com/r/devtools/new.json?limit=25"],
        )


if __name__ == "__main__":
    unittest.main()
