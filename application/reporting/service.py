"""Market signal reporting service."""
from dataclasses import dataclass
from datetime import UTC, datetime

from domain.cluster import SignalCluster
from domain.opportunity import Opportunity


@dataclass(frozen=True)
class MarketSignalReport:
    """Ranked report generated from clustered market signals."""

    title: str
    generated_at: datetime
    top_clusters: list[SignalCluster]
    emerging_pains: list[str]
    recommended_opportunities: list[Opportunity]


class ReportingService:
    """Ranks signal clusters and produces a market signal report."""

    def __init__(
        self,
        *,
        title: str = "LidScout Market Signal Report",
        top_cluster_limit: int = 5,
        opportunity_threshold: float = 7.0,
    ):
        if top_cluster_limit < 1:
            raise ValueError("top_cluster_limit must be at least 1")
        if not 0.0 <= opportunity_threshold <= 10.0:
            raise ValueError("opportunity_threshold must be between 0.0 and 10.0")

        self.title = title
        self.top_cluster_limit = top_cluster_limit
        self.opportunity_threshold = opportunity_threshold

    def generate(
        self,
        clusters: list[SignalCluster],
        opportunities: list[Opportunity] | None = None,
    ) -> MarketSignalReport:
        ranked_clusters = self._rank_clusters(clusters)
        top_clusters = ranked_clusters[: self.top_cluster_limit]
        ranked_opportunities = self._rank_opportunities(opportunities or [])

        return MarketSignalReport(
            title=self.title,
            generated_at=datetime.now(UTC),
            top_clusters=top_clusters,
            emerging_pains=[cluster.summary for cluster in top_clusters],
            recommended_opportunities=ranked_opportunities[: self.top_cluster_limit],
        )

    @staticmethod
    def _rank_clusters(clusters: list[SignalCluster]) -> list[SignalCluster]:
        return sorted(
            clusters,
            key=lambda cluster: (
                cluster.average_score,
                cluster.frequency,
                cluster.theme.lower(),
            ),
            reverse=True,
        )

    @staticmethod
    def _rank_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
        return sorted(
            opportunities,
            key=lambda opportunity: (
                opportunity.confidence,
                opportunity.evidence_count,
                opportunity.title.lower(),
            ),
            reverse=True,
        )
