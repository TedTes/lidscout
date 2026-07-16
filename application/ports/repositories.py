"""Persistence contracts for domain entities."""
from datetime import datetime
from typing import Protocol

from domain.niche import (
    Niche,
    NicheCompany,
    TemplateSourceBinding,
    UserNiche,
    UserSource,
    UserSourcePreference,
    UserSourceRunStats,
)
from domain.agent import (
    AgentActivity,
    AgentFeedback,
    AgentPreferences,
)
from domain.cluster import SignalCluster
from domain.finding import Finding
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import Source, SourceLocator
from domain.theme import Theme, ThemeFinding


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


class FindingRepository(Protocol):
    """Persistence boundary for durable accumulated findings."""

    def save_findings(self, findings: list[Finding]) -> int:
        """Persist findings and return the number saved or updated."""
        ...

    def get_seen_post_ids(
        self,
        user_niche_id: str,
        post_ids: list[str],
    ) -> set[str]:
        """Return the subset of post_ids that already have a finding for this niche."""
        ...

    def list_findings(
        self,
        *,
        user_niche_id: str | None = None,
        unassigned_only: bool = False,
    ) -> list[Finding]:
        """Load accumulated findings, optionally scoped to one niche."""
        ...


class ThemeRepository(Protocol):
    """Persistence boundary for durable accumulated themes."""

    def save_themes(self, themes: list[Theme]) -> int:
        """Persist themes and return the number saved or updated."""
        ...

    def save_theme_findings(self, assignments: list[ThemeFinding]) -> int:
        """Persist theme-finding assignments."""
        ...

    def list_themes(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
    ) -> list[Theme]:
        """Load accumulated themes, optionally scoped and filtered."""
        ...

    def list_changed_themes(
        self,
        *,
        user_niche_id: str,
        since: datetime,
    ) -> list[Theme]:
        """Load themes changed since a run timestamp."""
        ...

    def find_similar_themes(
        self,
        user_niche_id: str,
        embedding: list[float],
        *,
        top_k: int = 5,
        min_similarity: float = 0.70,
    ) -> list[Theme]:
        """Return the top-k themes whose centroid is within min_similarity of embedding.

        Results are ordered by cosine similarity descending. Uses the HNSW index
        on centroid_embedding for fast approximate nearest-neighbour search.
        """
        ...

    def list_findings_for_theme(self, theme_id: str) -> list[Finding]:
        """Load findings assigned to one theme."""
        ...

    def refresh_theme_rollups(self, theme_ids: list[str]) -> int:
        """Recompute theme counts and centroid embeddings from assigned findings."""
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

    def delete_agent_feedback(
        self,
        *,
        user_niche_id: str,
        opportunity_id: str,
        action: str,
    ) -> bool:
        """Delete one feedback action and return whether anything changed."""
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


class SourceRepository(Protocol):
    """Persistence boundary for canonical source identities."""

    def save_sources(self, sources: list[Source]) -> int:
        """Persist canonical sources and return the number saved."""
        ...

    def get_source(self, source_id: str) -> Source | None:
        """Load one canonical source by id."""
        ...

    def get_source_by_identity(self, source_type: str, locator: str) -> Source | None:
        """Load one canonical source by its unique source_type and locator pair."""
        ...

    def list_sources(
        self,
        *,
        source_type: str | None = None,
        source_family: str | None = None,
    ) -> list[Source]:
        """Load canonical sources, optionally filtered by type or family."""
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
        is_custom: bool | None = None,
    ) -> list[Niche]:
        """Load niches, optionally filtered by category, status, or is_custom."""
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


class TemplateSourceBindingRepository(Protocol):
    """Persistence boundary for template-to-source default bindings."""

    def save_template_source_bindings(
        self,
        bindings: list[TemplateSourceBinding],
    ) -> int:
        """Persist template source bindings and return the number saved."""
        ...

    def list_template_source_bindings(
        self,
        template_niche_id: str,
        *,
        default_enabled: bool | None = None,
    ) -> list[TemplateSourceBinding]:
        """Load source bindings for a template niche, optionally filtered."""
        ...

    def delete_template_source_binding(self, binding_id: str) -> bool:
        """Delete one template source binding and return whether it existed."""
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


class UserSourceRepository(Protocol):
    """Persistence boundary for concrete per-user source bindings."""

    def save_user_sources(self, sources: list[UserSource]) -> int:
        """Persist user source bindings and return the number saved."""
        ...

    def get_user_source(
        self,
        user_niche_id: str,
        source_id: str,
    ) -> UserSource | None:
        """Load one user source by user niche and canonical source."""
        ...

    def list_user_sources(
        self,
        user_niche_id: str,
        *,
        enabled: bool | None = None,
        include_muted: bool = True,
    ) -> list[UserSource]:
        """Load source bindings for one user niche."""
        ...

    def delete_user_source(self, user_source_id: str) -> bool:
        """Delete one user source binding and return whether it existed."""
        ...


class UserSourcePreferenceRepository(Protocol):
    """Persistence boundary for per-user source preference overrides."""

    def save_user_source_preference(
        self,
        preference: UserSourcePreference,
    ) -> bool:
        """Persist one user source preference and return whether it was inserted."""
        ...

    def get_user_source_preference(
        self,
        user_niche_id: str,
        source_id: str,
    ) -> UserSourcePreference | None:
        """Load one preference by user niche and canonical source."""
        ...

    def list_user_source_preferences(
        self,
        user_niche_id: str,
    ) -> list[UserSourcePreference]:
        """Load all source preferences for a user niche."""
        ...

    def delete_user_source_preference(self, preference_id: str) -> bool:
        """Delete one user source preference and return whether it existed."""
        ...


class UserSourceRunStatsRepository(Protocol):
    """Persistence boundary for per-user catalog source runtime stats."""

    def upsert_user_source_run_stats(
        self,
        stats: UserSourceRunStats,
    ) -> bool:
        """Create or replace cumulative runtime stats for one user source."""
        ...

    def get_user_source_run_stats(
        self,
        user_niche_id: str,
        source_id: str,
    ) -> UserSourceRunStats | None:
        """Load cumulative runtime stats for one user source."""
        ...

    def list_user_source_run_stats(
        self,
        user_niche_id: str,
        source_ids: list[str] | None = None,
    ) -> list[UserSourceRunStats]:
        """Load user source stats, optionally limited to source IDs."""
        ...
