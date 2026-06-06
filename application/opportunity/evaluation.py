"""Offline QA helpers for opportunity qualification thresholds."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from application.opportunity.service import (
    ClusterQualification,
    OpportunitySynthesisContext,
    qualify_cluster_for_opportunity,
)
from domain.cluster import SignalCluster
from domain.signal import Signal


@dataclass(frozen=True)
class OpportunityQualificationReport:
    """Summary of how current thresholds treat candidate themes."""

    evaluated_cluster_count: int
    qualified_count: int
    rejected_count: int
    skipped_low_score_count: int
    missing_signal_count: int
    rejection_reasons: dict[str, int]
    qualifications: list[ClusterQualification]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluated_cluster_count": self.evaluated_cluster_count,
            "qualified_count": self.qualified_count,
            "rejected_count": self.rejected_count,
            "skipped_low_score_count": self.skipped_low_score_count,
            "missing_signal_count": self.missing_signal_count,
            "rejection_reasons": dict(self.rejection_reasons),
            "qualifications": [
                {
                    "cluster_id": item.cluster_id,
                    "qualified": item.qualified,
                    "reason": item.reason,
                    "finding_count": item.finding_count,
                    "source_count": item.source_count,
                    "company_count": item.company_count,
                    "general_finding_count": item.general_finding_count,
                    "high_signal_source_count": item.high_signal_source_count,
                    "buyer_context_signal_count": item.buyer_context_signal_count,
                    "strong_pain_signal_count": item.strong_pain_signal_count,
                    "average_signal_confidence": item.average_signal_confidence,
                }
                for item in self.qualifications
            ],
        }


def evaluate_opportunity_qualification(
    clusters: list[SignalCluster],
    signals: list[Signal],
    *,
    context: OpportunitySynthesisContext | None = None,
    minimum_average_score: float = 7.0,
) -> OpportunityQualificationReport:
    """Evaluate candidate themes with production opportunity thresholds."""
    signal_index = {signal.id: signal for signal in signals}
    skipped_low_score_count = 0
    missing_signal_count = 0
    qualifications: list[ClusterQualification] = []

    for cluster in clusters:
        if cluster.average_score < minimum_average_score:
            skipped_low_score_count += 1
            continue

        cluster_signals = [
            signal_index[signal_id]
            for signal_id in cluster.signal_ids
            if signal_id in signal_index
        ]
        if not cluster_signals:
            missing_signal_count += 1
            continue

        qualifications.append(
            qualify_cluster_for_opportunity(cluster, cluster_signals, context),
        )

    rejection_reasons = Counter(
        item.reason or "qualified"
        for item in qualifications
        if not item.qualified
    )
    qualified_count = sum(1 for item in qualifications if item.qualified)
    rejected_count = len(qualifications) - qualified_count

    return OpportunityQualificationReport(
        evaluated_cluster_count=len(qualifications),
        qualified_count=qualified_count,
        rejected_count=rejected_count,
        skipped_low_score_count=skipped_low_score_count,
        missing_signal_count=missing_signal_count,
        rejection_reasons=dict(rejection_reasons),
        qualifications=qualifications,
    )
