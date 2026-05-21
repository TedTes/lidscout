"""Persistence contracts for domain entities."""
from typing import Protocol

from domain.cluster import SignalCluster
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
