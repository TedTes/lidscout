"""Niche seed definitions — version-controlled, never hand-entered in Supabase.

Format for each seed entry:
{
    "job":      str,            # job-to-be-done, phrased as an outcome
    "buyer":    str,            # who has this job
    "category": str,            # broad grouping (devtools, no_code, vertical_saas, ...)
    "tools": [                  # competing tools for this job
        {
            "name":    str,
            "website": str | None,
        }
    ],
    "sources": [                # OPTIONAL — a niche can be seeded with zero sources
        {
            "locator":       str,
            "source_type":   str,
            "source_family": str,
            "is_gate_free":  bool,
        }
    ],
}

A niche seeded with no sources starts in 'defined' status.
A niche seeded with sources starts in 'sourced' status.

The real niche list will be provided separately. This file contains
one placeholder example to validate the schema and seeding pipeline.
"""
from __future__ import annotations

NICHE_SEEDS: list[dict] = [
    # ── Placeholder example — replace with real niche definitions ────────────
    {
        "job": "build a web app without writing code",
        "buyer": "non-technical founders and product managers",
        "category": "no_code",
        "tools": [
            {"name": "Webflow", "website": "https://webflow.com"},
            {"name": "Bubble", "website": "https://bubble.io"},
        ],
        "sources": [],  # no sources yet — status will be 'defined'
    },
]
