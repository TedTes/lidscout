"""Cold-start planning for a niche research agent."""
from dataclasses import dataclass

from domain.niche import NicheCompany, NicheSource, UserNiche
from domain.source import SourceCandidate


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
        user_niche: UserNiche,
        companies: list[NicheCompany],
        sources: list[NicheSource],
        source_suggestions: list[SourceCandidate],
    ) -> AgentColdStartPlan:
        """Return the next setup actions for one niche."""
        active_sources = [s for s in sources if s.health_status != "paused"]
        suggested_new_sources = [
            suggestion
            for suggestion in source_suggestions
            if not suggestion.already_monitored
        ]
        brief = AgentResearchBrief(
            market_id=user_niche.id,
            niche_name=user_niche.job,
            target_user=user_niche.buyer,
            objective=(
                f"Find recurring public complaints and product gaps for {user_niche.job}."
            ),
            company_count=len(companies),
            source_family_priorities=_source_family_priorities(source_suggestions),
        )
        next_actions = _next_actions(
            user_niche=user_niche,
            company_count=len(companies),
            active_source_count=len(active_sources),
            suggested_new_source_count=len(suggested_new_sources),
        )
        status = (
            "ready_for_scan"
            if next_actions == ["run_first_scan"]
            else "setup_needed"
        )
        return AgentColdStartPlan(
            market_id=user_niche.id,
            status=status,
            brief=brief,
            monitored_source_count=len(sources),
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
    user_niche: UserNiche,
    company_count: int,
    active_source_count: int,
    suggested_new_source_count: int,
) -> list[str]:
    actions: list[str] = []
    if company_count == 0:
        actions.append("add_companies")
    if active_source_count == 0:
        actions.append("add_sources")
    elif suggested_new_source_count > 0 and active_source_count < 3:
        actions.append("review_suggested_sources")
    if not actions:
        actions.append("run_first_scan")
    return actions
