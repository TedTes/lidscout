from datetime import UTC, datetime, timedelta

from application.source_quality import source_quality_status
from domain.niche import NicheSource, NicheSourceRunStats


def _source(**overrides) -> NicheSource:
    defaults = {
        "niche_id": "niche-1",
        "locator": "https://example.com/feed",
        "source_type": "rss",
        "source_family": "technical_forum",
        "is_gate_free": True,
    }
    defaults.update(overrides)
    return NicheSource.create(**defaults)


def test_marks_proxy_sources_blocked() -> None:
    source = _source(
        access_mode="proxy_required",
        requires_proxy=True,
    )

    status = source_quality_status(source)

    assert status.label == "blocked"
    assert "proxy" in status.reason


def test_marks_unscanned_sources_untested() -> None:
    status = source_quality_status(_source())

    assert status.label == "untested"


def test_marks_stale_sources() -> None:
    now = datetime(2026, 6, 4, tzinfo=UTC)
    source = _source(last_scanned_at=now - timedelta(days=20))
    stats = NicheSourceRunStats.create(
        niche_source_id=source.id,
        total_runs=1,
        success_count=1,
        posts_fetched_count=10,
        last_scanned_at=now - timedelta(days=20),
    )

    status = source_quality_status(source, stats, now=now)

    assert status.label == "stale"


def test_marks_no_yield_sources_noisy() -> None:
    source = _source()
    stats = NicheSourceRunStats.create(
        niche_source_id=source.id,
        total_runs=3,
        success_count=3,
        posts_fetched_count=45,
        rule_filtered_count=30,
        llm_filtered_count=15,
    )

    status = source_quality_status(source, stats)

    assert status.label == "noisy"
    assert status.score is not None
    assert status.score < 0.25


def test_marks_buyer_evidence_sources_productive() -> None:
    source = _source(buyer_voice_verified=True)
    stats = NicheSourceRunStats.create(
        niche_source_id=source.id,
        total_runs=4,
        success_count=4,
        posts_fetched_count=40,
        relevant_posts_count=8,
        rule_filtered_count=12,
        extracted_signals_count=3,
    )

    status = source_quality_status(source, stats)

    assert status.label == "productive"
