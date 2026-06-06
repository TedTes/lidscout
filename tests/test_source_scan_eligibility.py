from dataclasses import replace

from domain.niche import NicheSource, NicheSourceRunStats

from application.source_quality import source_scan_eligibility


def _source(**overrides) -> NicheSource:
    force_enabled = bool(overrides.pop("force_enabled", False))
    values = {
        "id": "source-1",
        "niche_id": "niche-1",
        "locator": "https://example.com/source",
        "source_type": "hackernews_search",
        "source_family": "technical_forum",
        "is_gate_free": True,
    }
    values.update(overrides)
    source = NicheSource.create(**values)
    if force_enabled:
        return replace(source, enabled=True)
    return source


def _stats(**overrides) -> NicheSourceRunStats:
    values = {
        "niche_source_id": "source-1",
        "total_runs": 1,
        "success_count": 1,
        "posts_fetched_count": 5,
        "relevant_posts_count": 1,
    }
    values.update(overrides)
    return NicheSourceRunStats.create(**values)


def test_allows_untested_gate_free_source() -> None:
    result = source_scan_eligibility(_source())

    assert result.eligible is True


def test_skips_paused_source() -> None:
    result = source_scan_eligibility(_source(health_status="paused"))

    assert result.eligible is False
    assert "paused" in result.reason


def test_skips_proxy_source_without_proxy_access() -> None:
    result = source_scan_eligibility(
        _source(
            source_type="g2_reviews",
            source_family="reviews",
            is_gate_free=False,
            requires_proxy=True,
            force_enabled=True,
        )
    )

    assert result.eligible is False
    assert "proxy" in result.reason


def test_allows_proxy_source_when_proxy_access_is_enabled() -> None:
    result = source_scan_eligibility(
        _source(
            source_type="g2_reviews",
            source_family="reviews",
            is_gate_free=False,
            requires_proxy=True,
            force_enabled=True,
        ),
        allow_proxy_sources=True,
    )

    assert result.eligible is True


def test_skips_auth_source_without_authenticated_access() -> None:
    result = source_scan_eligibility(
        _source(
            source_type="reddit_search",
            source_family="social",
            is_gate_free=False,
            requires_auth=True,
            force_enabled=True,
        )
    )

    assert result.eligible is False
    assert "authenticated" in result.reason


def test_allows_auth_source_when_authenticated_access_is_enabled() -> None:
    result = source_scan_eligibility(
        _source(
            source_type="reddit_search",
            source_family="social",
            is_gate_free=False,
            requires_auth=True,
            force_enabled=True,
        ),
        allow_auth_sources=True,
    )

    assert result.eligible is True


def test_allows_retry_before_failure_threshold() -> None:
    result = source_scan_eligibility(
        _source(health_status="failing", last_error="temporary timeout"),
        _stats(
            total_runs=2,
            success_count=1,
            failure_count=1,
            consecutive_failures=1,
            posts_fetched_count=10,
            relevant_posts_count=2,
            rule_filtered_count=3,
        ),
    )

    assert result.eligible is True


def test_skips_source_after_repeated_failures() -> None:
    result = source_scan_eligibility(
        _source(health_status="failing", last_error="blocked"),
        _stats(
            total_runs=3,
            success_count=0,
            failure_count=3,
            consecutive_failures=3,
            posts_fetched_count=0,
            relevant_posts_count=0,
        ),
    )

    assert result.eligible is False
    assert "failures" in result.reason


def test_skips_noisy_source_after_enough_history() -> None:
    result = source_scan_eligibility(
        _source(signal_quality_score=0.2),
        _stats(
            total_runs=2,
            success_count=2,
            posts_fetched_count=40,
            relevant_posts_count=0,
            rule_filtered_count=20,
            llm_filtered_count=20,
        ),
    )

    assert result.eligible is False
    assert "quality" in result.reason or "relevant" in result.reason


def test_does_not_reject_sparse_noisy_history_too_early() -> None:
    result = source_scan_eligibility(
        _source(signal_quality_score=0.2),
        _stats(
            total_runs=2,
            success_count=2,
            posts_fetched_count=4,
            relevant_posts_count=0,
            rule_filtered_count=2,
            llm_filtered_count=2,
        ),
    )

    assert result.eligible is True


def test_skips_unverified_low_signal_source() -> None:
    result = source_scan_eligibility(
        _source(
            source_type="changelog",
            source_family="owned_site",
            tier=5,
            signal_quality_score=0.55,
        )
    )

    assert result.eligible is False
    assert "Low-signal" in result.reason


def test_allows_low_signal_source_after_buyer_voice_verification() -> None:
    result = source_scan_eligibility(
        _source(
            source_type="changelog",
            source_family="owned_site",
            tier=5,
            signal_quality_score=0.55,
            buyer_voice_verified=True,
        )
    )

    assert result.eligible is True


def test_allows_low_signal_source_after_relevant_history() -> None:
    result = source_scan_eligibility(
        _source(
            source_type="changelog",
            source_family="owned_site",
            tier=5,
            signal_quality_score=0.55,
        ),
        _stats(
            total_runs=1,
            success_count=1,
            posts_fetched_count=5,
            relevant_posts_count=1,
        ),
    )

    assert result.eligible is True
