import asyncio
import unittest
from typing import Any

from api.main import app, health_check
from api.routes.signals import (
    CompetitorRequest,
    MonitoredSourceRequest,
    PipelineRunRequest,
    SignalApiDependencies,
    create_competitor,
    create_competitor_source,
    get_latest_report,
    list_competitor_sources,
    list_competitors,
    list_clusters,
    list_signals,
    run_pipeline,
)
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.post import RawPost
from domain.signal import Signal
from domain.source import SourceInput, SourceLocator
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryCompetitorRepository,
    InMemoryMonitoredSourceRepository,
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
        self.assertIn("/clusters", paths)
        self.assertIn("/reports/latest", paths)
        self.assertIn("/pipeline/run", paths)
        self.assertIn("/competitors", paths)
        self.assertIn("/competitors/{competitor_id}/sources", paths)
        self.assertIn("/health", paths)

    def test_health_check_response(self):
        response = asyncio.run(health_check())

        self.assertEqual(response["status"], "healthy")
        self.assertEqual(response["service"], "lidscout-api")

    def test_lists_signals(self):
        signal_repository = InMemorySignalRepository()
        signal_repository.save_signals(
            [
                Signal.create(
                    id="signal-1",
                    post_id="reddit:r1",
                    pain="Manual reporting is slow",
                    category="reporting",
                    confidence=0.8,
                )
            ]
        )
        dependencies = self._dependencies(signal_repository=signal_repository)

        response = asyncio.run(list_signals(dependencies))

        self.assertEqual(response["signals"][0]["id"], "signal-1")
        self.assertEqual(response["signals"][0]["pain"], "Manual reporting is slow")

    def test_lists_clusters(self):
        cluster_repository = InMemoryClusterRepository()
        cluster_repository.save_clusters([self._cluster()])
        dependencies = self._dependencies(cluster_repository=cluster_repository)

        response = asyncio.run(list_clusters(dependencies))

        self.assertEqual(response["clusters"][0]["id"], "cluster-1")
        self.assertEqual(response["clusters"][0]["theme"], "reporting")

    def test_gets_latest_report(self):
        cluster_repository = InMemoryClusterRepository()
        cluster_repository.save_clusters([self._cluster()])
        dependencies = self._dependencies(cluster_repository=cluster_repository)

        response = asyncio.run(get_latest_report(dependencies))

        self.assertEqual(response["title"], "LidScout Market Signal Report")
        self.assertEqual(response["top_clusters"][0]["id"], "cluster-1")
        self.assertEqual(response["recommended_opportunities"][0], "reporting: Teams need faster reports.")

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

    def test_runs_pipeline_with_sources(self):
        signal_repository = InMemorySignalRepository()
        cluster_repository = InMemoryClusterRepository()
        dependencies = self._dependencies(
            signal_repository=signal_repository,
            cluster_repository=cluster_repository,
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
        self.assertTrue(response["email"]["sent"])
        self.assertEqual(signal_repository.list_signals()[0].pain, "Manual reporting is slow")
        self.assertEqual(cluster_repository.get_cluster("cluster-1").theme, "reporting")

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
        competitor_repository=None,
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
            competitor_repository=competitor_repository or InMemoryCompetitorRepository(),
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


if __name__ == "__main__":
    unittest.main()
