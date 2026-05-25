"""Cold-start planning for a niche research agent."""
from dataclasses import dataclass

from domain.competitor import Competitor
from domain.market import Market
from domain.source import MonitoredSource, SourceCandidate


@dataclass(frozen=True)
class AgentResearchBrief:
    """User-facing research brief inferred from niche setup."""

    market_id: str
    niche_name: str
    target_user: str
    objective: str
    company_count: int
    source_family_priorities: list[str]


@dataclass(frozen=True)
class AgentColdStartPlan:
    """Setup status for a new or underconfigured niche agent."""

    market_id: str
    status: str
    brief: AgentResearchBrief
    monitored_source_count: int
    active_source_count: int
    suggested_source_count: int
    next_actions: list[str]


class AgentColdStartService:
    """Build a setup plan before the agent has feedback history."""

    def build_plan(
        self,
        *,
        market: Market,
        competitors: list[Competitor],
        monitored_sources: list[MonitoredSource],
        source_suggestions: list[SourceCandidate],
    ) -> AgentColdStartPlan:
        """Return the next setup actions for one niche."""
        active_sources = [source for source in monitored_sources if source.enabled]
        suggested_new_sources = [
            suggestion
            for suggestion in source_suggestions
            if not suggestion.already_monitored
        ]
        brief = AgentResearchBrief(
            market_id=market.id,
            niche_name=market.name,
            target_user=(
                market.target_user
                or "product teams and founders evaluating this niche"
            ),
            objective=(
                market.idea_prompt
                or f"Find recurring public complaints and product gaps in {market.name}."
            ),
            company_count=len(competitors),
            source_family_priorities=_source_family_priorities(source_suggestions),
        )
        next_actions = _next_actions(
            market=market,
            company_count=len(competitors),
            active_source_count=len(active_sources),
            suggested_new_source_count=len(suggested_new_sources),
        )
        status = (
            "ready_for_scan"
            if next_actions == ["run_first_scan"]
            else "setup_needed"
        )
        return AgentColdStartPlan(
            market_id=market.id,
            status=status,
            brief=brief,
            monitored_source_count=len(monitored_sources),
            active_source_count=len(active_sources),
            suggested_source_count=len(suggested_new_sources),
            next_actions=next_actions,
        )


def _source_family_priorities(suggestions: list[SourceCandidate]) -> list[str]:
    families: list[str] = []
    seen: set[str] = set()
    for suggestion in sorted(
        suggestions,
        key=lambda candidate: candidate.rank_score,
        reverse=True,
    ):
        family = suggestion.source_family.strip().lower()
        if family and family not in seen:
            families.append(family)
            seen.add(family)
    return families


def _next_actions(
    *,
    market: Market,
    company_count: int,
    active_source_count: int,
    suggested_new_source_count: int,
) -> list[str]:
    actions: list[str] = []
    if market.target_user is None and market.idea_prompt is None:
        actions.append("refine_research_brief")
    if company_count == 0:
        actions.append("add_companies")
    if active_source_count == 0:
        actions.append("add_sources")
    elif suggested_new_source_count > 0 and active_source_count < 3:
        actions.append("review_suggested_sources")
    if not actions:
        actions.append("run_first_scan")
    return actions
