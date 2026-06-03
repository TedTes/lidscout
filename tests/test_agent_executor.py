from application.agent import AgentActionExecutor
from domain.agent import AgentAction, AgentAlert, AgentFollowUp
from domain.niche import NicheSource
from infrastructure.db import (
    InMemoryAgentActionRepository,
    InMemoryAgentAlertRepository,
    InMemoryAgentFollowUpRepository,
    InMemoryNicheSourceRepository,
)


def test_executor_pauses_source_for_approved_action() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    source_repository.save_niche_sources(
        [
            NicheSource.create(
                id="source-1",
                niche_id="niche-1",
                locator="https://example.com/feed",
                source_type="web",
                source_family="forum",
                is_gate_free=True,
                health_status="failing",
            )
        ]
    )
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="pause_source",
            status="approved",
            metadata={"source_id": "source-1"},
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
    ).execute_approved_actions("market-1")

    sources = source_repository.list_niche_sources("niche-1")
    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 1
    assert result.failed_count == 0
    assert sources[0].health_status == "paused"
    assert actions[0].status == "completed"


def test_executor_marks_pause_source_failed_when_source_id_missing() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="pause_source",
            status="approved",
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 0
    assert result.failed_count == 1
    assert actions[0].status == "failed"


def test_executor_answers_follow_up_for_approved_action() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    follow_up_repository = InMemoryAgentFollowUpRepository()
    follow_up_repository.save_agent_follow_up(
        AgentFollowUp.create(
            id="follow-up-1",
            user_niche_id="market-1",
            question="Why is this credible?",
        )
    )
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="answer_follow_up",
            status="approved",
            metadata={
                "follow_up_id": "follow-up-1",
                "response": "The agent found two independent evidence items.",
            },
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
        follow_up_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    follow_ups = follow_up_repository.list_agent_follow_ups(
        user_niche_id="market-1",
    )
    assert result.executed_count == 1
    assert result.failed_count == 0
    assert actions[0].status == "completed"
    assert follow_ups[0].status == "answered"
    assert follow_ups[0].response == "The agent found two independent evidence items."
    assert follow_ups[0].metadata["answered_by_action_id"] == "action-1"


def test_executor_marks_follow_up_action_failed_when_response_missing() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    follow_up_repository = InMemoryAgentFollowUpRepository()
    follow_up_repository.save_agent_follow_up(
        AgentFollowUp.create(
            id="follow-up-1",
            user_niche_id="market-1",
            question="Why is this credible?",
        )
    )
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="answer_follow_up",
            status="approved",
            metadata={"follow_up_id": "follow-up-1"},
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
        follow_up_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    follow_ups = follow_up_repository.list_agent_follow_ups(
        user_niche_id="market-1",
    )
    assert result.executed_count == 0
    assert result.failed_count == 1
    assert actions[0].status == "failed"
    assert follow_ups[0].status == "queued"


def test_executor_acknowledges_alert_for_approved_action() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    alert_repository = InMemoryAgentAlertRepository()
    alert_repository.save_agent_alert(
        AgentAlert.create(
            id="alert-1",
            user_niche_id="market-1",
            alert_type="threshold",
            title="Theme crossed threshold",
            severity="warning",
        )
    )
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="send_alert",
            status="approved",
            metadata={"alert_id": "alert-1"},
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
        alert_repository=alert_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    alert = alert_repository.get_agent_alert("alert-1")
    assert result.executed_count == 1
    assert result.failed_count == 0
    assert actions[0].status == "completed"
    assert alert is not None
    assert alert.status == "acknowledged"


def test_executor_marks_alert_action_failed_when_alert_id_missing() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    alert_repository = InMemoryAgentAlertRepository()
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="send_alert",
            status="approved",
            metadata={},
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
        alert_repository=alert_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 0
    assert result.failed_count == 1
    assert actions[0].status == "failed"


def test_executor_adds_source_for_concrete_source_suggestion() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="suggest_source",
            status="approved",
            metadata={
                "niche_id": "niche-1",
                "locator": "https://hn.algolia.com/api/v1/search_by_date?query=dbt",
                "source_type": "hackernews_search",
                "source_family": "technical_forum",
                "is_gate_free": True,
                "limit": 25,
                "tier": 2,
                "signal_quality_score": 0.78,
                "access_mode": "api",
                "recommended_cadence": "daily",
            },
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    sources = source_repository.list_niche_sources("niche-1")
    assert result.executed_count == 1
    assert result.failed_count == 0
    assert actions[0].status == "completed"
    assert len(sources) == 1
    assert sources[0].source_type == "hackernews_search"
    assert sources[0].options["created_by_action_id"] == "action-1"


def test_executor_marks_source_suggestion_failed_when_locator_missing() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemoryNicheSourceRepository()
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="suggest_source",
            status="approved",
            metadata={"source_count": 0},
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 0
    assert result.failed_count == 1
    assert actions[0].status == "failed"
    assert source_repository.list_niche_sources("niche-1") == []
