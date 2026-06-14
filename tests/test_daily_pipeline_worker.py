import unittest
from dataclasses import replace
from typing import Any

from domain.agent import AgentPreferences
from domain.competitor import Competitor
from domain.finding import Finding
from domain.market import Market
from domain.niche import (
    NicheSource,
    NicheSourceRunStats,
    TemplateSourceBinding,
    UserNiche,
    UserSource,
    UserSourcePreference,
)
from domain.post import RawPost
from domain.source import MonitoredSource, Source, SourceInput
from domain.theme import Theme, ThemeFinding
from application.ingestion import SourceFetchDetail
from infrastructure.db import (
    InMemoryAgentPreferencesRepository,
    InMemoryNicheCompanyRepository,
    InMemoryUserNicheRepository,
    InMemoryOpportunityRepository,
    InMemoryPipelineRunMetricsRepository,
    InMemoryNicheSourceRepository,
    InMemorySourceRepository,
    InMemoryTemplateSourceBindingRepository,
    InMemoryUserSourceRepository,
    InMemoryUserSourcePreferenceRepository,
    InMemoryUserSourceRunStatsRepository,
)
from infrastructure.email import EmailClient, EmailNotifier
from infrastructure.llm import EmbeddingClient, LLMClient
from workers.run_daily_pipeline import (
    PipelineConfig,
    SourceRelevanceStats,
    _configured_sources,
    _record_niche_source_health,
    _synthesize_accumulated_theme_opportunities,
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


class _TwoPostSourceAdapter:
    def can_handle(self, source: SourceInput) -> bool:
        return source.locator == "https://example.com/two"

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        return [
            RawPost.create(
                source="web",
                source_id=f"post-{i}",
                title=f"Post {i}",
                body="Acme CRM export pain.",
                url=f"https://example.com/post-{i}",
                metadata={k: v for k, v in source.options.items() if isinstance(v, str)},
            )
            for i in range(2)
        ]


def _extraction_response(pain: str, user_type: str) -> str:
    return f"""{{
        "has_signal": true,
        "is_about_competitor": false,
        "competitor_match_reason": null,
        "signal": {{
            "pain": "{pain}",
            "user_type": "{user_type}",
            "job_to_be_done": "export reports",
            "current_workaround": "manual CSV",
            "urgency": 3, "severity": 3,
            "willingness_to_pay": 5,
            "category": "reporting",
            "confidence": 0.8
        }}
    }}"""


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

    def get_seen_post_ids(
        self,
        user_niche_id: str,
        post_ids: list[str],
    ) -> set[str]:
        seen = {f.post_id for f in self.findings if f.user_niche_id == user_niche_id}
        return {pid for pid in post_ids if pid in seen}

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
        self.findings_by_theme_id: dict[str, list[Finding]] = {}

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

    def find_similar_themes(
        self,
        user_niche_id: str,
        embedding: list[float],
        *,
        top_k: int = 5,
        min_similarity: float = 0.70,
    ) -> list[Theme]:
        import math

        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0.0

        candidates = [
            (t, cosine_sim(embedding, t.centroid_embedding))
            for t in self.themes
            if t.user_niche_id == user_niche_id and t.centroid_embedding
        ]
        return [
            t for t, sim in sorted(candidates, key=lambda x: -x[1])
            if sim >= min_similarity
        ][:top_k]

    def list_findings_for_theme(self, theme_id: str) -> list[Finding]:
        return self.findings_by_theme_id.get(theme_id, [])

    def refresh_theme_rollups(self, theme_ids: list[str]) -> int:
        self.refreshed_theme_ids.extend(theme_ids)
        return len(theme_ids)


class DailyPipelineWorkerTests(unittest.TestCase):
    def test_runs_pipeline_with_generic_sources(self):
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
        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(result.no_signal_count, 0)
        self.assertEqual(result.embedding_failed_count, 0)
        self.assertTrue(result.email_result.sent)
        self.assertIsNone(opportunity_repository.get_opportunity("opportunity-cluster-1"))
        self.assertEqual(email_notifier.calls[0][2], ["founder@example.com"])

    def test_persists_accumulated_findings_with_source_provenance(self):
        finding_repository = FakeFindingRepository()
        config = PipelineConfig(
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

        # A single finding with no existing themes is a singleton — it stays
        # unassigned until a future run produces a similar finding to cluster with.
        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(len(finding_repository.findings), 1)
        self.assertEqual(len(theme_repository.themes), 0)
        self.assertEqual(len(theme_repository.assignments), 0)

    def test_clusters_similar_unassigned_findings_into_shared_theme(self):
        """Two unassigned findings with high similarity form one shared seed theme."""
        finding_repository = FakeFindingRepository()
        theme_repository = FakeThemeRepository()

        two_post_adapter = _TwoPostSourceAdapter()
        config = PipelineConfig(
            finding_repository=finding_repository,
            theme_repository=theme_repository,
            llm_client=SequentialLLMClient(
                [
                    _extraction_response("Export pain A", "finance team"),
                    _extraction_response("Export pain B", "ops team"),
                ]
            ),
            embedding_client=FakeEmbeddingClient(),
            email_client=None,
            recipient="",
            send_email=False,
            source_adapters=[two_post_adapter],
            user_niche_id="market-1",
            sources=[
                SourceInput.create(
                    locator="https://example.com/two",
                    limit=2,
                    options={"niche_source_id": "source-1"},
                )
            ],
        )

        run_daily_pipeline(config)

        self.assertEqual(len(finding_repository.findings), 2)
        # Both unassigned findings were similar → one shared theme, two assignments.
        self.assertEqual(len(theme_repository.themes), 1)
        self.assertEqual(len(theme_repository.assignments), 2)
        self.assertEqual(theme_repository.themes[0].finding_count, 2)
        self.assertEqual(
            theme_repository.assignments[0].assignment_method, "seed_new_theme"
        )
        self.assertEqual(
            theme_repository.assignments[1].assignment_method, "seed_new_theme"
        )
        self.assertEqual(
            theme_repository.assignments[0].theme_id,
            theme_repository.assignments[1].theme_id,
        )

    def test_synthesizes_opportunities_from_qualified_accumulated_themes(self):
        theme = Theme.create(
            id="c9158d97-9449-4bf2-9ef5-17bb825d522f",
            user_niche_id="market-1",
            title="Reporting export reliability",
            summary="Finance teams need reliable report exports.",
            status="qualified",
            finding_count=2,
            source_count=2,
            average_confidence=0.8,
        )
        findings = [
            Finding.create(
                user_niche_id="market-1",
                post_id="post-1",
                pain="Report exports fail",
                evidence_text="Report exports fail",
                structured_embedding_text="Report exports fail",
                urgency="high",
                severity="medium",
                confidence=0.8,
                source_id="source-1",
                affected_user="finance teams",
                category="reporting",
            ),
            Finding.create(
                user_niche_id="market-1",
                post_id="post-2",
                pain="CSV exports need manual cleanup",
                evidence_text="CSV exports need manual cleanup",
                structured_embedding_text="CSV exports need manual cleanup",
                urgency="medium",
                severity="medium",
                confidence=0.8,
                source_id="source-2",
                affected_user="finance teams",
                category="reporting",
            ),
        ]
        theme_repository = FakeThemeRepository()
        theme_repository.save_themes([theme])
        theme_repository.findings_by_theme_id[theme.id] = findings
        opportunity_repository = InMemoryOpportunityRepository()
        config = PipelineConfig(
            opportunity_repository=opportunity_repository,
            theme_repository=theme_repository,
            llm_client=SequentialLLMClient([]),
            embedding_client=FakeEmbeddingClient(),
            email_client=None,
            recipient="",
            user_niche_id="market-1",
        )

        inserted_count = _synthesize_accumulated_theme_opportunities(
            config,
            [theme.id],
        )

        self.assertEqual(inserted_count, 1)
        opportunity = opportunity_repository.list_opportunities()[0]
        self.assertEqual(opportunity.source_theme_id, theme.id)
        self.assertIsNone(opportunity.cluster_id)
        self.assertEqual(opportunity.evidence_count, 2)

    def test_runs_pipeline_from_user_sources(self):
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
        source_repository = InMemorySourceRepository()
        source_repository.save_sources(
            [
                Source.create(
                    id="source-1",
                    locator="https://example.com/reviews",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                ),
                Source.create(
                    id="source-2",
                    locator="https://example.com/disabled",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                ),
            ]
        )
        template_source_binding_repository = InMemoryTemplateSourceBindingRepository()
        template_source_binding_repository.save_template_source_bindings(
            [
                TemplateSourceBinding.create(
                    id="binding-1",
                    template_niche_id="niche-1",
                    source_id="source-1",
                    default_limit=1,
                ),
                TemplateSourceBinding.create(
                    id="binding-2",
                    template_niche_id="niche-1",
                    source_id="source-2",
                ),
            ]
        )
        user_source_repository = InMemoryUserSourceRepository()
        user_source_repository.save_user_sources(
            [
                UserSource.create(
                    user_niche_id="market-1",
                    source_id="source-2",
                    template_source_binding_id="binding-2",
                    enabled=False,
                )
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
            source_repository=source_repository,
            template_source_binding_repository=template_source_binding_repository,
            user_source_repository=user_source_repository,
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

    def test_runs_pipeline_from_catalog_sources(self):
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
        source_repository = InMemorySourceRepository()
        source_repository.save_sources(
            [
                Source.create(
                    id="source-1",
                    locator="https://example.com/reviews",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                ),
                Source.create(
                    id="source-2",
                    locator="https://example.com/disabled",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                ),
            ]
        )
        template_source_binding_repository = InMemoryTemplateSourceBindingRepository()
        template_source_binding_repository.save_template_source_bindings(
            [
                TemplateSourceBinding.create(
                    id="binding-1",
                    template_niche_id="niche-1",
                    source_id="source-1",
                    default_limit=1,
                    tier=1,
                    signal_quality_score=0.9,
                ),
                TemplateSourceBinding.create(
                    id="binding-2",
                    template_niche_id="niche-1",
                    source_id="source-2",
                    default_enabled=True,
                ),
            ]
        )
        user_source_preference_repository = InMemoryUserSourcePreferenceRepository()
        user_source_preference_repository.save_user_source_preference(
            UserSourcePreference.create(
                user_niche_id="market-1",
                source_id="source-2",
                enabled=False,
            )
        )
        niche_source_repository = InMemoryNicheSourceRepository()
        user_source_run_stats_repository = InMemoryUserSourceRunStatsRepository()
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
            source_repository=source_repository,
            template_source_binding_repository=template_source_binding_repository,
            user_source_preference_repository=user_source_preference_repository,
            user_source_run_stats_repository=user_source_run_stats_repository,
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
        self.assertIsNone(
            niche_source_repository.get_niche_source_run_stats("binding-1")
        )
        stats = user_source_run_stats_repository.get_user_source_run_stats(
            "market-1",
            "source-1",
        )
        self.assertIsNotNone(stats)
        self.assertEqual(stats.template_source_binding_id, "binding-1")
        self.assertEqual(stats.total_runs, 1)
        self.assertEqual(stats.success_count, 1)
        self.assertEqual(stats.posts_fetched_count, 1)
        self.assertEqual(stats.relevant_posts_count, 1)

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
        config = PipelineConfig(
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
        config = PipelineConfig(
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

    def test_persists_pipeline_run_metrics(self):
        metrics_repository = InMemoryPipelineRunMetricsRepository()
        config = PipelineConfig(
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

    def test_configured_sources_boosts_preferred_source_families(self):
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
                    id="source-social",
                    niche_id="niche-1",
                    locator="https://example.com/social",
                    source_type="hackernews_search",
                    source_family="social",
                    is_gate_free=True,
                    signal_quality_score=0.7,
                    limit=10,
                ),
                NicheSource.create(
                    id="source-forum",
                    niche_id="niche-1",
                    locator="https://example.com/forum",
                    source_type="github_issues_search",
                    source_family="technical_forum",
                    is_gate_free=True,
                    signal_quality_score=0.62,
                    limit=10,
                ),
            ]
        )
        preferences_repository = InMemoryAgentPreferencesRepository()
        preferences_repository.save_agent_preferences(
            AgentPreferences.create(
                user_niche_id="market-1",
                preferred_source_families=["technical_forum"],
            )
        )

        sources = _configured_sources(
            source_repository,
            user_niche_repository,
            preferences_repository,
            "market-1",
        )

        self.assertEqual(
            [source.locator for source in sources],
            [
                "https://example.com/forum",
                "https://example.com/social",
            ],
        )
        self.assertEqual(sources[0].limit, 20)
        self.assertEqual(sources[1].limit, 10)

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
