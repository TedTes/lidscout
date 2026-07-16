from application.onboarding.niche_seeds import NICHE_SEEDS


def _seed_for_job(job: str) -> dict:
    for seed in NICHE_SEEDS:
        if seed["job"] == job:
            return seed
    raise AssertionError(f"missing seed for job: {job}")


def test_internal_tool_watchlist_has_multiple_scan_ready_sources() -> None:
    seed = _seed_for_job("Track customer complaints about internal tool builders")
    gate_free_sources = [
        source for source in seed["sources"] if source.get("is_gate_free") is True
    ]
    source_types = {source["source_type"] for source in gate_free_sources}

    assert len(gate_free_sources) >= 5
    assert source_types >= {
        "hackernews",
        "github_issues_search",
        "stackoverflow_search",
    }


def test_managed_postgres_watchlist_has_multiple_scan_ready_sources() -> None:
    seed = _seed_for_job("Track customer complaints about managed Postgres platforms")
    gate_free_sources = [
        source for source in seed["sources"] if source.get("is_gate_free") is True
    ]
    source_types = {source["source_type"] for source in gate_free_sources}

    assert len(gate_free_sources) >= 5
    assert source_types >= {
        "hackernews",
        "github_issues_search",
        "stackoverflow_search",
    }


def test_seed_defaults_do_not_include_gated_sources() -> None:
    gated_types = {
        "reddit",
        "reddit_search",
        "reddit_subreddit",
        "g2",
        "g2_reviews",
        "capterra",
        "capterra_reviews",
    }

    for seed in NICHE_SEEDS:
        for source in seed["sources"]:
            assert source["source_type"] not in gated_types
            assert source.get("is_gate_free") is True
