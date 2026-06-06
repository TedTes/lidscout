"""Runtime source scan eligibility policy."""
from __future__ import annotations

from dataclasses import dataclass

from domain.niche import NicheSource, NicheSourceRunStats

from application.source_quality.scoring import source_observed_quality_score


MIN_REVIEWED_POSTS_FOR_NOISY_SOURCE = 10
MIN_RUNS_FOR_QUALITY_REJECTION = 2
MIN_OBSERVED_SCAN_QUALITY = 0.25
MAX_CONSECUTIVE_FAILURES = 3
LOW_SIGNAL_TIER_THRESHOLD = 5


@dataclass(frozen=True)
class SourceScanEligibility:
    """Whether a source should be fetched in the current pipeline run."""

    eligible: bool
    reason: str


def source_scan_eligibility(
    source: NicheSource,
    stats: NicheSourceRunStats | None = None,
    *,
    allow_proxy_sources: bool = False,
    allow_auth_sources: bool = False,
) -> SourceScanEligibility:
    """Return whether a niche source is safe and useful enough to scan.

    ``enabled`` means the source belongs to the niche's monitored source set.
    Eligibility is the stricter runtime decision: should this run spend time
    fetching the source right now?
    """
    if not source.enabled:
        return SourceScanEligibility(False, "Source is disabled.")

    if source.health_status == "paused":
        return SourceScanEligibility(False, "Source is paused.")

    if source.requires_proxy or source.access_mode == "proxy_required":
        if not allow_proxy_sources:
            return SourceScanEligibility(
                False,
                "Source requires proxy access.",
            )

    if source.requires_auth or source.access_mode == "api_auth":
        if not allow_auth_sources:
            return SourceScanEligibility(
                False,
                "Source requires authenticated access.",
            )

    if _is_unverified_low_signal_source(source, stats):
        return SourceScanEligibility(
            False,
            "Low-signal source has not produced buyer evidence.",
        )

    if stats is not None and stats.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        return SourceScanEligibility(
            False,
            "Source has repeated consecutive fetch failures.",
        )

    if stats is None and source.health_status == "failing" and source.last_error:
        return SourceScanEligibility(False, "Source has a previous fetch error.")

    if stats is not None and _has_enough_history(stats):
        observed_score = source_observed_quality_score(stats)
        if observed_score < MIN_OBSERVED_SCAN_QUALITY:
            return SourceScanEligibility(
                False,
                "Source has low observed signal quality.",
            )
        if stats.success_count >= MIN_RUNS_FOR_QUALITY_REJECTION and stats.relevant_posts_count == 0:
            return SourceScanEligibility(
                False,
                "Source has repeatedly produced no relevant posts.",
            )

    return SourceScanEligibility(True, "Source is eligible for scanning.")


def _has_enough_history(stats: NicheSourceRunStats) -> bool:
    reviewed_count = (
        stats.relevant_posts_count
        + stats.rule_filtered_count
        + stats.llm_filtered_count
        + stats.relevance_failed_count
    )
    return (
        stats.total_runs >= MIN_RUNS_FOR_QUALITY_REJECTION
        and reviewed_count >= MIN_REVIEWED_POSTS_FOR_NOISY_SOURCE
    )


def _is_unverified_low_signal_source(
    source: NicheSource,
    stats: NicheSourceRunStats | None,
) -> bool:
    if source.buyer_voice_verified:
        return False
    if source.tier is None or source.tier < LOW_SIGNAL_TIER_THRESHOLD:
        return False
    if stats is not None and stats.relevant_posts_count > 0:
        return False
    return True
