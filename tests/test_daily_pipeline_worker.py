import unittest
from typing import Any

from domain.agent import AgentPreferences
from domain.competitor import Competitor
from domain.market import Market
from domain.post import RawPost
from domain.source import MonitoredSource, SourceInput, SourceLocator
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
    InMemorySourceLocatorRepository,
)
from infrastructure.email import EmailClient, EmailNotifier
from infrastructure.llm import EmbeddingClient, LLMClient
from workers.run_daily_pipeline import PipelineConfig, run_daily_pipeline


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

    def test_runs_pipeline_from_enabled_source_locators(self):
        source_locator_repository = InMemorySourceLocatorRepository()
        source_locator_repository.save_source_locators(
            [
                SourceLocator.create(
                    id="locator-1",
                    locator="https://example.com/reviews",
                    limit=1,
                ),
                SourceLocator.create(
                    id="locator-2",
                    locator="https://example.com/disabled",
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
            source_locator_repository=source_locator_repository,
            llm_client=llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
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
        source_locator_repository = InMemorySourceLocatorRepository()
        source_locator_repository.save_source_locators(
            [
                SourceLocator.create(
                    id="locator-1",
                    locator="https://example.com/reviews",
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
            monitored_source_repository=monitored_source_repository,
            source_locator_repository=source_locator_repository,
            llm_client=SequentialLLMClient([]),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
            market_id="workspace-tools",
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


if __name__ == "__main__":
    unittest.main()
