"""Persistence contracts for domain entities."""
from typing import Protocol

from domain.cluster import SignalCluster
from domain.competitor import Competitor
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
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        """Load monitored sources, optionally filtered by competitor and enabled state."""
        ...
