from application.agent import AgentActionExecutor
from domain.agent import AgentAction
from domain.niche import NicheSource
from infrastructure.db import InMemoryAgentActionRepository, InMemoryNicheSourceRepository


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
