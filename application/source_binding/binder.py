"""Source-binding job — binds candidate sources to a niche deterministically.

This job does NOT activate monitoring. It only generates and inserts candidate
NicheSource rows. A separate verification step (manual or future automated job)
sets buyer_voice_verified=True and promotes the niche status from 'defined'
to 'sourced'.
"""
from __future__ import annotations

import logging
from typing import Any

from application.source_binding.templates import CandidateSource, generate_company_sources
from domain.niche import NicheCompany, NicheSource
from shared.logger import get_logger, log_event

logger = get_logger(__name__)


def bind_sources_for_niche(
    niche_id: str,
    niche_company_repo: Any,
    niche_source_repo: Any,
) -> int:
    """Generate and insert candidate sources for all companies in a niche.

    Idempotent — the unique index on (niche_id, locator) in niche_sources
    prevents duplicates. Returns the number of newly inserted sources.
    """
    companies: list[NicheCompany] = niche_company_repo.list_niche_companies(niche_id)
    if not companies:
        log_event(logger, "source_binding_skipped", niche_id=niche_id, reason="no_companies")
        return 0

    sources: list[NicheSource] = []
    for company in companies:
        candidates = _candidates_for_company(company)
        for candidate in candidates:
            sources.append(
                NicheSource.create(
                    niche_id=niche_id,
                    company_id=company.id,
                    locator=candidate.locator,
                    source_type=candidate.source_type,
                    source_family=candidate.source_family,
                    is_gate_free=candidate.is_gate_free,
                )
            )

    inserted = niche_source_repo.save_niche_sources(sources)
    log_event(
        logger,
        "sources_bound",
        niche_id=niche_id,
        company_count=len(companies),
        candidate_count=len(sources),
        inserted_count=inserted,
    )
    return inserted


def bind_sources_all(
    niche_repo: Any,
    niche_company_repo: Any,
    niche_source_repo: Any,
) -> dict[str, int]:
    """Bind sources for all niches in 'defined' status.

    Returns a summary dict with total niches processed and sources inserted.
    """
    niches = niche_repo.list_niches(status="defined")
    total_inserted = 0
    for niche in niches:
        total_inserted += bind_sources_for_niche(
            niche.id, niche_company_repo, niche_source_repo
        )

    log_event(
        logger,
        "source_binding_batch_complete",
        level=logging.INFO,
        niche_count=len(niches),
        total_inserted=total_inserted,
    )
    return {"niche_count": len(niches), "total_inserted": total_inserted}


def _candidates_for_company(company: NicheCompany) -> list[CandidateSource]:
    """Extract source metadata from a NicheCompany and generate candidates.

    NicheCompany only has name and website for now — additional metadata
    (github_repo, subreddit, g2_slug, etc.) can be added to the model later
    as source coverage improves.
    """
    return generate_company_sources(company.name)
