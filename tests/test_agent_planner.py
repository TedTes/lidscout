from application.agent import AgentPlannerInput, AgentPlannerService
from domain.niche import UserNiche


def test_agent_planner_defaults_to_wait_action() -> None:
    user_niche = UserNiche.create(
        id="market-1",
        user_id="user-1",
        job="Build internal tools",
        buyer="Ops teams",
        category="devtools",
    )
    actions = AgentPlannerService().plan_actions(
        AgentPlannerInput(
            user_niche=user_niche,
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
