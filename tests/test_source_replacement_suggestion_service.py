from datetime import UTC, datetime, timedelta

from application.source_suggestions import SourceReplacementSuggestionService
from domain.niche import NicheSource, NicheSourceRunStats, UserNiche


def _niche() -> UserNiche:
    return UserNiche.create(
        id="niche-1",
        user_id="user-1",
        job="Build internal tools",
        buyer="Engineering teams",
        category="devtools",
    )


def _source(**overrides: object) -> NicheSource:
    values = {
        "id": "source-1",
        "niche_id": "niche-1",
        "locator": "https://www.reddit.com/search.json?q=retool&sort=new",
        "source_type": "reddit_search",
        "source_family": "social",
        "is_gate_free": False,
        "enabled": False,
        "access_mode": "api_auth",
        "requires_auth": True,
    }
    values.update(overrides)
    return NicheSource.create(**values)  # type: ignore[arg-type]


def test_suggests_gate_free_replacements_for_blocked_source() -> None:
    suggestions = SourceReplacementSuggestionService().suggest_for_source(
        _source(),
        niche=_niche(),
    )

    assert [suggestion.trigger for suggestion in suggestions] == [
        "blocked_source",
        "blocked_source",
    ]
    assert [suggestion.candidate.source_type for suggestion in suggestions] == [
        "hackernews_search",
        "stackoverflow_search",
    ]
    assert suggestions[0].replaces_source_id == "source-1"
    assert suggestions[0].candidate.market_name == "Build internal tools"


def test_suppresses_already_monitored_replacement_locators() -> None:
    existing = _source(
        id="source-2",
        locator=(
            "https://hn.algolia.com/api/v1/search_by_date"
            "?query=Build+internal+tools&tags=comment&hitsPerPage=25"
        ),
        source_type="hackernews_search",
        source_family="technical_forum",
        is_gate_free=True,
        enabled=True,
        access_mode="api",
        requires_auth=False,
    )

    suggestions = SourceReplacementSuggestionService().suggest_for_source(
        _source(),
        niche=_niche(),
        existing_sources=[existing],
    )

    assert [suggestion.candidate.source_type for suggestion in suggestions] == [
        "stackoverflow_search",
    ]


def test_suggests_low_yield_replacement_for_noisy_source() -> None:
    source = _source(
        locator="https://hn.algolia.com/api/v1/search_by_date?query=retool",
        source_type="hackernews_search",
        source_family="technical_forum",
        is_gate_free=True,
        enabled=True,
        access_mode="api",
        requires_auth=False,
        signal_quality_score=0.1,
        last_scanned_at=datetime.now(tz=UTC),
    )

    suggestions = SourceReplacementSuggestionService().suggest_for_source(
        source,
        niche=_niche(),
    )

    assert suggestions
    assert suggestions[0].trigger == "low_yield"
    assert "low yield" in suggestions[0].reason


def test_suggests_stale_replacement_for_old_source() -> None:
    now = datetime.now(tz=UTC)
    source = _source(
        locator="https://hn.algolia.com/api/v1/search_by_date?query=retool",
        source_type="hackernews_search",
        source_family="technical_forum",
        is_gate_free=True,
        enabled=True,
        access_mode="api",
        requires_auth=False,
        last_scanned_at=now - timedelta(days=20),
    )

    suggestions = SourceReplacementSuggestionService().suggest_for_source(
        source,
        niche=_niche(),
        now=now,
    )

    assert suggestions
    assert suggestions[0].trigger == "stale_source"


def test_does_not_suggest_replacements_for_productive_source() -> None:
    source = _source(
        locator="https://hn.algolia.com/api/v1/search_by_date?query=retool",
        source_type="hackernews_search",
        source_family="technical_forum",
        is_gate_free=True,
        enabled=True,
        access_mode="api",
        requires_auth=False,
        buyer_voice_verified=True,
    )
    stats = NicheSourceRunStats.create(
        niche_source_id=source.id,
        total_runs=3,
        success_count=3,
        posts_fetched_count=30,
        relevant_posts_count=8,
        extracted_signals_count=3,
    )

    suggestions = SourceReplacementSuggestionService().suggest_for_source(
        source,
        niche=_niche(),
        stats=stats,
    )

    assert suggestions == []
