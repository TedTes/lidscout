"""Planning service for niche research agents."""
from domain.agent import AgentAction


class AgentPlannerService:
    """Build planned agent actions from current niche state."""

    def plan_actions(self, *, user_niche_id: str) -> list[AgentAction]:
        """Return the current planned actions for one niche agent."""
        return [
            AgentAction.create(
                user_niche_id=user_niche_id,
                action_type="wait",
                reason="No planner inputs have been provided yet.",
                metadata={"planner_version": "v1"},
            )
        ]
