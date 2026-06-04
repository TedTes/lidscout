"""Derived source quality status labels."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from domain.niche import NicheSource, NicheSourceRunStats

from application.source_quality.scoring import source_observed_quality_score

SourceQualityStatusLabel = Literal[
    "productive",
    "noisy",
    "blocked",
    "untested",
    "stale",
]


@dataclass(frozen=True)
class SourceQualityStatus:
    """User-facing source quality classification."""

    label: SourceQualityStatusLabel
    reason: str
    score: float | None


def source_quality_status(
    source: NicheSource,
    stats: NicheSourceRunStats | None = None,
    *,
    now: datetime | None = None,
) -> SourceQualityStatus:
    """Classify a source into an actionable quality status."""
    score = (
        source_observed_quality_score(stats)
        if stats is not None
        else source.signal_quality_score
    )

    if source.requires_proxy or source.access_mode == "proxy_required":
        return SourceQualityStatus(
            label="blocked",
            reason="Requires proxy access before it can be scanned reliably.",
            score=score,
        )
    if source.requires_auth or source.access_mode == "api_auth":
        return SourceQualityStatus(
            label="blocked",
            reason="Requires authenticated access before it can be scanned.",
            score=score,
        )
    if source.health_status == "failing" or source.last_error:
        return SourceQualityStatus(
            label="blocked",
            reason=source.last_error or "Recent scans failed.",
            score=score,
        )
    if stats is not None and stats.consecutive_failures >= 3:
        return SourceQualityStatus(
            label="blocked",
            reason="Multiple consecutive scans failed.",
            score=score,
        )

    if _is_stale(source, stats, now=now):
        return SourceQualityStatus(
            label="stale",
            reason="Source has not been scanned recently.",
            score=score,
        )

    if stats is None and score is not None and score < 0.25 and source.last_scanned_at:
        return SourceQualityStatus(
            label="noisy",
            reason="Previous scans produced low-quality evidence.",
            score=score,
        )

    if stats is None or stats.total_runs == 0:
        return SourceQualityStatus(
            label="untested",
            reason="Source has not completed a scan yet.",
            score=score,
        )

    if _is_noisy(stats, score):
        return SourceQualityStatus(
            label="noisy",
            reason="Recent scans mostly produced filtered or irrelevant posts.",
            score=score,
        )

    if source.buyer_voice_verified or _is_productive(stats, score):
        return SourceQualityStatus(
            label="productive",
            reason="Source has produced relevant buyer evidence.",
            score=score,
        )

    return SourceQualityStatus(
        label="untested",
        reason="Source needs more scan history before it can be trusted.",
        score=score,
    )


def _is_stale(
    source: NicheSource,
    stats: NicheSourceRunStats | None,
    *,
    now: datetime | None,
) -> bool:
    scanned_at = (
        stats.last_scanned_at
        if stats is not None and stats.last_scanned_at is not None
        else source.last_scanned_at
    )
    if scanned_at is None:
        return False
    reference = now or datetime.now(tz=UTC)
    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=UTC)
    return reference - scanned_at > timedelta(days=14)


def _is_noisy(stats: NicheSourceRunStats, score: float | None) -> bool:
    if score is not None and stats.total_runs >= 2 and score < 0.25:
        return True
    return stats.success_count >= 2 and stats.relevant_posts_count == 0


def _is_productive(stats: NicheSourceRunStats, score: float | None) -> bool:
    if stats.relevant_posts_count >= 3 and stats.extracted_signals_count >= 1:
        return True
    return score is not None and score >= 0.65 and stats.relevant_posts_count >= 3
