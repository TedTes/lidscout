"""Cold-start planning for a niche research agent."""
from dataclasses import dataclass

from domain.niche import NicheCompany, NicheSource, UserNiche


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
    source_explanations: list[str]
    expected_result_window: str
    no_result_guidance: list[str]


class AgentColdStartService:
    """Build a setup plan before the agent has feedback history."""

    def build_plan(
        self,
        *,
        user_niche: UserNiche,
        companies: list[NicheCompany],
        sources: list[NicheSource],
    ) -> AgentColdStartPlan:
        """Return the next setup actions for one niche."""
        active_sources = [s for s in sources if s.health_status != "paused"]
        brief = AgentResearchBrief(
            market_id=user_niche.id,
            niche_name=user_niche.job,
            target_user=user_niche.buyer,
            objective=(
                f"Find recurring public complaints and product gaps for {user_niche.job}."
            ),
            company_count=len(companies),
            source_family_priorities=_source_family_priorities(active_sources),
        )
        next_actions = _next_actions(
            user_niche=user_niche,
            company_count=len(companies),
            active_source_count=len(active_sources),
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
            suggested_source_count=0,
            next_actions=next_actions,
            source_explanations=_source_explanations(active_sources),
            expected_result_window=_expected_result_window(active_sources),
            no_result_guidance=_no_result_guidance(active_sources),
        )


def _source_family_priorities(sources: list[NicheSource]) -> list[str]:
    families: list[str] = []
    seen: set[str] = set()
    for source in sources:
        family = source.source_family.strip().lower()
        if family and family not in seen:
            families.append(family)
            seen.add(family)
    return families


def _source_explanations(sources: list[NicheSource]) -> list[str]:
    if not sources:
        return ["No active sources are configured yet."]
    families = {source.source_family.strip().lower() for source in sources}
    explanations: list[str] = []
    if "technical_forum" in families:
        explanations.append(
            "Technical forums are scanned because they often contain detailed setup, bug, and workflow complaints."
        )
    if "reviews" in families:
        explanations.append(
            "Review sources are monitored for direct buyer-side dislikes and comparison feedback."
        )
    if "social" in families:
        explanations.append(
            "Social sources are monitored for fresh public complaints, but may be skipped until authenticated access is configured."
        )
    if "owned_site" in families:
        explanations.append(
            "Owned content is monitored for competitor positioning, changelog, and roadmap context."
        )
    if not explanations:
        explanations.append(
            "Configured sources are scanned when they are accessible and likely to contain buyer evidence."
        )
    return explanations


def _expected_result_window(active_sources: list[NicheSource]) -> str:
    if not active_sources:
        return "Add at least one active source before the first scan can produce results."
    if len(active_sources) < 3:
        return "First scan usually completes in 8-15 minutes, but sparse sources may need multiple scheduled runs."
    return "First scan usually completes in 8-15 minutes; recurring opportunities may need 1-2 scheduled runs for corroboration."


def _no_result_guidance(active_sources: list[NicheSource]) -> list[str]:
    if not active_sources:
        return [
            "Add or enable sources that contain buyer complaints.",
            "Prefer gate-free technical forums, GitHub issues, Stack Overflow, or public roadmaps first.",
        ]
    return [
        "Check source health for blocked or noisy sources.",
        "Add more buyer-side sources if the scan found posts but no qualified opportunities.",
        "Broaden the research brief if the niche is too narrow.",
    ]


def _next_actions(
    *,
    user_niche: UserNiche,
    company_count: int,
    active_source_count: int,
) -> list[str]:
    actions: list[str] = []
    if company_count == 0:
        actions.append("add_companies")
    if active_source_count == 0:
        actions.append("add_sources")
    if not actions:
        actions.append("run_first_scan")
    return actions
