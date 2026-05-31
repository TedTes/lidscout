import unittest
from typing import Any

from api.routes.signals import SignalApiDependencies
from domain.post import RawPost
from domain.source import MonitoredSource, SourceInput, SourceLocator
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryNicheSourceRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemorySourceLocatorRepository,
)
from infrastructure.email import EmailClient, EmailNotifier
from infrastructure.llm import EmbeddingClient, LLMClient
from workers.jobs import check_worker_readiness, run_configured_daily_pipeline


class FakeSourceAdapter:
    def can_handle(self, source: SourceInput) -> bool:
        return source.locator == "https://example.com/reviews"

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        return [
            RawPost.create(
                source="web",
                source_id=source.locator,
                title="Review page",
                body="Manual exports are painful.",
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
            "pain": "Manual exports are painful",
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


class FakeEmbeddingClient(EmbeddingClient):
    def _generate_embedding(self, signal_text: str) -> list[float]:
        return [1.0, 0.0]


class FakeEmailNotifier(EmailNotifier):
    def send_report(self, subject: str, body: str, recipients: list[str]) -> None:
        return None


class BackgroundJobTests(unittest.TestCase):
    @unittest.skip("check_worker_readiness API migrated to user_niche_repository/niche_source_repository — needs rewrite")
    def test_checks_worker_readiness_from_monitored_sources(self):
        monitored_source_repository = InMemoryNicheSourceRepository()
        monitored_source_repository.save_monitored_sources(
            [
                MonitoredSource.create(
                    locator="https://example.com/reviews",
                    market_id="workspace-tools",
                )
            ]
        )
        dependencies = SignalApiDependencies(
            monitored_source_repository=monitored_source_repository,
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            relevance_llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )

        result = check_worker_readiness(
            market_id="workspace-tools",
            dependencies=dependencies,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["enabled_monitored_source_count"], 1)
        self.assertEqual(result["enabled_source_locator_count"], 0)
        self.assertEqual(result["source_adapter_count"], 1)

    def test_runs_configured_daily_pipeline_from_source_locators(self):
        source_locator_repository = InMemorySourceLocatorRepository()
        source_locator_repository.save_source_locators(
            [
                SourceLocator.create(
                    id="locator-1",
                    locator="https://example.com/reviews",
                )
            ]
        )
        dependencies = SignalApiDependencies(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            source_locator_repository=source_locator_repository,
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )

        result = run_configured_daily_pipeline(
            recipient="founder@example.com",
            dependencies=dependencies,
        )

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(result.clustered_count, 1)
        self.assertTrue(result.email_result.sent)


if __name__ == "__main__":
    unittest.main()
