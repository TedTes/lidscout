import asyncio
import unittest

from api.main import app
from api.routes.signals import (
    PipelineRunRequest,
    SignalApiDependencies,
    get_latest_report,
    list_clusters,
    list_signals,
    run_pipeline,
)
from domain.cluster import SignalCluster
from domain.post import RawPost
from domain.signal import Signal
from domain.source import SourceInput
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
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
    def generate_structured_response(self, prompt: str, post_content: str) -> str:
        return """
        {
          "has_signal": true,
          "signal": {
            "id": "signal-1",
            "pain": "Manual reporting is slow",
            "urgency": "high",
            "severity": "medium",
            "willingness_to_pay": true,
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
        self.assertEqual(signal_repository.get_signal("signal-1").pain, "Manual reporting is slow")
        self.assertEqual(cluster_repository.get_cluster("cluster-1").theme, "reporting")

    def _dependencies(
        self,
        *,
        post_repository=None,
        signal_repository=None,
        score_repository=None,
        cluster_repository=None,
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
