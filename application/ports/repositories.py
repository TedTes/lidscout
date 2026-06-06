"""Persistence contracts for domain entities."""
from typing import Protocol

from domain.niche import (
    Gap,
    Niche,
    NicheCompany,
    NicheSource,
    NicheSourceRunStats,
    UserNiche,
)
from domain.agent import (
    AgentAction,
    AgentActivity,
    AgentAlert,
    AgentFeedback,
    AgentFollowUp,
    AgentPreferences,
)
from domain.cluster import SignalCluster
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import SourceLocator


class PostRepository(Protocol):
    """Persistence boundary for raw posts."""

    def save_posts(self, posts: list[RawPost]) -> int:
        """Persist posts and return the number saved."""
        ...

    def get_post(self, post_id: str) -> RawPost | None:
        """Load one post by id."""
        ...

    def list_posts(self) -> list[RawPost]:
        """Load all persisted posts."""
        ...


class SignalRepository(Protocol):
    """Persistence boundary for extracted signals."""

    def save_signals(self, signals: list[Signal]) -> int:
        """Persist signals and return the number saved."""
        ...

    def get_signal(self, signal_id: str) -> Signal | None:
        """Load one signal by id."""
        ...

    def delete_signal(self, signal_id: str) -> bool:
        """Delete one signal and return whether it existed."""
        ...

    def list_signals(self) -> list[Signal]:
        """Load all persisted signals."""
        ...


class ScoreRepository(Protocol):
    """Persistence boundary for opportunity scores."""

    def save_scores(self, scores: list[OpportunityScore]) -> int:
        """Persist scores and return the number saved."""
        ...

    def get_score(self, signal_id: str) -> OpportunityScore | None:
        """Load one score by signal id."""
        ...

    def delete_score(self, signal_id: str) -> bool:
        """Delete one score by signal id and return whether it existed."""
        ...

    def list_scores(self) -> list[OpportunityScore]:
        """Load all persisted scores."""
        ...


class ClusterRepository(Protocol):
    """Persistence boundary for signal clusters."""

    def save_clusters(self, clusters: list[SignalCluster]) -> int:
        """Persist clusters and return the number saved."""
        ...

    def get_cluster(self, cluster_id: str) -> SignalCluster | None:
        """Load one cluster by id."""
        ...

    def list_clusters(self) -> list[SignalCluster]:
        """Load all persisted clusters."""
        ...


class OpportunityRepository(Protocol):
    """Persistence boundary for synthesized opportunities."""

    def save_opportunities(self, opportunities: list[Opportunity]) -> int:
        """Persist opportunities and return the number saved."""
        ...

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        """Load one opportunity by id."""
        ...

    def list_opportunities(self) -> list[Opportunity]:
        """Load all persisted opportunities."""
        ...


class AgentPreferencesRepository(Protocol):
    """Persistence boundary for per-niche agent preferences."""

    def save_agent_preferences(self, preferences: AgentPreferences) -> bool:
        """Persist agent preferences and return whether they changed."""
        ...

    def get_agent_preferences(self, user_niche_id: str) -> AgentPreferences | None:
        """Load agent preferences for one user niche."""
        ...

    def delete_agent_preferences(self, user_niche_id: str) -> bool:
        """Delete agent preferences for one user niche."""
        ...


