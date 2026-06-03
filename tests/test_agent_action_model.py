from domain.agent import AgentAction


def test_agent_action_create_normalizes_fields() -> None:
    action = AgentAction.create(
        user_niche_id=" market-1 ",
        action_type=" Scan_Sources ",
        status=" Proposed ",
        reason=" Find more evidence ",
        metadata={"source_count": 3},
    )

    assert action.id.startswith("agent-action-")
    assert action.user_niche_id == "market-1"
    assert action.action_type == "scan_sources"
    assert action.status == "proposed"
    assert action.reason == "Find more evidence"
    assert action.metadata == {"source_count": 3}
    assert action.created_at is not None
    assert action.completed_at is None


def test_agent_action_requires_action_type() -> None:
    try:
        AgentAction.create(user_niche_id="market-1", action_type="")
    except ValueError as exc:
        assert str(exc) == "action_type is required"
    else:
        raise AssertionError("Expected empty action_type to fail")


def test_agent_action_rejects_unsupported_values() -> None:
    try:
        AgentAction.create(user_niche_id="market-1", action_type="delete_everything")
    except ValueError as exc:
        assert str(exc) == "unsupported action_type"
    else:
        raise AssertionError("Expected unsupported action_type to fail")

    try:
        AgentAction.create(
            user_niche_id="market-1",
            action_type="wait",
            status="waiting",
        )
    except ValueError as exc:
        assert str(exc) == "unsupported status"
    else:
        raise AssertionError("Expected unsupported status to fail")
