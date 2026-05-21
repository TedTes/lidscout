"""Opportunity synthesis service."""
from collections import Counter
from dataclasses import dataclass

from application.ports import OpportunityRepository
from domain.cluster import SignalCluster
from domain.opportunity import Opportunity
from domain.signal import Signal
from shared.logger import get_logger, log_event


logger = get_logger(__name__)


@dataclass(frozen=True)
class OpportunitySynthesisResult:
    """Summary of one opportunity synthesis run."""

    synthesized_count: int
    inserted_count: int
    failed_count: int
    opportunities: list[Opportunity]


class OpportunitySynthesisService:
    """Synthesizes actionable product opportunities from pain clusters."""

    def __init__(
        self,
        repository: OpportunityRepository,
        *,
        minimum_average_score: float = 7.0,
    ):
        if not 0.0 <= minimum_average_score <= 10.0:
            raise ValueError("minimum_average_score must be between 0.0 and 10.0")
        self.repository = repository
        self.minimum_average_score = minimum_average_score

    def synthesize(
        self,
        clusters: list[SignalCluster],
        signals: list[Signal],
    ) -> OpportunitySynthesisResult:
        signal_index = {signal.id: signal for signal in signals}
        opportunities: list[Opportunity] = []
        failed_count = 0

        for cluster in clusters:
            if cluster.average_score < self.minimum_average_score:
                continue

            cluster_signals = [
                signal_index[signal_id]
                for signal_id in cluster.signal_ids
                if signal_id in signal_index
            ]
            if not cluster_signals:
                failed_count += 1
                continue

            try:
                opportunities.append(self._build_opportunity(cluster, cluster_signals))
            except ValueError:
                failed_count += 1

        inserted_count = self.repository.save_opportunities(opportunities)
        failed_count += len(opportunities) - inserted_count

        result = OpportunitySynthesisResult(
            synthesized_count=len(opportunities),
            inserted_count=inserted_count,
            failed_count=failed_count,
            opportunities=opportunities,
        )
        log_event(
            logger,
            "opportunity_synthesis_completed",
            synthesized_count=result.synthesized_count,
            inserted_count=result.inserted_count,
            failed_count=result.failed_count,
        )
        return result

    def _build_opportunity(
        self,
        cluster: SignalCluster,
        signals: list[Signal],
    ) -> Opportunity:
        target_user = _most_common(
            [signal.user_type for signal in signals if signal.user_type],
            fallback="affected users",
        )
        workaround = _most_common(
            [
                signal.current_workaround
                for signal in signals
                if signal.current_workaround
            ],
            fallback=None,
        )
        category = _most_common(
            [signal.category for signal in signals if signal.category],
            fallback=cluster.theme,
        )

        return Opportunity.create(
            id=f"opportunity-{cluster.id}",
            cluster_id=cluster.id,
            title=f"Reduce {cluster.theme.lower()} friction for {target_user}",
            target_user=target_user,
            pain_summary=_pain_summary(cluster, signals),
            why_it_matters=_why_it_matters(cluster, signals),
            suggested_wedge=_suggested_wedge(category, workaround),
            evidence_count=cluster.frequency,
            confidence=_confidence_for(cluster),
            evidence_signal_ids=[signal.id for signal in signals],
        )


def _most_common(values: list[str], *, fallback: str | None) -> str | None:
    if not values:
        return fallback
    return Counter(values).most_common(1)[0][0]


def _pain_summary(cluster: SignalCluster, signals: list[Signal]) -> str:
    if cluster.summary:
        return cluster.summary
    return signals[0].pain


def _why_it_matters(cluster: SignalCluster, signals: list[Signal]) -> str:
    willing_count = sum(
        1 for signal in signals if signal.willingness_to_pay is True
    )
    return (
        f"{cluster.frequency} evidence item(s) cluster around {cluster.theme} "
        f"with an average opportunity score of {cluster.average_score:.1f}. "
        f"{willing_count} signal(s) include willingness-to-pay evidence."
    )


def _suggested_wedge(category: str | None, workaround: str | None) -> str:
    if workaround:
        return (
            f"Build a focused {category.lower()} workflow that removes the "
            f"repeated workaround: {workaround}."
        )
    return f"Build a focused {category.lower()} workflow for this repeated pain."


def _confidence_for(cluster: SignalCluster) -> float:
    score_component = min(cluster.average_score / 10.0, 1.0) * 0.7
    frequency_component = min(cluster.frequency, 5) / 5 * 0.3
    return round(min(score_component + frequency_component, 1.0), 2)
