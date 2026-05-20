"""In-memory repository implementations for domain entities."""
from dataclasses import dataclass, field

from application.ports import (
    ClusterRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
)
from domain.cluster import SignalCluster
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal


@dataclass
class InMemoryPostRepository(PostRepository):
    """In-memory raw post repository."""

    posts: dict[str, RawPost] = field(default_factory=dict)

    def save_posts(self, posts: list[RawPost]) -> int:
        inserted_count = 0
        for post in posts:
            if post.id in self.posts:
                continue
            self.posts[post.id] = post
            inserted_count += 1
        return inserted_count


@dataclass
class InMemorySignalRepository(SignalRepository):
    """In-memory signal repository."""

    signals: dict[str, Signal] = field(default_factory=dict)

    def save_signals(self, signals: list[Signal]) -> int:
        inserted_count = 0
        for signal in signals:
            if signal.id in self.signals:
                continue
            self.signals[signal.id] = signal
            inserted_count += 1
        return inserted_count


@dataclass
class InMemoryScoreRepository(ScoreRepository):
    """In-memory opportunity score repository."""

    scores: dict[str, OpportunityScore] = field(default_factory=dict)

    def save_scores(self, scores: list[OpportunityScore]) -> int:
        inserted_count = 0
        for score in scores:
            if score.signal_id in self.scores:
                continue
            self.scores[score.signal_id] = score
            inserted_count += 1
        return inserted_count


@dataclass
class InMemoryClusterRepository(ClusterRepository):
    """In-memory signal cluster repository."""

    clusters: dict[str, SignalCluster] = field(default_factory=dict)

    def save_clusters(self, clusters: list[SignalCluster]) -> int:
        inserted_count = 0
        for cluster in clusters:
            if cluster.id in self.clusters:
                continue
            self.clusters[cluster.id] = cluster
            inserted_count += 1
        return inserted_count
