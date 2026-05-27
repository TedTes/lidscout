"""Template market seeding for new users.

On first login, 3 starter niches from ALL_TEMPLATES are seeded automatically.
Full template library is available in niche_templates.py.

Seeding is:
  - Idempotent  — skipped entirely if the user already has any markets.
  - Transactional — all inserts (market + competitors + sources + prefs) are
    wrapped in a single database transaction. If any insert fails, nothing is
    written and no activity event is recorded.
  - One-template-per-user — duplicate seeding of the same template is
    prevented by the idempotency check.

Template data is COPIED at seeding time; changes to niche_templates.py never
mutate already-seeded user niches.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from application.onboarding.niche_templates import (
    NicheTemplate,
    TemplateCompany,
    TemplateSource,
    get_template,
)
from shared.logger import get_logger, log_event

logger = get_logger(__name__)

DEFAULT_TEMPLATE_IDS = (
    "ai-coding-tools",
    "nocode-lowcode-tools",
    "ai-writing-tools",
)


def apply_template(
    user_id: str,
    template_id: str,
    market_repo: Any,
    competitor_repo: Any,
    source_repo: Any,
    activity_repo: Any | None = None,
) -> dict[str, Any] | None:
    """Apply one template as a new market for an existing user.

    Returns summary info, or None if the template was already applied for this user.
    Does NOT skip when the user already has other markets — only prevents re-seeding
    the same template twice (idempotency by template_id).
    """
    template = get_template(template_id)
    if template is None:
        return None

    existing = market_repo.list_markets(user_id=user_id)
    if any(getattr(m, "template_id", None) == template_id for m in existing):
        return None  # already has this template

    connection = market_repo.connection
    with connection.transaction():
        info = _insert_template(connection, user_id, template)

    if activity_repo is not None:
        _write_initialization_activity(activity_repo, info)

    return info


def seed_template_markets(
    user_id: str,
    market_repo: Any,
    competitor_repo: Any,
    source_repo: Any,
    activity_repo: Any | None = None,
) -> None:
    """Seed default template niches for a new user.

    All writes for each template are committed atomically. The activity event
    fires only after the transaction commits successfully.
    Skipped entirely if the user already has any markets.
    """
    # Idempotency check — outside the transaction so we don't hold a lock
    existing = market_repo.list_markets(user_id=user_id)
    if existing:
        return

    # All repos share one connection — access it once
    connection = market_repo.connection
    seeded: list[dict[str, Any]] = []

    for template_id in DEFAULT_TEMPLATE_IDS:
        template = get_template(template_id)
        if template is None:
            continue

        # Each template is its own atomic transaction. A failure on one
        # template does not prevent the others from being seeded.
        try:
            with connection.transaction():
                info = _insert_template(connection, user_id, template)
            seeded.append(info)
        except Exception as exc:
            # Continue seeding other templates, but keep enough signal to debug
            # broken template data or database constraints in production.
            log_event(
                logger,
                "template_seed_failed",
                level=logging.ERROR,
                user_id=user_id,
                template_id=template_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )

    # Activity events fire only after each transaction commits successfully.
    if activity_repo is not None:
        for info in seeded:
            _write_initialization_activity(activity_repo, info)


# ── Transactional insert helpers ──────────────────────────────────────────────

def _insert_template(
    connection: Any,
    user_id: str,
    template: NicheTemplate,
) -> dict[str, Any]:
    """Insert one template's market, competitors, sources, and prefs.

    Must be called inside connection.transaction(). Does NOT commit.
    Returns summary info used to write the post-commit activity event.
    """
    market_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # Market
    connection.execute(
        """
        INSERT INTO markets (
            id, name, description, target_user, idea_prompt,
            user_id, template_id, created_at, inserted_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (
            market_id,
            template.name,
            template.description,
            template.target_user,
            template.idea_prompt,
            user_id,
            template.id,
            now, now, now,
        ),
    )

    # Competitors
    source_families: set[str] = set()
    company_names: list[str] = []
    source_count = 0

    for company in template.companies:
        comp_id = str(uuid.uuid4())
        connection.execute(
            """
            INSERT INTO competitors (
                id, name, website, category, description, market_id, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (comp_id, company.name, company.website, company.category, None, market_id, now),
        )
        company_names.append(company.name)

        # Per-company sources
        for src in _build_company_sources(comp_id, market_id, company):
            _insert_source(connection, src)
            source_families.add(src["source_family"])
            source_count += 1

    # Market-level sources
    for tmpl_src in template.market_sources:
        _insert_market_source(connection, market_id, tmpl_src)
        source_families.add(tmpl_src.source_family)
        source_count += 1

    # Agent preferences (research brief)
    connection.execute(
        """
        INSERT INTO agent_preferences (
            market_id, preferred_source_families, ignored_themes,
            ignored_categories, muted_source_ids, extra_instructions,
            created_at, updated_at
        ) VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
        ON CONFLICT (market_id) DO NOTHING
        """,
        (
            market_id,
            json.dumps([]),
            json.dumps([]),
            json.dumps([]),
            json.dumps([]),
            template.extra_instructions,
            now, now,
        ),
    )

    return {
        "market_id": market_id,
        "template_name": template.name,
        "company_names": company_names,
        "source_count": source_count,
        "source_families": sorted(source_families),
    }


def _insert_source(connection: Any, src: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO monitored_sources (
            id, competitor_id, market_id, locator, source_type, enabled,
            limit_value, scan_frequency, last_scanned_at, last_error, options
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (id) DO NOTHING
        """,
        (
            src["id"],
            src["competitor_id"],
            src["market_id"],
            src["locator"],
            src["source_type"],
            True,
            src["limit"],
            None,
            None,
            None,
            json.dumps(src["options"]),
        ),
    )


