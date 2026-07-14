from application.onboarding.niche_seeds import NICHE_SEEDS


def _seed_for_job(job: str) -> dict:
    for seed in NICHE_SEEDS:
        if seed["job"] == job:
            return seed
    raise AssertionError(f"missing seed for job: {job}")


def test_ecommerce_fulfillment_has_multiple_scan_ready_sources() -> None:
    seed = _seed_for_job("Manage ecommerce fulfillment and shipping")
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


def test_podcast_has_multiple_scan_ready_sources() -> None:
    seed = _seed_for_job("Produce and host a podcast")
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
