import pytest

from domain.source import SourceCandidate, SourceReplacementSuggestion


def _candidate() -> SourceCandidate:
    return SourceCandidate.create(
        locator="https://hn.algolia.com/api/v1/search_by_date?query=devtools",
        source_type="hackernews_search",
        label="Hacker News comments",
        rationale="Gate-free technical discussion source.",
        source_family="technical_forum",
        market_id="devtools",
        limit=25,
        rank_score=0.8,
    )


def test_creates_source_replacement_suggestion() -> None:
    suggestion = SourceReplacementSuggestion.create(
        candidate=_candidate(),
        trigger="blocked_source",
        reason="Reddit source is blocked; use a gate-free technical forum.",
        replaces_source_id="source-1",
    )

    assert suggestion.trigger == "blocked_source"
    assert suggestion.replaces_source_id == "source-1"
    assert suggestion.candidate.source_family == "technical_forum"


def test_rejects_unknown_trigger() -> None:
    with pytest.raises(ValueError, match="unsupported replacement trigger"):
        SourceReplacementSuggestion.create(
            candidate=_candidate(),
            trigger="random",
            reason="Use this instead.",
        )


def test_requires_reason() -> None:
    with pytest.raises(ValueError, match="reason is required"):
        SourceReplacementSuggestion.create(
            candidate=_candidate(),
            trigger="low_yield",
            reason=" ",
        )
