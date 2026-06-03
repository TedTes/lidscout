from application.agent import AgentPlannerInput, AgentPlannerService
from domain.agent import AgentAlert, AgentFollowUp
from domain.niche import NicheSource, UserNiche


def _user_niche() -> UserNiche:
    return UserNiche.create(
        id="market-1",
        user_id="user-1",
        job="Build internal tools",
        buyer="Ops teams",
        category="devtools",
    )


def _source(**overrides: object) -> NicheSource:
    values = {
        "id": "source-1",
        "niche_id": "niche-1",
        "locator": "https://example.com/feed",
        "source_type": "web",
        "source_family": "forum",
        "is_gate_free": True,
        "enabled": True,
        "health_status": "active",
    }
    values.update(overrides)
    return NicheSource.create(**values)  # type: ignore[arg-type]


def test_agent_planner_defaults_to_wait_action() -> None:
    user_niche = _user_niche()
    actions = AgentPlannerService().plan_actions(
        AgentPlannerInput(
            user_niche=user_niche,
            sources=[_source()],
            follow_ups=[],
            opportunities=[],
        )
    )

    assert len(actions) == 1
    assert actions[0].user_niche_id == "market-1"
    assert actions[0].action_type == "wait"
    assert actions[0].status == "proposed"
    assert actions[0].metadata["planner_version"] == "v1"
    assert actions[0].metadata["follow_up_count"] == 0


def test_agent_planner_answers_queued_follow_up_first() -> None:
    follow_up = AgentFollowUp.create(
        id="follow-up-1",
        user_niche_id="market-1",
        question="Why is this gap credible?",
    )

    actions = AgentPlannerService().plan_actions(
        AgentPlannerInput(
            user_niche=_user_niche(),
            sources=[_source(health_status="failing", last_error="blocked")],
            follow_ups=[follow_up],
        )
    )

    assert actions[0].action_type == "answer_follow_up"
    assert actions[0].metadata["follow_up_id"] == "follow-up-1"


def test_agent_planner_pauses_failing_source() -> None:
    actions = AgentPlannerService().plan_actions(
        AgentPlannerInput(
            user_niche=_user_niche(),
            sources=[_source(health_status="failing", last_error="403 blocked")],
        )
    )

    assert actions[0].action_type == "pause_source"
    assert actions[0].metadata["source_id"] == "source-1"


def test_agent_planner_suggests_source_without_healthy_sources() -> None:
    actions = AgentPlannerService().plan_actions(
        AgentPlannerInput(user_niche=_user_niche(), sources=[])
    )

    assert actions[0].action_type == "suggest_source"


def test_agent_planner_sends_high_priority_alert() -> None:
    alert = AgentAlert.create(
        id="alert-1",
        user_niche_id="market-1",
        alert_type="gap_threshold",
        title="High confidence gap",
        severity="warning",
    )

    actions = AgentPlannerService().plan_actions(
        AgentPlannerInput(
            user_niche=_user_niche(),
            sources=[_source()],
            alerts=[alert],
        )
    )

    assert actions[0].action_type == "send_alert"
    assert actions[0].metadata["alert_id"] == "alert-1"
