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
        queued_follow_up = next(
            (
                follow_up
                for follow_up in planner_input.follow_ups
                if follow_up.status == "queued"
            ),
            None,
        )
        if queued_follow_up is not None:
            return [
                AgentAction.create(
                    user_niche_id=planner_input.user_niche.id,
                    action_type="answer_follow_up",
                    reason="A queued follow-up question is waiting for the agent.",
                    metadata={
                        "planner_version": "v1",
                        "follow_up_id": queued_follow_up.id,
                        "question": queued_follow_up.question,
                    },
                )
            ]

        failing_source = next(
            (
                source
                for source in planner_input.sources
                if source.enabled and source.health_status == "failing"
            ),
            None,
        )
        if failing_source is not None:
            return [
                AgentAction.create(
                    user_niche_id=planner_input.user_niche.id,
                    action_type="pause_source",
                    reason="An enabled source is currently failing.",
                    metadata={
                        "planner_version": "v1",
                        "source_id": failing_source.id,
                        "locator": failing_source.locator,
                        "last_error": failing_source.last_error,
                    },
                )
            ]

        low_quality_source = next(
            (
                source
                for source in planner_input.sources
                if source.enabled
                and source.signal_quality_score is not None
                and source.signal_quality_score < 0.15
            ),
            None,
        )
        if low_quality_source is not None:
            return [
                AgentAction.create(
                    user_niche_id=planner_input.user_niche.id,
                    action_type="pause_source",
                    reason="An enabled source has repeatedly produced low-quality evidence.",
                    metadata={
                        "planner_version": "v1",
                        "source_id": low_quality_source.id,
                        "locator": low_quality_source.locator,
                        "signal_quality_score": low_quality_source.signal_quality_score,
                    },
                )
            ]

        healthy_sources = [
            source
            for source in planner_input.sources
            if source.enabled and source.health_status in {"active", "unknown"}
        ]
        if not healthy_sources:
            return [
                AgentAction.create(
                    user_niche_id=planner_input.user_niche.id,
                    action_type="suggest_source",
                    reason="The agent has no healthy active sources to scan.",
                    metadata={
                        "planner_version": "v1",
                        "source_count": len(planner_input.sources),
                    },
                )
            ]

        open_alert = next(
            (
                alert
                for alert in planner_input.alerts
                if alert.status == "open" and alert.severity in {"warning", "critical"}
            ),
            None,
        )
        if open_alert is not None:
            return [
                AgentAction.create(
                    user_niche_id=planner_input.user_niche.id,
                    action_type="send_alert",
                    reason="A high-priority alert is ready for delivery.",
                    metadata={
                        "planner_version": "v1",
                        "alert_id": open_alert.id,
                        "alert_type": open_alert.alert_type,
                        "severity": open_alert.severity,
                    },
                )
            ]

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