class AgentFeedbackRepository(Protocol):
    """Persistence boundary for user feedback that trains agent behavior."""

    def save_agent_feedback(self, feedback: AgentFeedback) -> bool:
        """Persist one feedback event and return whether it changed."""
        ...

    def list_agent_feedback(
        self,
        *,
        user_niche_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        """Load feedback events, optionally filtered by scope."""
        ...


class AgentActivityRepository(Protocol):
    """Persistence boundary for user-visible agent activity events."""

    def save_agent_activity(self, activity: AgentActivity) -> bool:
        """Persist one agent activity event."""
        ...

    def list_agent_activity(
        self,
        *,
        user_niche_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentActivity]:
        """Load activity events, optionally filtered by scope."""
        ...


class AgentAlertRepository(Protocol):
    """Persistence boundary for proactive agent alerts."""

    def save_agent_alert(self, alert: AgentAlert) -> bool:
        """Persist one agent alert."""
        ...

    def get_agent_alert(self, alert_id: str) -> AgentAlert | None:
        """Load one agent alert by id."""
        ...

    def list_agent_alerts(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAlert]:
        """Load alerts, optionally filtered by scope and status."""
        ...

    def acknowledge_agent_alert(self, alert_id: str) -> AgentAlert | None:
        """Mark one alert acknowledged and return the updated alert."""
        ...


class AgentFollowUpRepository(Protocol):
    """Persistence boundary for user follow-up questions and instructions."""

    def save_agent_follow_up(self, follow_up: AgentFollowUp) -> bool:
        """Persist one follow-up intent."""
        ...

    def list_agent_follow_ups(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentFollowUp]:
        """Load follow-ups, optionally filtered by scope and status."""
        ...

    def update_agent_follow_up(
        self,
        follow_up_id: str,
        *,
        status: str,
        response: str | None = None,
        metadata: dict | None = None,
    ) -> AgentFollowUp | None:
        """Update one follow-up state and return the updated follow-up."""
        ...


class AgentActionRepository(Protocol):
    """Persistence boundary for planned agent actions."""

    def save_agent_action(self, action: AgentAction) -> bool:
        """Persist one planned action and return whether it changed."""
        ...

    def list_agent_actions(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        action_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAction]:
        """Load planned actions, optionally filtered by scope and state."""
        ...

    def update_agent_action_status(
        self,
        action_id: str,
        status: str,
    ) -> AgentAction | None:
        """Update one planned action status and return the updated action."""
        ...


class PipelineRunMetricsRepository(Protocol):
    """Persistence boundary for pipeline run funnel metrics."""

    def save_pipeline_run_metrics(self, metrics: PipelineRunMetrics) -> bool:
        """Persist pipeline run metrics and return whether they were inserted."""
        ...

    def list_pipeline_run_metrics(self) -> list[PipelineRunMetrics]:
        """Load persisted pipeline run metrics."""
        ...


class SourceLocatorRepository(Protocol):
    """Persistence boundary for whitelisted source locators."""

    def save_source_locators(self, locators: list[SourceLocator]) -> int:
        """Persist source locators and return the number saved."""
        ...

    def get_source_locator(self, locator_id: str) -> SourceLocator | None:
        """Load one source locator by id."""
        ...

    def list_source_locators(self, enabled: bool | None = None) -> list[SourceLocator]:
        """Load source locators, optionally filtered by enabled state."""
        ...


class NicheRepository(Protocol):
    """Persistence boundary for shared operator-curated niches."""

    def save_niches(self, niches: list[Niche]) -> int:
        """Persist niches and return the number saved."""
        ...

    def get_niche(self, niche_id: str) -> Niche | None:
        """Load one niche by id."""
        ...

    def list_niches(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
    ) -> list[Niche]:
        """Load niches, optionally filtered by category or status."""
        ...

    def update_niche(self, niche: Niche) -> bool:
        """Update an existing niche and return whether it changed."""
        ...

    def delete_niche(self, niche_id: str) -> bool:
        """Delete one niche and return whether it existed."""
        ...


class NicheCompanyRepository(Protocol):
    """Persistence boundary for per-niche companies."""

    def save_niche_companies(self, companies: list[NicheCompany]) -> int:
        """Persist companies and return the number saved."""
        ...

    def list_niche_companies(self, niche_id: str) -> list[NicheCompany]:
        """Load all companies for a niche."""
        ...

    def delete_niche_company(self, company_id: str) -> bool:
        """Delete one company and return whether it existed."""
        ...


class NicheSourceRepository(Protocol):
    """Persistence boundary for niche-bound monitoring sources."""

    def save_niche_sources(self, sources: list[NicheSource]) -> int:
        """Persist sources and return the number saved."""
        ...

    def list_niche_sources(
        self,
        niche_id: str,
        *,
        enabled: bool | None = None,
        is_gate_free: bool | None = None,
        buyer_voice_verified: bool | None = None,
    ) -> list[NicheSource]:
        """Load sources for a niche, optionally filtered."""
        ...

    def update_niche_source(self, source: NicheSource) -> bool:
        """Replace mutable fields for one source and return whether it existed."""
        ...

    def update_niche_source_health(
        self,
        source_id: str,
        health_status: str,
        last_scanned_at: object | None = None,
        last_error: str | None = None,
    ) -> bool:
        """Update health status and last_scanned_at for one source."""
        ...

    def update_niche_source_quality(
        self,
        source_id: str,
        signal_quality_score: float,
        *,
        buyer_voice_verified: bool | None = None,
    ) -> bool:
        """Update the observed quality score for one source."""
        ...

    def upsert_niche_source_run_stats(
        self,
        stats: NicheSourceRunStats,
    ) -> bool:
        """Create or replace cumulative runtime stats for one source."""
        ...

    def get_niche_source_run_stats(
        self,
        source_id: str,
    ) -> NicheSourceRunStats | None:
        """Load cumulative runtime stats for one source."""
        ...

    def list_niche_source_run_stats(
        self,
        source_ids: list[str] | None = None,
    ) -> list[NicheSourceRunStats]:
        """Load cumulative runtime stats, optionally limited to source IDs."""
        ...

    def delete_niche_source(self, source_id: str) -> bool:
        """Delete one source and return whether it existed."""
        ...


class GapRepository(Protocol):
    """Persistence boundary for synthesised product gaps."""

    def save_gaps(self, gaps: list[Gap]) -> int:
        """Persist gaps and return the number saved."""
        ...

    def get_gap(self, gap_id: str) -> Gap | None:
        """Load one gap by id."""
        ...

    def list_gaps(
        self,
        niche_id: str,
        *,
        unmet_need_type: str | None = None,
        signal_strength: str | None = None,
    ) -> list[Gap]:
        """Load gaps for a niche, optionally filtered."""
        ...

    def delete_gap(self, gap_id: str) -> bool:
        """Delete one gap and return whether it existed."""
        ...


class UserNicheRepository(Protocol):
    """Persistence boundary for per-user niche adoptions."""

    def save_user_niche(self, user_niche: UserNiche) -> bool:
        """Persist a user niche and return whether it was inserted."""
        ...

    def get_user_niche(self, user_niche_id: str) -> UserNiche | None:
        """Load one user niche by id."""
        ...

    def list_user_niches(self, user_id: str) -> list[UserNiche]:
        """Load all niches adopted by a user."""
        ...

    def list_all_user_niches(self) -> list[UserNiche]:
        """Load every user_niche across all users (used by the pipeline coordinator)."""
        ...

    def update_user_niche(self, user_niche: UserNiche) -> bool:
        """Update an existing user niche and return whether it changed."""
        ...

    def delete_user_niche(self, user_niche_id: str) -> bool:
        """Delete one user niche and return whether it existed."""
        ...
