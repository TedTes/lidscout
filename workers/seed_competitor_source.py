"""Seed one competitor and monitored source for pipeline smoke tests."""
from __future__ import annotations

import argparse
import json

from domain.competitor import Competitor
from domain.market import Market
from domain.source import MonitoredSource
from infrastructure.db import (
    PostgresCompetitorRepository,
    PostgresMarketRepository,
    PostgresMonitoredSourceRepository,
)
from shared.config import get_app_config


def seed_competitor_source(
    *,
    competitor_id: str,
    competitor_name: str,
    source_url: str,
    market_id: str | None = None,
    market_name: str | None = None,
    market_description: str | None = None,
    market_target_user: str | None = None,
    market_idea_prompt: str | None = None,
    source_type: str = "web",
    website: str | None = None,
    category: str | None = None,
    description: str | None = None,
    limit: int | None = None,
    enabled: bool = True,
    database_url: str | None = None,
) -> dict[str, object]:
    """Persist one competitor and one monitored source."""
    resolved_database_url = database_url or get_app_config().DATABASE_URL
    if not _is_postgres_url(resolved_database_url):
        raise ValueError("DATABASE_URL must be a Supabase/Postgres URL")

    market = None
    if market_id is not None:
        market = Market.create(
            id=market_id,
            name=market_name or market_id,
            description=market_description,
            target_user=market_target_user,
            idea_prompt=market_idea_prompt,
        )

    competitor = Competitor.create(
        id=competitor_id,
        name=competitor_name,
        website=website,
        category=category,
        description=description,
        market_id=market.id if market else None,
    )
    source = MonitoredSource.create(
        competitor_id=competitor.id,
        market_id=market.id if market else None,
        locator=source_url,
        source_type=source_type,
        enabled=enabled,
        limit=limit,
    )

    market_repository = (
        PostgresMarketRepository(resolved_database_url)
        if market is not None
        else None
    )
    competitor_repository = PostgresCompetitorRepository(resolved_database_url)
    source_repository = PostgresMonitoredSourceRepository(resolved_database_url)
    try:
        market_inserted_count = (
            market_repository.save_markets([market])
            if market_repository is not None and market is not None
            else 0
        )
        competitor_inserted_count = competitor_repository.save_competitors([competitor])
        source_inserted_count = source_repository.save_monitored_sources([source])
    finally:
        if market_repository is not None:
            market_repository.close()
        competitor_repository.close()
        source_repository.close()

    return {
        "market": (
            {
                "id": market.id,
                "name": market.name,
            }
            if market is not None
            else None
        ),
        "competitor": {
            "id": competitor.id,
            "name": competitor.name,
            "market_id": competitor.market_id,
        },
        "source": {
            "id": source.id,
            "market_id": source.market_id,
            "locator": source.locator,
            "source_type": source.source_type,
            "enabled": source.enabled,
            "limit": source.limit,
        },
        "market_inserted_count": market_inserted_count,
        "competitor_inserted_count": competitor_inserted_count,
        "source_inserted_count": source_inserted_count,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the seed command from the command line."""
    args = _parser().parse_args(argv)
    result = seed_competitor_source(
        competitor_id=args.competitor_id,
        competitor_name=args.competitor_name,
        market_id=args.market_id,
        market_name=args.market_name,
        market_description=args.market_description,
        market_target_user=args.market_target_user,
        market_idea_prompt=args.market_idea_prompt,
        source_url=args.source_url,
        source_type=args.source_type,
        website=args.website,
        category=args.category,
        description=args.description,
        limit=args.limit,
        enabled=not args.disabled,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed one LidScout competitor and monitored source.",
    )
    parser.add_argument("--competitor-id", required=True)
    parser.add_argument("--competitor-name", required=True)
    parser.add_argument("--market-id")
    parser.add_argument("--market-name")
    parser.add_argument("--market-description")
    parser.add_argument("--market-target-user")
    parser.add_argument("--market-idea-prompt")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-type", default="web")
    parser.add_argument("--website")
    parser.add_argument("--category")
    parser.add_argument("--description")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--disabled", action="store_true")
    return parser


def _is_postgres_url(database_url: str) -> bool:
    return database_url.startswith(("postgresql://", "postgres://"))


if __name__ == "__main__":
    raise SystemExit(main())
