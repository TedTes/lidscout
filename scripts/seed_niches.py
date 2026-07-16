"""Idempotent watchlist seeding script.

Usage:
    python -m scripts.seed_niches
    python scripts/seed_niches.py

Reads NICHE_SEEDS from application/onboarding/niche_seeds.py and inserts
watchlist templates, companies, sources, and template-source bindings into
Postgres. Re-running is safe.

All niche definitions live here in version-controlled code.
The Supabase console is for inspection only.
"""
from __future__ import annotations

import sys
import os

# Allow running as a script from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.onboarding.niche_seeds import NICHE_SEEDS
from domain.niche import Niche, NicheCompany, TemplateSourceBinding
from domain.source import Source
from infrastructure.db import (
    PostgresNicheCompanyRepository,
    PostgresNicheRepository,
    PostgresSourceRepository,
    PostgresTemplateSourceBindingRepository,
    connect_postgres,
)
from shared.config import get_app_config


def seed(database_url: str) -> dict[str, int]:
    connection = connect_postgres(database_url)
    niche_repo = PostgresNicheRepository(connection=connection)
    company_repo = PostgresNicheCompanyRepository(connection=connection)
    source_repo = PostgresSourceRepository(connection=connection)
    template_source_repo = PostgresTemplateSourceBindingRepository(
        connection=connection
    )

    existing_by_job = {
        n.job.lower().strip(): n
        for n in niche_repo.list_niches(is_custom=False)
    }

    niches_inserted = 0
    companies_inserted = 0
    sources_inserted = 0
    template_sources_inserted = 0
    skipped = 0

    for seed_entry in NICHE_SEEDS:
        job = seed_entry["job"].strip()
        niche = existing_by_job.get(job.lower())
        if niche is not None:
            skipped += 1
        else:
            has_sources = bool(seed_entry.get("sources"))
            status = "sourced" if has_sources else "defined"

            niche = Niche.create(
                job=job,
                buyer=seed_entry["buyer"],
                category=seed_entry["category"],
                status=status,
            )
            niche_repo.save_niches([niche])
            niches_inserted += 1
            existing_by_job[job.lower()] = niche

        existing_companies = {
            company.name.lower().strip()
            for company in company_repo.list_niche_companies(niche.id)
        }
        for tool in seed_entry.get("tools", []):
            if tool["name"].lower().strip() in existing_companies:
                continue
            company = NicheCompany.create(
                niche_id=niche.id,
                name=tool["name"],
                website=tool.get("website"),
            )
            companies_inserted += company_repo.save_niche_companies([company])
            existing_companies.add(company.name.lower().strip())

        for source_entry in seed_entry.get("sources", []):
            source = Source.create(
                locator=source_entry["locator"],
                source_type=source_entry["source_type"],
                source_family=source_entry["source_family"],
                is_gate_free=bool(source_entry.get("is_gate_free", False)),
                access_mode=source_entry.get("access_mode", "unknown"),
                requires_proxy=bool(source_entry.get("requires_proxy", False)),
                requires_auth=bool(source_entry.get("requires_auth", False)),
            )
            sources_inserted += source_repo.save_sources([source])
            persisted_source = source_repo.get_source_by_identity(
                source.source_type,
                source.locator,
            )
            if persisted_source is None:
                continue
            binding = TemplateSourceBinding.create(
                template_niche_id=niche.id,
                source_id=persisted_source.id,
                default_enabled=bool(source_entry.get("enabled", True)),
                default_limit=source_entry.get("limit_value"),
                default_scan_frequency=source_entry.get("scan_frequency"),
                default_buyer_voice_verified=bool(
                    source_entry.get("buyer_voice_verified", False)
                ),
                default_options=source_entry.get("options") or {},
                tier=source_entry.get("tier"),
                signal_quality_score=source_entry.get("signal_quality_score"),
                recommended_cadence=source_entry.get("recommended_cadence", "daily"),
            )
            template_sources_inserted += (
                template_source_repo.save_template_source_bindings([binding])
            )

    return {
        "inserted": niches_inserted,
        "skipped": skipped,
        "companies_inserted": companies_inserted,
        "sources_inserted": sources_inserted,
        "template_sources_inserted": template_sources_inserted,
    }


if __name__ == "__main__":
    import json
    config = get_app_config()
    result = seed(config.DATABASE_URL)
    print(json.dumps(result, indent=2))