def _insert_market_source(
    connection: Any,
    market_id: str,
    src: TemplateSource,
) -> None:
    connection.execute(
        """
        INSERT INTO monitored_sources (
            id, competitor_id, market_id, locator, source_type, enabled,
            limit_value, scan_frequency, last_scanned_at, last_error, options
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (id) DO NOTHING
        """,
        (
            str(uuid.uuid4()),
            None,
            market_id,
            src.locator,
            src.source_type,
            True,
            src.limit,
            None,
            None,
            None,
            json.dumps({**src.options, "source_family": src.source_family}),
        ),
    )


def _build_company_sources(
    competitor_id: str,
    market_id: str,
    company: TemplateCompany,
) -> list[dict[str, Any]]:
    sources = []
    query = company.name.replace(" ", "+")

    sources.append({
        "id": str(uuid.uuid4()),
        "competitor_id": competitor_id,
        "market_id": market_id,
        "locator": f"https://www.reddit.com/search.json?q={query}&sort=new&limit=25",
        "source_type": "reddit_search",
        "source_family": "social",
        "limit": 25,
        "options": {"adapter": "json", "source_family": "social"},
    })

    if company.subreddit:
        sources.append({
            "id": str(uuid.uuid4()),
            "competitor_id": competitor_id,
            "market_id": market_id,
            "locator": f"https://www.reddit.com/r/{company.subreddit}/new.json?limit=25",
            "source_type": "reddit_subreddit",
            "source_family": "social",
            "limit": 25,
            "options": {"adapter": "json", "source_family": "social"},
        })

    if company.g2_slug:
        sources.append({
            "id": str(uuid.uuid4()),
            "competitor_id": competitor_id,
            "market_id": market_id,
            "locator": f"https://www.g2.com/products/{company.g2_slug}/reviews",
            "source_type": "review_page",
            "source_family": "reviews",
            "limit": 10,
            "options": {"adapter": "static", "source_family": "reviews"},
        })

    sources.append({
        "id": str(uuid.uuid4()),
        "competitor_id": competitor_id,
        "market_id": market_id,
        "locator": (
            f"https://hn.algolia.com/api/v1/search_by_date"
            f"?query={query}&tags=story&hitsPerPage=25"
        ),
        "source_type": "hackernews_search",
        "source_family": "technical_forum",
        "limit": 25,
        "options": {"adapter": "json", "source_family": "technical_forum"},
    })

    return sources


# ── Post-commit activity event ────────────────────────────────────────────────

def _write_initialization_activity(activity_repo: Any, info: dict[str, Any]) -> None:
    """Write the agent-initialized activity event after the transaction commits."""
    try:
        from domain.agent import AgentActivity

        company_list = ", ".join(info["company_names"][:6])
        if len(info["company_names"]) > 6:
            company_list += f" +{len(info['company_names']) - 6} more"

        families = " · ".join(
            f.replace("_", " ").title() for f in info["source_families"]
        )

        activity_repo.save_agent_activity(
            AgentActivity.create(
                market_id=info["market_id"],
                event_type="agent_initialized",
                title="Agent initialized",
                detail=(
                    f"Identified {len(info['company_names'])} companies — "
                    f"{company_list}. "
                    f"Activated {info['source_count']} sources across {families}."
                ),
                metadata={
                    "template_id": None,
                    "company_count": len(info["company_names"]),
                    "source_count": info["source_count"],
                    "source_families": info["source_families"],
                },
            )
        )
    except Exception:
        pass
