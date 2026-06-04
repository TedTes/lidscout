"""Observed source quality scoring."""
from domain.niche import NicheSourceRunStats


def source_observed_quality_score(stats: NicheSourceRunStats) -> float:
    """Score a source from observed reliability and evidence yield.

    The score is intentionally conservative for sparse sources: a single useful
    post should not make a source look great, and repeated failures should
    quickly make a source eligible for agent attention.
    """
    if stats.total_runs <= 0:
        return 0.5

    reliability = stats.success_count / stats.total_runs
    reviewed_count = (
        stats.relevant_posts_count
        + stats.rule_filtered_count
        + stats.llm_filtered_count
        + stats.relevance_failed_count
    )
    relevance_rate = (
        stats.relevant_posts_count / reviewed_count if reviewed_count > 0 else 0.0
    )
    extraction_rate = (
        stats.extracted_signals_count / stats.relevant_posts_count
        if stats.relevant_posts_count > 0
        else 0.0
    )
    gap_rate = (
        stats.gap_count / stats.extracted_signals_count
        if stats.extracted_signals_count > 0
        else 0.0
    )
    coverage = min(reviewed_count / 25, 1.0)
    relevance_component = _sparse_rate(relevance_rate, coverage)
    extraction_component = _sparse_rate(extraction_rate, coverage)

    score = (
        0.05
        + (0.30 * reliability)
        + (0.40 * relevance_component)
        + (0.20 * extraction_component)
        + (0.05 * gap_rate)
    )

    if stats.success_count > 0 and stats.posts_fetched_count == 0:
        score *= 0.7

    if stats.success_count >= 2 and stats.relevant_posts_count == 0:
        score *= 0.55

    if 0 < reviewed_count < 5:
        score = min(score, 0.60 + (reviewed_count * 0.01))

    if stats.consecutive_failures >= 3:
        score *= 0.35
    elif stats.consecutive_failures > 0:
        score *= 0.85

    return round(max(0.05, min(0.98, score)), 3)


def _sparse_rate(rate: float, coverage: float) -> float:
    """Blend sparse observations toward neutral until enough posts are reviewed."""
    return (0.5 * (1 - coverage)) + (rate * coverage)
