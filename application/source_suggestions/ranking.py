"""Ranking rules for source suggestions."""
from domain.source import SourceCandidate

_SOURCE_FAMILY_PRIORITY = {
    "reviews": 4.0,
    "social": 3.0,
    "technical_forum": 3.0,
    "owned_site": 1.0,
}

_VALIDATION_PRIORITY = {
    "valid": 0,
    "unknown": 1,
    "invalid": 2,
}


def rank_source_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
    """Sort source candidates by actionability and expected signal quality."""
    return sorted(candidates, key=_ranking_key)


def _ranking_key(candidate: SourceCandidate) -> tuple[bool, int, float, float, str]:
    return (
        candidate.already_monitored,
        _VALIDATION_PRIORITY[candidate.validation_status],
        -candidate.rank_score,
        -_SOURCE_FAMILY_PRIORITY.get(candidate.source_family, 0.0),
        candidate.label,
    )
