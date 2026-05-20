import unittest

from domain.post import RawPost
from domain.source import SourceInput
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
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
            )
        ]


class SequentialLLMClient(LLMClient):
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def generate_structured_response(self, prompt: str, post_content: str) -> str:
        self.calls.append((prompt, post_content))
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
                    "id": "signal-1",
                    "pain": "Export workflows are painful",
                    "user_type": "finance team",
                    "job_to_be_done": "export reports",
                    "current_workaround": "manual CSV cleanup",
                    "urgency": "medium",
                    "severity": "medium",
                    "willingness_to_pay": true,
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
        self.assertEqual(signal_repository.get_signal("signal-1").pain, "Export workflows are painful")
        self.assertEqual(score_repository.get_score("signal-1").total_score, 7.6)
        self.assertEqual(cluster_repository.get_cluster("cluster-1").theme, "reporting")
        self.assertEqual(email_notifier.calls[0][2], ["founder@example.com"])


if __name__ == "__main__":
    unittest.main()
