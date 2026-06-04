import asyncio

from api.routes.signals import SignalApiDependencies, list_market_sources
from domain.niche import NicheSource, NicheSourceRunStats, UserNiche
from domain.user import User
from infrastructure.db import (
    InMemoryNicheSourceRepository,
    InMemoryUserNicheRepository,
)


def test_market_sources_include_quality_status_and_health_stats() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemoryNicheSourceRepository()
    source = NicheSource.create(
        id="source-1",
        niche_id="template-1",
        locator="https://hn.algolia.com/api/v1/search_by_date?query=devtools",
        source_type="hackernews_search",
        source_family="technical_forum",
        is_gate_free=True,
        buyer_voice_verified=True,
    )
    source_repository.save_niche_sources([source])
    source_repository.upsert_niche_source_run_stats(
        NicheSourceRunStats.create(
            niche_source_id=source.id,
            total_runs=4,
            success_count=4,
            posts_fetched_count=40,
            relevant_posts_count=8,
            rule_filtered_count=12,
            extracted_signals_count=3,
            gap_count=1,
            last_status="healthy",
            last_fetched_count=10,
            last_relevant_count=2,
            last_extracted_count=1,
            last_gap_count=1,
        )
    )
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        niche_source_repository=source_repository,
    )

    response = asyncio.run(
        list_market_sources("market-1", dependencies, current_user=user)
    )

    item = response["sources"][0]
    assert item["quality_status"] == "productive"
    assert item["quality_reason"] == "Source has produced relevant buyer evidence."
    assert item["health"]["total_runs"] == 4
    assert item["health"]["fetch_success_rate"] == 1.0
    assert item["health"]["relevance_yield_rate"] == 0.2
    assert item["health"]["signal_yield_rate"] == 0.375
