"""Persistence contracts for domain entities."""
from typing import Protocol

from domain.agent import AgentFeedback, AgentPreferences
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.market import Market
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import MonitoredSource, SourceLocator


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


class MarketRepository(Protocol):
    """Persistence boundary for watched markets or niches."""

    def save_markets(self, markets: list[Market]) -> int:
        """Persist markets and return the number saved."""
        ...

    def get_market(self, market_id: str) -> Market | None:
        """Load one market by id."""
        ...

    def list_markets(self) -> list[Market]:
        """Load all persisted markets."""
        ...

    def update_market(self, market: Market) -> bool:
        """Update an existing market and return whether it changed."""
        ...

    def delete_market(self, market_id: str) -> bool:
        """Delete one market and return whether it existed."""
        ...


class AgentPreferencesRepository(Protocol):
    """Persistence boundary for per-niche agent preferences."""

    def save_agent_preferences(self, preferences: AgentPreferences) -> bool:
        """Persist agent preferences and return whether they changed."""
        ...

    def get_agent_preferences(self, market_id: str) -> AgentPreferences | None:
        """Load agent preferences for one market."""
        ...

    def delete_agent_preferences(self, market_id: str) -> bool:
        """Delete agent preferences for one market."""
        ...


class AgentFeedbackRepository(Protocol):
    """Persistence boundary for user feedback that trains agent behavior."""

    def save_agent_feedback(self, feedback: AgentFeedback) -> bool:
        """Persist one feedback event and return whether it changed."""
        ...

    def list_agent_feedback(
        self,
        *,
        market_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        """Load feedback events, optionally filtered by scope."""
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


class CompetitorRepository(Protocol):
    """Persistence boundary for monitored competitors."""

    def save_competitors(self, competitors: list[Competitor]) -> int:
        """Persist competitors and return the number saved."""
        ...

    def get_competitor(self, competitor_id: str) -> Competitor | None:
        """Load one competitor by id."""
        ...

    def list_competitors(self) -> list[Competitor]:
        """Load all persisted competitors."""
        ...


class MonitoredSourceRepository(Protocol):
    """Persistence boundary for competitor-linked monitored sources."""

    def save_monitored_sources(self, sources: list[MonitoredSource]) -> int:
        """Persist monitored sources and return the number saved."""
        ...

    def get_monitored_source(self, source_id: str) -> MonitoredSource | None:
        """Load one monitored source by id."""
        ...

    def update_monitored_source(self, source: MonitoredSource) -> bool:
        """Replace one monitored source and return whether it existed."""
        ...

    def list_monitored_sources(
        self,
        *,
        competitor_id: str | None = None,
        market_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        """Load monitored sources, optionally filtered by scope and enabled state."""
        ...
