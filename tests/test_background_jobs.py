import unittest
from typing import Any

from api.routes.signals import SignalApiDependencies
from domain.agent import AgentAction
from domain.niche import NicheSource, TemplateSourceBinding, UserNiche
from domain.post import RawPost
from domain.source import Source, SourceInput
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
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
    def test_worker_readiness_reports_missing_runtime_config(self):
        dependencies = SignalApiDependencies(
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            source_adapters=[],
            llm_client=None,
            embedding_client=None,
        )

        result = check_worker_readiness(dependencies=dependencies)

        self.assertFalse(result["ready"])
        self.assertEqual(result["enabled_niche_source_count"], 0)
        self.assertIn("llm_client", result["missing_dependencies"])
        self.assertIn("embedding_client", result["missing_dependencies"])
        self.assertIn("source_adapters", result["missing_dependencies"])
        self.assertIn("pipeline_schedule", result)
        self.assertIn("coordinator_lock_seconds", result)

    def test_worker_readiness_counts_catalog_sources(self):
        dependencies = SignalApiDependencies(
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
        )
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                template_niche_id="niche-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
            )
        )
        dependencies.source_repository.save_sources(
            [
                Source.create(
                    id="source-1",
                    locator="https://example.com/reviews",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                )
            ]
        )
        dependencies.template_source_binding_repository.save_template_source_bindings(
            [
                TemplateSourceBinding.create(
                    template_niche_id="niche-1",
                    source_id="source-1",
                )
            ]
        )

        result = check_worker_readiness(
            user_niche_id="market-1",
            dependencies=dependencies,
        )

        self.assertEqual(result["enabled_niche_source_count"], 1)

    def test_runs_configured_daily_pipeline_from_niche_sources(self):
        dependencies = SignalApiDependencies(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                template_niche_id="niche-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
            )
        )
        dependencies.niche_source_repository.save_niche_sources(
            [
                NicheSource.create(
                    id="source-1",
                    niche_id="niche-1",
                    locator="https://example.com/reviews",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                )
            ]
        )

        result = run_configured_daily_pipeline(
            recipient="founder@example.com",
            market_id="market-1",
            dependencies=dependencies,
        )

        self.assertEqual(result.fetched_count, 1)
        self.assertEqual(result.extracted_count, 1)
        self.assertEqual(result.clustered_count, 1)
        self.assertFalse(result.email_result.sent)
        self.assertIsNone(result.email_result.error)

    def test_pipeline_persists_planned_agent_actions(self):
        dependencies = SignalApiDependencies(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                template_niche_id="niche-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
            )
        )

        run_configured_daily_pipeline(
            recipient="founder@example.com",
            market_id="market-1",
            dependencies=dependencies,
        )

        actions = dependencies.agent_action_repository.list_agent_actions(
            user_niche_id="market-1",
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].action_type, "suggest_source")

    def test_pipeline_skips_completed_duplicate_planned_actions(self):
        dependencies = SignalApiDependencies(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                template_niche_id="niche-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
            )
        )
        dependencies.agent_action_repository.save_agent_action(
            AgentAction.create(
                id="completed-action",
                user_niche_id="market-1",
                action_type="suggest_source",
                status="completed",
                metadata={
                    "source_count": 0,
                    "niche_id": "niche-1",
                    "locator": (
                        "https://hn.algolia.com/api/v1/search_by_date"
                        "?query=Build+internal+tools&tags=comment&hitsPerPage=25"
                    ),
                },
            )
        )

        run_configured_daily_pipeline(
            recipient="founder@example.com",
            market_id="market-1",
            dependencies=dependencies,
        )

        actions = dependencies.agent_action_repository.list_agent_actions(
            user_niche_id="market-1",
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].id, "completed-action")

    def test_pipeline_executes_approved_pause_source_actions_before_fetch(self):
        dependencies = SignalApiDependencies(
            post_repository=InMemoryPostRepository(),
            signal_repository=InMemorySignalRepository(),
            score_repository=InMemoryScoreRepository(),
            cluster_repository=InMemoryClusterRepository(),
            source_adapters=[FakeSourceAdapter()],
            llm_client=FakeLLMClient(),
            embedding_client=FakeEmbeddingClient(),
            email_client=EmailClient(FakeEmailNotifier()),
        )
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                template_niche_id="niche-1",
                job="Build internal tools",
                buyer="Ops teams",
                category="devtools",
            )
        )
        dependencies.niche_source_repository.save_niche_sources(
            [
                NicheSource.create(
                    id="source-1",
                    niche_id="niche-1",
                    locator="https://example.com/reviews",
                    source_type="web",
                    source_family="forum",
                    is_gate_free=True,
                    health_status="failing",
                )
            ]
        )
        dependencies.agent_action_repository.save_agent_action(
            AgentAction.create(
                id="action-1",
                user_niche_id="market-1",
                action_type="pause_source",
                status="approved",
                metadata={"source_id": "source-1"},
            )
        )

        result = run_configured_daily_pipeline(
            recipient="founder@example.com",
            market_id="market-1",
            dependencies=dependencies,
        )

        sources = dependencies.niche_source_repository.list_niche_sources("niche-1")
        actions = dependencies.agent_action_repository.list_agent_actions(
            user_niche_id="market-1",
        )
        pause_action = next(action for action in actions if action.id == "action-1")
        self.assertEqual(result.fetched_count, 0)
        self.assertEqual(sources[0].health_status, "paused")
        self.assertEqual(pause_action.status, "completed")


if __name__ == "__main__":
    unittest.main()
