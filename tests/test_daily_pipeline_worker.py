import unittest
from typing import Any

from domain.post import RawPost
from domain.source import MonitoredSource, SourceInput, SourceLocator
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemoryMonitoredSourceRepository,
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
                body="Export workflows are painful for finance teams.",
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
        llm_client = SequentialLLMClient(
            [
                """
                {
                  "has_signal": true,
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
        self.assertTrue(result.email_result.sent)
        signal = signal_repository.list_signals()[0]
        self.assertEqual(signal.pain, "Export workflows are painful")
        self.assertEqual(score_repository.get_score(signal.id).total_score, 7.6)
        self.assertEqual(cluster_repository.get_cluster("cluster-1").theme, "reporting")
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
                  "has_signal": false
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

    def test_runs_pipeline_from_enabled_monitored_sources(self):
        monitored_source_repository = InMemoryMonitoredSourceRepository()
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
            monitored_source_repository=monitored_source_repository,
            llm_client=llm_client,
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
            recipient="founder@example.com",
            source_adapters=[FakeSourceAdapter()],
        )

        result = run_daily_pipeline(config)

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.extracted_count, 1)
        signal = signal_repository.list_signals()[0]
        self.assertEqual(signal.competitor_id, "competitor-1")
        self.assertEqual(
            signal.evidence_url,
            "https://example.com/reviews",
        )


if __name__ == "__main__":
    unittest.main()
