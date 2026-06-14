"""Idempotent niche seeding script.

Usage:
    python -m scripts.seed_niches
    python scripts/seed_niches.py

Reads NICHE_SEEDS from application/onboarding/niche_seeds.py and inserts
niches, companies, and sources into Postgres. Re-running is safe — existing
niches (matched by lowercased job text) are skipped.

All niche definitions live here in version-controlled code.
The Supabase console is for inspection only.
"""
from __future__ import annotations

import sys
import os

# Allow running as a script from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.onboarding.niche_seeds import NICHE_SEEDS
from domain.niche import Niche, NicheCompany
from infrastructure.db import (
    PostgresNicheCompanyRepository,
    PostgresNicheRepository,
    connect_postgres,
)
from shared.config import get_app_config


def seed(database_url: str) -> dict[str, int]:
    connection = connect_postgres(database_url)
    niche_repo = PostgresNicheRepository(connection=connection)
    company_repo = PostgresNicheCompanyRepository(connection=connection)

    existing = {n.job.lower().strip() for n in niche_repo.list_niches()}

    niches_inserted = 0
    companies_inserted = 0
    skipped = 0

    for seed_entry in NICHE_SEEDS:
        job = seed_entry["job"].strip()
        if job.lower() in existing:
            skipped += 1
            continue

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
        existing.add(job.lower())

        for tool in seed_entry.get("tools", []):
            company = NicheCompany.create(
                niche_id=niche.id,
                name=tool["name"],
                website=tool.get("website"),
            )
            companies_inserted += company_repo.save_niche_companies([company])

        # Sources are now seeded via template_sources / PostgresTemplateSourceBindingRepository.
        # NicheSource persistence was removed in the catalog migration.

    return {
        "inserted": niches_inserted,
        "skipped": skipped,
        "companies_inserted": companies_inserted,
    }


if __name__ == "__main__":
    import json
    config = get_app_config()
    result = seed(config.DATABASE_URL)
    print(json.dumps(result, indent=2))
