"""Signal clustering service."""
from dataclasses import dataclass
import math

from domain.cluster import SignalCluster
from domain.score import calculate_opportunity_score
from domain.signal import Signal
from shared.logger import get_logger, log_event

SignalEmbeddings = dict[str, list[float]]
logger = get_logger(__name__)


@dataclass
class _ClusterBucket:
    signals: list[Signal]
    embeddings: list[list[float]]

    def add(self, signal: Signal, embedding: list[float]) -> None:
        self.signals.append(signal)
        self.embeddings.append(embedding)

    @property
    def centroid(self) -> list[float]:
        dimensions = len(self.embeddings[0])
        return [
            sum(embedding[index] for embedding in self.embeddings) / len(self.embeddings)
            for index in range(dimensions)
        ]


class ClusteringService:
    """Groups semantically similar signals using cosine similarity."""

    def __init__(self, similarity_threshold: float = 0.82):
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        self.similarity_threshold = similarity_threshold

    def cluster(
        self,
        signals: list[Signal],
        embeddings: SignalEmbeddings,
    ) -> list[SignalCluster]:
        buckets: list[_ClusterBucket] = []

        for signal in signals:
            embedding = self._embedding_for_signal(signal, embeddings)
            matching_bucket = self._find_matching_bucket(embedding, buckets)

            if matching_bucket is None:
                buckets.append(_ClusterBucket(signals=[signal], embeddings=[embedding]))
            else:
                matching_bucket.add(signal, embedding)

        clusters = [
            self._build_cluster(bucket=bucket, index=index)
            for index, bucket in enumerate(buckets, start=1)
        ]
        log_event(
            logger,
            "clustering_completed",
            signal_count=len(signals),
            clustered_count=len(clusters),
            similarity_threshold=self.similarity_threshold,
        )
        return clusters

    def _find_matching_bucket(
        self,
        embedding: list[float],
        buckets: list[_ClusterBucket],
    ) -> _ClusterBucket | None:
        for bucket in buckets:
            if _cosine_similarity(embedding, bucket.centroid) >= self.similarity_threshold:
                return bucket
        return None

    def _build_cluster(self, bucket: _ClusterBucket, index: int) -> SignalCluster:
        signals = bucket.signals
        top_examples = [signal.pain for signal in signals[:3]]
        theme = self._theme_for(signals)
        average_score = sum(calculate_opportunity_score(signal) for signal in signals) / len(signals)

        return SignalCluster.create(
            id=f"cluster-{index}",
            theme=theme,
            summary=f"{len(signals)} signal(s) related to {theme}",
            signal_ids=[signal.id for signal in signals],
            frequency=len(signals),
            average_score=average_score,
            top_examples=top_examples,
        )

    @staticmethod
    def _theme_for(signals: list[Signal]) -> str:
        categories = [signal.category for signal in signals if signal.category]
        if categories:
            return max(categories, key=categories.count)
        return signals[0].pain

    @staticmethod
    def _embedding_for_signal(
        signal: Signal,
        embeddings: SignalEmbeddings,
    ) -> list[float]:
        if signal.id not in embeddings:
            raise ValueError(f"missing embedding for signal {signal.id}")

        embedding = [float(value) for value in embeddings[signal.id]]
        if not embedding:
            raise ValueError(f"embedding for signal {signal.id} must not be empty")
        return embedding


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embeddings must have matching dimensions")

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    return dot_product / (left_norm * right_norm)
