"""Planning service for niche research agents."""
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from application.source_quality import source_quality_status
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

        source_attention = _source_attention_candidate(planner_input.sources)
        if source_attention is not None:
            source, quality = source_attention
            return [
                AgentAction.create(
                    user_niche_id=planner_input.user_niche.id,
                    action_type="source_needs_attention",
                    reason=f"Source is {quality.label}: {quality.reason}",
                    metadata={
                        "planner_version": "v1",
                        "source_id": source.id,
                        "locator": source.locator,
                        "quality_status": quality.label,
                        "quality_reason": quality.reason,
                        "signal_quality_score": quality.score,
                        "last_error": source.last_error,
                    },
                )
            ]

        healthy_sources = [
            source
            for source in planner_input.sources
            if source.enabled and source.health_status in {"active", "unknown"}
        ]
        if not healthy_sources:
            source_metadata = _fallback_source_metadata(planner_input.user_niche)
            return [
                AgentAction.create(
                    user_niche_id=planner_input.user_niche.id,
                    action_type="suggest_source",
                    reason="The agent has no healthy active sources to scan.",
                    metadata={
                        "planner_version": "v1",
                        "source_count": len(planner_input.sources),
                        **source_metadata,
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


def _fallback_source_metadata(user_niche: UserNiche) -> dict[str, object]:
    if not user_niche.template_niche_id:
        return {}
    query = quote_plus(user_niche.job)
    return {
        "niche_id": user_niche.template_niche_id,
        "locator": (
            "https://hn.algolia.com/api/v1/search_by_date"
            f"?query={query}&tags=comment&hitsPerPage=25"
        ),
        "source_type": "hackernews_search",
        "source_family": "technical_forum",
        "is_gate_free": True,
        "enabled": True,
        "limit": 25,
        "tier": 2,
        "signal_quality_score": 0.78,
        "access_mode": "api",
        "recommended_cadence": "daily",
    }


def _source_attention_candidate(sources: list[NicheSource]):
    for source in sources:
        quality = source_quality_status(source)
        if quality.label in {"blocked", "noisy", "stale"}:
            return source, quality
    return None
