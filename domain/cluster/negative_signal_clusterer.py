"""Cluster negative interactions into recurring signal themes."""
from collections import defaultdict
from typing import Iterable, Protocol

from domain.cluster.models import SignalCluster
from domain.score.severity import severity_for_frequency


class ClusterableInteraction(Protocol):
    """Interaction fields needed by the domain clusterer."""

    interaction_id: str
    body: str
    topics: list[str]


class NegativeSignalClusterer:
    """Groups negative public interactions by detected topic."""

    def cluster(self, interactions: Iterable[ClusterableInteraction]) -> list[SignalCluster]:
        buckets: dict[str, list[ClusterableInteraction]] = defaultdict(list)

        for interaction in interactions:
            for topic in interaction.topics or ["unclassified negative feedback"]:
                buckets[topic].append(interaction)

        clusters = [
            SignalCluster(
                theme=theme,
                frequency=len(clustered),
                severity=severity_for_frequency(len(clustered)),
                interaction_ids=[
                    interaction.interaction_id for interaction in clustered[:10]
                ],
                excerpts=[interaction.body for interaction in clustered[:5]],
            )
            for theme, clustered in buckets.items()
        ]

        return sorted(clusters, key=lambda cluster: cluster.frequency, reverse=True)
