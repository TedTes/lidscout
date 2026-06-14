from application.agent import AgentActionExecutor
from domain.agent import AgentAction, AgentAlert, AgentFollowUp
from domain.niche import UserSource
from domain.source import Source
from infrastructure.db import (
    InMemoryAgentActionRepository,
    InMemoryAgentAlertRepository,
    InMemoryAgentFollowUpRepository,
    InMemorySourceRepository,
    InMemoryUserSourceRepository,
)


def test_executor_marks_pause_source_failed_when_source_id_missing() -> None:
    action_repository = InMemoryAgentActionRepository()
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="pause_source",
            status="approved",
        )
    )

    result = AgentActionExecutor(action_repository).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 0
    assert result.failed_count == 1
    assert actions[0].status == "failed"


def test_executor_pauses_user_source_binding_for_approved_action() -> None:
    action_repository = InMemoryAgentActionRepository()
    canonical_source_repository = InMemorySourceRepository()
    canonical_source_repository.save_sources(
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
    user_source_repository = InMemoryUserSourceRepository()
    user_source_repository.save_user_sources(
        [
            UserSource.create(
                id="user-source-1",
                user_niche_id="market-1",
                source_id="source-1",
                enabled=True,
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
        source_repository=canonical_source_repository,
        user_source_repository=user_source_repository,
    ).execute_approved_actions("market-1")

    user_source = user_source_repository.get_user_source("market-1", "source-1")
    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 1
    assert result.failed_count == 0
    assert user_source is not None
    assert user_source.enabled is False
    assert user_source.muted is True
    assert actions[0].status == "completed"


def test_executor_answers_follow_up_for_approved_action() -> None:
    action_repository = InMemoryAgentActionRepository()
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
        follow_up_repository=follow_up_repository,
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
        follow_up_repository=follow_up_repository,
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
        alert_repository=alert_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 0
    assert result.failed_count == 1
    assert actions[0].status == "failed"


def test_executor_adds_user_source_for_concrete_source_suggestion() -> None:
    action_repository = InMemoryAgentActionRepository()
    canonical_source_repository = InMemorySourceRepository()
    user_source_repository = InMemoryUserSourceRepository()
    action_repository.save_agent_action(
        AgentAction.create(
            id="action-1",
            user_niche_id="market-1",
            action_type="suggest_source",
            status="approved",
            metadata={
                "locator": "https://hn.algolia.com/api/v1/search_by_date?query=dbt",
                "source_type": "hackernews_search",
                "source_family": "technical_forum",
                "is_gate_free": True,
                "limit": 25,
                "access_mode": "api",
                "scan_frequency": "daily",
            },
        )
    )

    result = AgentActionExecutor(
        action_repository,
        source_repository=canonical_source_repository,
        user_source_repository=user_source_repository,
    ).execute_approved_actions("market-1")

    source = canonical_source_repository.get_source_by_identity(
        "hackernews_search",
        "https://hn.algolia.com/api/v1/search_by_date?query=dbt",
    )
    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert source is not None
    user_source = user_source_repository.get_user_source("market-1", source.id)
    assert result.executed_count == 1
    assert result.failed_count == 0
    assert actions[0].status == "completed"
    assert user_source is not None
    assert user_source.limit == 25
    assert user_source.cadence == "daily"
    assert user_source.options["created_by_action_id"] == "action-1"


def test_executor_marks_source_suggestion_failed_when_locator_missing() -> None:
    action_repository = InMemoryAgentActionRepository()
    source_repository = InMemorySourceRepository()
    user_source_repository = InMemoryUserSourceRepository()
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
        source_repository=source_repository,
        user_source_repository=user_source_repository,
    ).execute_approved_actions("market-1")

    actions = action_repository.list_agent_actions(user_niche_id="market-1")
    assert result.executed_count == 0
    assert result.failed_count == 1
    assert actions[0].status == "failed"
    assert source_repository.list_sources() == []
