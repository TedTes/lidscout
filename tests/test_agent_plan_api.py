import asyncio
from datetime import UTC, datetime
from unittest.mock import patch

from api.routes.signals import (
    AgentFeedbackRequest,
    AgentFollowUpAnswerRequest,
    SignalApiDependencies,
    answer_market_agent_follow_up,
    approve_market_agent_action,
    create_opportunity_feedback,
    delete_opportunity_feedback,
    dismiss_market_agent_follow_up,
    dismiss_market_agent_action,
    execute_market_agent_actions,
    get_market_agent_plan,
    list_market_agent_actions,
    propose_market_agent_actions,
    trigger_market_pipeline,
)
from domain.agent import AgentAction, AgentFollowUp
from domain.cluster import SignalCluster
from domain.finding import Finding
from domain.niche import UserNiche, UserSource, UserSourceRunStats
from domain.opportunity import Opportunity
from domain.signal import Signal
from domain.source import Source
from domain.theme import Theme
from domain.user import User


def test_get_market_agent_plan_returns_proposed_actions() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    response = asyncio.run(
        get_market_agent_plan(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    assert response["actions"][0]["action_type"] == "answer_follow_up"
    assert response["actions"][0]["metadata"]["follow_up_id"] == "follow-up-1"


def test_propose_market_agent_actions_persists_without_duplicates() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )
    repeated_response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    stored_actions = dependencies.agent_action_repository.list_agent_actions(
        user_niche_id="market-1",
    )
    assert response["actions"][0]["action_type"] == "answer_follow_up"
    assert repeated_response["actions"] == []
    assert len(stored_actions) == 1
    assert stored_actions[0].metadata["follow_up_id"] == "follow-up-1"


def test_propose_market_agent_actions_skips_completed_duplicates() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    dependencies.agent_action_repository.save_agent_action(
        AgentAction.create(
            id="completed-action",
            user_niche_id="market-1",
            action_type="answer_follow_up",
            status="completed",
            metadata={
                "follow_up_id": "follow-up-1",
                "question": "Previous wording",
                "response": "Answered already.",
            },
        )
    )

    response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    stored_actions = dependencies.agent_action_repository.list_agent_actions(
        user_niche_id="market-1",
    )
    assert response["actions"] == []
    assert len(stored_actions) == 1


def test_approve_market_agent_action_updates_status() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    propose_response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )
    action_id = propose_response["actions"][0]["id"]

    response = asyncio.run(
        approve_market_agent_action(
            "market-1",
            action_id,
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    assert response["action"]["status"] == "approved"


def test_list_market_agent_actions_returns_stored_actions() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    response = asyncio.run(
        list_market_agent_actions(
            "market-1",
            status="proposed",
            action_type="answer_follow_up",
            limit=10,
            dependencies=dependencies,
            current_user=User(id="user-1", email="user@example.com"),
        )
    )

    assert len(response["actions"]) == 1
    assert response["actions"][0]["action_type"] == "answer_follow_up"


def test_dismiss_market_agent_action_updates_status() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    propose_response = asyncio.run(
        propose_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )
    action_id = propose_response["actions"][0]["id"]

    response = asyncio.run(
        dismiss_market_agent_action(
            "market-1",
            action_id,
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    assert response["action"]["status"] == "dismissed"


def test_execute_market_agent_actions_applies_approved_actions() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    dependencies.agent_action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="pause_source",
            status="approved",
            metadata={"source_id": "source-1"},
        )
    )

    response = asyncio.run(
        execute_market_agent_actions(
            "market-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    user_source = dependencies.user_source_repository.get_user_source(
        "market-1",
        "source-1",
    )
    actions = dependencies.agent_action_repository.list_agent_actions(
        user_niche_id="market-1",
    )
    assert response["executed_count"] == 1
    assert response["failed_count"] == 0
    assert user_source is not None
    assert user_source.muted is True
    assert user_source.enabled is False
    assert actions[0].status == "completed"


def test_trigger_market_pipeline_enqueues_owned_market() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    with (
        patch("api.routes.signals._enqueue_pipeline") as enqueue,
        patch("api.routes.signals._acquire_manual_scan_enqueue_lock", return_value=True),
    ):
        response = asyncio.run(
            trigger_market_pipeline(
                "market-1",
                dependencies,
                User(id="user-1", email="user@example.com"),
            )
        )

    assert response == {"status": "queued"}
    enqueue.assert_called_once_with("market-1")


def test_trigger_market_pipeline_skips_recent_scan() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    scanned_at = datetime.now(tz=UTC)
    dependencies.user_source_run_stats_repository.upsert_user_source_run_stats(
        UserSourceRunStats.create(
            user_niche_id="market-1",
            source_id="source-1",
            total_runs=1,
            success_count=1,
            last_status="healthy",
            last_scanned_at=scanned_at,
        )
    )

    with patch("api.routes.signals._enqueue_pipeline") as enqueue:
        response = asyncio.run(
            trigger_market_pipeline(
                "market-1",
                dependencies,
                User(id="user-1", email="user@example.com"),
            )
        )

    assert response["status"] == "recent"
    assert response["last_scanned_at"] == scanned_at.isoformat()
    assert response["cooldown_seconds"] > 0
    enqueue.assert_not_called()


def test_trigger_market_pipeline_skips_when_enqueue_lock_is_held() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    with (
        patch("api.routes.signals._enqueue_pipeline") as enqueue,
        patch("api.routes.signals._acquire_manual_scan_enqueue_lock", return_value=False),
    ):
        response = asyncio.run(
            trigger_market_pipeline(
                "market-1",
                dependencies,
                User(id="user-1", email="user@example.com"),
            )
        )

    assert response == {"status": "already_queued"}
    enqueue.assert_not_called()


def test_less_like_this_feedback_updates_agent_preferences() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    _seed_opportunity_context(dependencies)

    asyncio.run(
        create_opportunity_feedback(
            "opportunity-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="less_like_this",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert preferences is not None
    assert preferences.ignored_themes == ["reporting"]
    assert preferences.ignored_categories == ["time"]


def test_dismiss_feedback_updates_agent_preferences() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    _seed_opportunity_context(dependencies)

    asyncio.run(
        create_opportunity_feedback(
            "opportunity-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="dismiss",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert preferences is not None
    assert preferences.ignored_themes == ["reporting"]
    assert preferences.ignored_categories == ["time"]


def test_positive_feedback_learns_source_family_preferences() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    _seed_opportunity_context(dependencies)

    asyncio.run(
        create_opportunity_feedback(
            "opportunity-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="save",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert preferences is not None
    assert preferences.preferred_source_families == ["technical_forum"]


def test_theme_backed_feedback_updates_agent_preferences() -> None:
    dependencies = SignalApiDependencies()
    dependencies.theme_repository = FakeThemeRepository()
    _seed_market_with_follow_up(dependencies)
    dependencies.theme_repository.save_themes(
        [
            Theme.create(
                id="theme-1",
                user_niche_id="market-1",
                title="payment reconciliation",
                summary="Operators need less manual reconciliation.",
            )
        ]
    )
    dependencies.theme_repository.add_findings(
        "theme-1",
        [
            Finding.create(
                id="finding-1",
                user_niche_id="market-1",
                post_id="github:issue-1",
                pain="Manual reconciliation takes too long.",
                evidence_text="Manual reconciliation takes too long.",
                structured_embedding_text="Manual reconciliation takes too long.",
                urgency="medium",
                severity="medium",
                confidence=0.8,
                category="payments",
                metadata={"source_family": "technical_forum"},
            )
        ],
    )
    dependencies.opportunity_repository.save_opportunities(
        [
            Opportunity.create(
                id="opportunity-theme-1",
                cluster_id=None,
                source_theme_id="theme-1",
                title="Reduce reconciliation friction",
                target_user="finance teams",
                pain_summary="Manual reconciliation takes too long.",
                why_it_matters="This repeats across evidence.",
                suggested_wedge="Automate reconciliation review.",
                evidence_count=2,
                confidence=0.7,
                evidence_signal_ids=["finding-1"],
                unmet_need_type="effort",
            )
        ]
    )

    asyncio.run(
        create_opportunity_feedback(
            "opportunity-theme-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="dismiss",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert preferences is not None
    assert preferences.ignored_themes == ["payment reconciliation"]
    assert preferences.ignored_categories == ["effort"]

    asyncio.run(
        create_opportunity_feedback(
            "opportunity-theme-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="save",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert preferences is not None
    assert preferences.ignored_themes == []
    assert preferences.ignored_categories == []
    assert preferences.preferred_source_families == ["technical_forum"]


def test_more_like_this_feedback_removes_ignored_preferences() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    _seed_opportunity_context(dependencies)
    asyncio.run(
        create_opportunity_feedback(
            "opportunity-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="less_like_this",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    asyncio.run(
        create_opportunity_feedback(
            "opportunity-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="more_like_this",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert preferences is not None
    assert preferences.ignored_themes == []
    assert preferences.ignored_categories == []


def test_delete_feedback_removes_unsupported_learned_preferences() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    _seed_opportunity_context(dependencies)
    asyncio.run(
        create_opportunity_feedback(
            "opportunity-1",
            AgentFeedbackRequest(
                market_id="market-1",
                action="dismiss",
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    response = asyncio.run(
        delete_opportunity_feedback(
            "opportunity-1",
            "market-1",
            "dismiss",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert response == {"deleted": 1}
    assert preferences is not None
    assert preferences.ignored_themes == []
    assert preferences.ignored_categories == []


def test_delete_feedback_keeps_preferences_supported_by_other_feedback() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)
    _seed_opportunity_context(dependencies)
    dependencies.opportunity_repository.save_opportunities(
        [
            Opportunity.create(
                id="opportunity-2",
                cluster_id="cluster-1",
                title="Improve reports again",
                target_user="finance teams",
                pain_summary="Reports are still slow.",
                why_it_matters="It wastes weekly ops time.",
                suggested_wedge="Build a faster reporting assistant.",
                evidence_count=1,
                confidence=0.7,
                evidence_signal_ids=["signal-1"],
                unmet_need_type="time",
            )
        ]
    )
    for opportunity_id in ("opportunity-1", "opportunity-2"):
        asyncio.run(
            create_opportunity_feedback(
                opportunity_id,
                AgentFeedbackRequest(
                    market_id="market-1",
                    action="dismiss",
                ),
                dependencies,
                User(id="user-1", email="user@example.com"),
            )
        )

    response = asyncio.run(
        delete_opportunity_feedback(
            "opportunity-1",
            "market-1",
            "dismiss",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        "market-1",
    )
    assert response == {"deleted": 1}
    assert preferences is not None
    assert preferences.ignored_themes == ["reporting"]
    assert preferences.ignored_categories == ["time"]


def test_answer_market_agent_follow_up_updates_status() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    response = asyncio.run(
        answer_market_agent_follow_up(
            "market-1",
            "follow-up-1",
            AgentFollowUpAnswerRequest(
                response="Two independent source families support this.",
                metadata={"answered_by": "test"},
            ),
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    activity = dependencies.agent_activity_repository.list_agent_activity(
        user_niche_id="market-1",
    )
    assert response["status"] == "answered"
    assert response["response"] == "Two independent source families support this."
    assert response["metadata"]["answered_by"] == "test"
    assert activity[0].event_type == "follow_up_answered"


def test_dismiss_market_agent_follow_up_updates_status() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_with_follow_up(dependencies)

    response = asyncio.run(
        dismiss_market_agent_follow_up(
            "market-1",
            "follow-up-1",
            dependencies,
            User(id="user-1", email="user@example.com"),
        )
    )

    activity = dependencies.agent_activity_repository.list_agent_activity(
        user_niche_id="market-1",
    )
    assert response["status"] == "dismissed"
    assert activity[0].event_type == "follow_up_dismissed"


def _seed_market_with_follow_up(dependencies: SignalApiDependencies) -> None:
    user_niche = UserNiche.create(
        id="market-1",
        user_id="user-1",
        template_niche_id="niche-1",
        job="Build internal tools",
        buyer="Ops teams",
        category="devtools",
    )
    dependencies.user_niche_repository.save_user_niche(user_niche)
    dependencies.source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://example.com/feed",
                source_type="web",
                source_family="forum",
                is_gate_free=True,
            )
        ]
    )
    dependencies.user_source_repository.save_user_sources(
        [
            UserSource.create(
                user_niche_id="market-1",
                source_id="source-1",
            )
        ]
    )
    dependencies.agent_follow_up_repository.save_agent_follow_up(
        AgentFollowUp.create(
            id="follow-up-1",
            user_niche_id="market-1",
            question="Why is this credible?",
        )
    )


def _seed_opportunity_context(dependencies: SignalApiDependencies) -> None:
    dependencies.signal_repository.save_signals(
        [
            Signal.create(
                id="signal-1",
                post_id="github:issue-1",
                pain="Reports are slow.",
                user_type="finance teams",
                evidence_url="https://github.com/example/reports/issues/1",
            )
        ]
    )
    dependencies.cluster_repository.save_clusters(
        [
            SignalCluster.create(
                id="cluster-1",
                theme="reporting",
                summary="Teams need faster reports.",
                signal_ids=["signal-1"],
                frequency=1,
                average_score=8.0,
            )
        ]
    )
    dependencies.opportunity_repository.save_opportunities(
        [
            Opportunity.create(
                id="opportunity-1",
                cluster_id="cluster-1",
                title="Improve reports",
                target_user="finance teams",
                pain_summary="Reports are slow.",
                why_it_matters="It wastes weekly ops time.",
                suggested_wedge="Build a faster reporting assistant.",
                evidence_count=1,
                confidence=0.7,
                evidence_signal_ids=["signal-1"],
                unmet_need_type="time",
            )
        ]
    )


class FakeThemeRepository:
    def __init__(self) -> None:
        self.themes: list[Theme] = []
        self.findings_by_theme: dict[str, list[Finding]] = {}

    def save_themes(self, themes: list[Theme]) -> int:
        existing = {theme.id: theme for theme in self.themes}
        for theme in themes:
            existing[theme.id] = theme
        self.themes = list(existing.values())
        return len(themes)

    def add_findings(self, theme_id: str, findings: list[Finding]) -> None:
        self.findings_by_theme[theme_id] = findings

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

    def list_findings_for_theme(self, theme_id: str) -> list[Finding]:
        return self.findings_by_theme.get(theme_id, [])
