from application.agent import AgentPlannerService


def test_agent_planner_defaults_to_wait_action() -> None:
    actions = AgentPlannerService().plan_actions(user_niche_id="market-1")

    assert len(actions) == 1
    assert actions[0].user_niche_id == "market-1"
    assert actions[0].action_type == "wait"
    assert actions[0].status == "proposed"
    assert actions[0].metadata["planner_version"] == "v1"
