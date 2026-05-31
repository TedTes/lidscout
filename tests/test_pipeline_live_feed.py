import asyncio
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any

from api.routes.signals import SignalApiDependencies, get_market_pipeline_live_feed
from domain.agent import AgentActivity
from domain.niche import UserNiche
from domain.post import RawPost
from domain.user import User
from infrastructure.db import InMemoryAgentActivityRepository
from infrastructure.llm import LLMClient
from workers.run_daily_pipeline import _filter_relevant_posts


class FailingRelevanceLLM(LLMClient):
    def generate_structured_response(
        self,
        prompt: str,
        post_content: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        raise RuntimeError("classifier unavailable")


class PipelineLiveFeedTests(unittest.TestCase):
    def test_live_feed_clears_current_item_after_decision(self) -> None:
        dependencies = SignalApiDependencies()
        current_user = User(id="user-1", email="user@example.com")
        dependencies.user_niche_repository.save_user_niche(
            UserNiche.create(
                id="market-1",
                user_id="user-1",
                job="Build internal tools",
                buyer="Developer teams",
                category="devtools",
            )
        )
        started_at = datetime(2026, 5, 31, tzinfo=UTC)
        dependencies.agent_activity_repository.save_agent_activity(
            AgentActivity.create(
                user_niche_id="market-1",
                event_type="run_started",
                title="Started",
                created_at=started_at,
            )
        )
        dependencies.agent_activity_repository.save_agent_activity(
            AgentActivity.create(
                user_niche_id="market-1",
                event_type="post_evaluating",
                title="Evaluating post",
                metadata={"title": "Post A"},
                created_at=started_at + timedelta(seconds=1),
            )
        )
        dependencies.agent_activity_repository.save_agent_activity(
            AgentActivity.create(
                user_niche_id="market-1",
                event_type="post_filtered",
                title="Filtered post",
                metadata={"title": "Post A", "reason": "wrong_subject"},
                created_at=started_at + timedelta(seconds=2),
            )
        )

        response = asyncio.run(
            get_market_pipeline_live_feed(
                "market-1",
                dependencies=dependencies,
                current_user=current_user,
            )
        )

        self.assertIsNone(response["current_item"])
        self.assertEqual(response["recent_decisions"][0]["event_type"], "post_filtered")

    def test_relevance_errors_record_terminal_filtered_decision(self) -> None:
        activity_repository = InMemoryAgentActivityRepository()
        post = RawPost.create(
            source="web",
            source_id="post-1",
            title="Supabase export is painful",
            body="Supabase export keeps failing and this painful workflow is blocking us.",
            metadata={
                "competitor_name": "Supabase",
                "source_type": "github_issues_search",
            },
        )

        result = _filter_relevant_posts(
            [post],
            FailingRelevanceLLM(),
            activity_repository=activity_repository,
            user_niche_id="market-1",
        )

        activity = activity_repository.list_agent_activity(user_niche_id="market-1")

        self.assertEqual(result.failed_count, 1)
        self.assertEqual(activity[0].event_type, "post_filtered")
        self.assertEqual(activity[0].metadata["reason"], "other")
        self.assertEqual(activity[1].event_type, "post_evaluating")


if __name__ == "__main__":
    unittest.main()
