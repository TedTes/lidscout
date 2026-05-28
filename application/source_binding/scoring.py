"""Niche status lifecycle and monitorability scoring.

monitorability_score is grounded in verifiable source facts:
  - count of buyer_voice_verified sources
  - count of is_gate_free sources
  - number of distinct source families
  - whether any source is currently active (health_status='active')

opportunity_score is always computed from synthesised gaps after monitoring
produces findings. It is NEVER assigned here or at seed time.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from domain.niche import Niche, NicheSource
from shared.logger import get_logger, log_event

logger = get_logger(__name__)

# Minimum verified gate-free sources before a niche can become 'sourced'.
_MIN_VERIFIED_GATE_FREE = 1


def compute_monitorability_score(sources: list[NicheSource]) -> float:
    """Return a 0-1 monitorability score from a niche's bound sources.

    Formula (all components normalised to 0-1, then averaged):
      - verified_ratio:    verified / total sources (0 if no sources)
      - gate_free_ratio:   gate-free / total sources
      - family_diversity:  distinct families / 4 (capped at 1.0;
                           4 families = social, technical_forum, reviews, owned)
      - has_active:        1.0 if any source has health_status='active', else 0.0

    Returns 0.0 when there are no sources.
    """
    if not sources:
        return 0.0

    total = len(sources)
    verified = sum(1 for s in sources if s.buyer_voice_verified)
    gate_free = sum(1 for s in sources if s.is_gate_free)
    families = len({s.source_family for s in sources})
    has_active = any(s.health_status == "active" for s in sources)

    verified_ratio = verified / total
    gate_free_ratio = gate_free / total
    family_diversity = min(families / 4, 1.0)
    active_component = 1.0 if has_active else 0.0

    return round((verified_ratio + gate_free_ratio + family_diversity + active_component) / 4, 4)


def resolve_niche_status(sources: list[NicheSource], current_status: str) -> str:
    """Return the correct status given current bound sources.

    Transitions:
      defined  → sourced  when there is at least one verified gate-free source
      sourced  → active   only via explicit operator/user activation (not here)
      active   stays active regardless of source changes

    A niche can move back from 'sourced' to 'defined' if verified sources drop
    below the threshold (e.g. after source deletion).
    """
    if current_status == "active":
        return "active"

    verified_gate_free = sum(
        1 for s in sources if s.buyer_voice_verified and s.is_gate_free
    )
    if verified_gate_free >= _MIN_VERIFIED_GATE_FREE:
        return "sourced"
    return "defined"


def refresh_niche_scores(
    niche: Niche,
    niche_source_repo: Any,
    niche_repo: Any,
) -> Niche:
    """Recompute monitorability_score and status for a niche and persist.

    Does not touch opportunity_score — that is computed from gaps elsewhere.
    Returns the updated Niche.
    """
    from domain.niche.models import Niche as _Niche

    sources = niche_source_repo.list_niche_sources(niche.id)
    score = compute_monitorability_score(sources)
    status = resolve_niche_status(sources, niche.status)

    updated = _Niche(
        id=niche.id,
        job=niche.job,
        buyer=niche.buyer,
        category=niche.category,
        description=niche.description,
        status=status,
        monitorability_score=score,
        opportunity_score=niche.opportunity_score,
        created_at=niche.created_at,
        updated_at=datetime.now(tz=UTC),
    )
    niche_repo.update_niche(updated)
    log_event(
        logger,
        "niche_scores_refreshed",
        niche_id=niche.id,
        monitorability_score=score,
        status=status,
    )
    return updated
