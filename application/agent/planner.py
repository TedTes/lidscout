"""Planning service for niche research agents."""
from dataclasses import dataclass, field

from domain.agent import (
    AgentAction,
    AgentActivity,
    AgentAlert,
    AgentFollowUp,
    AgentPreferences,
)
from domain.niche import NicheSource, UserNiche
from domain.opportunity import Opportunity


@dataclass(frozen=True)
class AgentPlannerInput:
    """Read-only state used to plan the agent's next actions."""

    user_niche: UserNiche
    preferences: AgentPreferences | None = None
    sources: list[NicheSource] = field(default_factory=list)
    recent_activity: list[AgentActivity] = field(default_factory=list)
    alerts: list[AgentAlert] = field(default_factory=list)
    follow_ups: list[AgentFollowUp] = field(default_factory=list)
    opportunities: list[Opportunity] = field(default_factory=list)


class AgentPlannerService:
    """Build planned agent actions from current niche state."""

    def plan_actions(self, planner_input: AgentPlannerInput) -> list[AgentAction]:
        """Return the current planned actions for one niche agent."""
        return [
            AgentAction.create(
                user_niche_id=planner_input.user_niche.id,
                action_type="wait",
                reason="No planner inputs have been provided yet.",
                metadata={
                    "planner_version": "v1",
                    "source_count": len(planner_input.sources),
                    "follow_up_count": len(planner_input.follow_ups),
                    "alert_count": len(planner_input.alerts),
                    "opportunity_count": len(planner_input.opportunities),
                },
            )
        ]
