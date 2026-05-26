"""Proactive alert generation for niche research agents."""
from domain.agent import AgentAlert
from domain.cluster import SignalCluster
from domain.opportunity import Opportunity


def generate_threshold_alerts(
    *,
    market_id: str,
    clusters: list[SignalCluster],
    opportunities: list[Opportunity],
    theme_score_threshold: float = 8.0,
    theme_frequency_threshold: int = 5,
    gap_confidence_threshold: float = 0.75,
) -> list[AgentAlert]:
    """Create deterministic alerts for threshold-crossing themes and gaps."""
    alerts: list[AgentAlert] = []
    for cluster in clusters:
        if (
            cluster.average_score < theme_score_threshold
            and cluster.frequency < theme_frequency_threshold
        ):
            continue
        alerts.append(
            AgentAlert.create(
                id=f"agent-alert-{market_id}-theme-{cluster.id}",
                market_id=market_id,
                alert_type="theme_threshold",
                title=f"{cluster.theme} crossed a signal threshold",
                severity="warning" if cluster.average_score >= theme_score_threshold else "info",
                detail=(
                    f"{cluster.frequency} finding(s), average score "
                    f"{cluster.average_score:.1f}."
                ),
                metadata={
                    "cluster_id": cluster.id,
                    "theme": cluster.theme,
                    "frequency": cluster.frequency,
                    "average_score": cluster.average_score,
                },
            )
        )

    for opportunity in opportunities:
        if opportunity.confidence < gap_confidence_threshold:
            continue
        alerts.append(
            AgentAlert.create(
                id=f"agent-alert-{market_id}-gap-{opportunity.id}",
                market_id=market_id,
                alert_type="gap_threshold",
                title=f"High-confidence gap: {opportunity.title}",
                severity="warning",
                detail=(
                    f"Confidence {opportunity.confidence:.2f} from "
                    f"{opportunity.evidence_count} evidence item(s)."
                ),
                metadata={
                    "opportunity_id": opportunity.id,
                    "cluster_id": opportunity.cluster_id,
                    "confidence": opportunity.confidence,
                    "evidence_count": opportunity.evidence_count,
                },
            )
        )
    return alerts
