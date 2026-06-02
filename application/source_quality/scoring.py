"""Observed source quality scoring."""
from domain.niche import NicheSourceRunStats


def source_observed_quality_score(stats: NicheSourceRunStats) -> float:
    """Score a source from observed reliability and relevance outcomes."""
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

    score = (
        0.10
        + (0.25 * reliability)
        + (0.45 * relevance_rate)
        + (0.15 * extraction_rate)
        + (0.05 * gap_rate)
    )

    if stats.consecutive_failures >= 3:
        score *= 0.5
    elif stats.consecutive_failures > 0:
        score *= 0.85

    return round(max(0.05, min(0.98, score)), 3)
