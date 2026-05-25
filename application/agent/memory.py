"""Computed memory summaries for niche research agents."""
from dataclasses import dataclass

from domain.agent import AgentFeedback, AgentPreferences
from domain.market import Market
from domain.source import MonitoredSource, SourceHealth


@dataclass(frozen=True)
class AgentMemorySummary:
    """User-facing summary of what the agent has learned so far."""

    market_id: str
    headline: str
    learned_preferences: list[str]
    source_notes: list[str]
    feedback_notes: list[str]


def build_agent_memory_summary(
    *,
    market: Market,
    preferences: AgentPreferences,
    feedback: list[AgentFeedback],
    sources: list[MonitoredSource],
    source_health: list[SourceHealth],
) -> AgentMemorySummary:
    """Build a compact memory summary from persisted agent state."""
    health_by_source_id = {
        health.monitored_source_id: health
        for health in source_health
    }
    healthy_sources = [
        source
        for source in sources
        if health_by_source_id.get(source.id) is not None
        and health_by_source_id[source.id].last_status == "healthy"
    ]
    failing_sources = [
        source
        for source in sources
        if health_by_source_id.get(source.id) is not None
        and health_by_source_id[source.id].last_status == "failing"
    ]
    saved_count = sum(1 for item in feedback if item.action == "save")
    dismissed_count = sum(1 for item in feedback if item.action == "dismiss")

    learned_preferences = []
    if preferences.preferred_source_families:
        learned_preferences.append(
            "Prioritize "
            + ", ".join(preferences.preferred_source_families)
            + " sources."
        )
    if preferences.ignored_themes:
        learned_preferences.append(
            "Avoid themes: " + ", ".join(preferences.ignored_themes) + "."
        )
    if preferences.ignored_categories:
        learned_preferences.append(
            "Avoid categories: " + ", ".join(preferences.ignored_categories) + "."
        )
    if preferences.extra_instructions:
        learned_preferences.append(preferences.extra_instructions)
    if not learned_preferences:
        learned_preferences.append("Use default source and ranking preferences.")

    source_notes = [
        f"{len(sources)} monitored source(s), {len(healthy_sources)} recently healthy."
    ]
    if failing_sources:
        source_notes.append(
            f"{len(failing_sources)} source(s) need attention after recent failures."
        )
    if preferences.muted_source_ids:
        source_notes.append(
            f"{len(preferences.muted_source_ids)} source(s) muted for future runs."
        )

    feedback_notes = []
    if saved_count or dismissed_count:
        feedback_notes.append(
            f"{saved_count} saved gap(s), {dismissed_count} dismissed gap(s)."
        )
    more_like_count = sum(1 for item in feedback if item.action == "more_like_this")
    less_like_count = sum(1 for item in feedback if item.action == "less_like_this")
    if more_like_count or less_like_count:
        feedback_notes.append(
            f"{more_like_count} positive training signal(s), "
            f"{less_like_count} negative training signal(s)."
        )
    if not feedback_notes:
        feedback_notes.append("No gap feedback recorded yet.")

    headline = (
        f"The agent is tracking {market.name} with {len(sources)} source(s) "
        f"and {len(feedback)} feedback event(s)."
    )
    return AgentMemorySummary(
        market_id=market.id,
        headline=headline,
        learned_preferences=learned_preferences,
        source_notes=source_notes,
        feedback_notes=feedback_notes,
    )
