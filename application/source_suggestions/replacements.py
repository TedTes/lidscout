"""Replacement suggestions for low-quality niche sources."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs, unquote_plus, urlparse

from application.source_binding.templates import (
    CandidateSource,
    github_discussions,
    github_issues,
    hackernews_search,
    stackoverflow_search,
)
from application.source_quality import source_quality_status
from domain.niche import NicheSource, NicheSourceRunStats, UserNiche
from domain.source import SourceCandidate, SourceReplacementSuggestion


class SourceReplacementSuggestionService:
    """Suggest gate-free alternatives for sources that need attention."""

    def suggest_for_source(
        self,
        source: NicheSource,
        *,
        niche: UserNiche | None = None,
        stats: NicheSourceRunStats | None = None,
        existing_sources: list[NicheSource] | None = None,
        now: datetime | None = None,
        limit: int = 3,
    ) -> list[SourceReplacementSuggestion]:
        """Return replacement suggestions for one unhealthy source."""
        if limit < 1:
            return []

        quality = source_quality_status(source, stats, now=now)
        trigger = _trigger_for_status(quality.label)
        if trigger is None:
            return []

        existing_locators = {
            _normalize_locator(existing.locator)
            for existing in existing_sources or []
            if existing.id != source.id
        }
        query = _replacement_query(source, niche)
        candidates = _replacement_candidates(source, query)
        suggestions: list[SourceReplacementSuggestion] = []
        seen: set[str] = set()

        for candidate_source in candidates:
            locator_key = _normalize_locator(candidate_source.locator)
            if locator_key in seen or locator_key in existing_locators:
                continue
            seen.add(locator_key)
            suggestions.append(
                SourceReplacementSuggestion.create(
                    candidate=_to_source_candidate(
                        candidate_source,
                        source=source,
                        niche=niche,
                    ),
                    trigger=trigger,
                    reason=_replacement_reason(quality.label, quality.reason),
                    replaces_source_id=source.id,
                )
            )
            if len(suggestions) >= limit:
                break

        return suggestions


def _replacement_candidates(
    source: NicheSource,
    query: str,
) -> list[CandidateSource]:
    candidates: list[CandidateSource] = []
    github_repo = _github_repo(source.locator)
    if github_repo:
        if "discussion" not in source.source_type:
            candidates.append(github_discussions(github_repo))
        if "issue" not in source.source_type:
            candidates.append(github_issues(github_repo))

    candidates.extend(
        [
            hackernews_search(query),
            stackoverflow_search(query),
        ]
    )
    return [candidate for candidate in candidates if candidate.is_gate_free]


def _to_source_candidate(
    candidate: CandidateSource,
    *,
    source: NicheSource,
    niche: UserNiche | None,
) -> SourceCandidate:
    return SourceCandidate.create(
        locator=candidate.locator,
        source_type=candidate.source_type,
        label=_candidate_label(candidate),
        rationale=_candidate_rationale(candidate),
        source_family=candidate.source_family,
        market_id=source.niche_id,
        market_name=niche.job if niche else None,
        limit=25,
        options={
            "adapter": "json",
            "source_family": candidate.source_family,
            "replacement_for_source_id": source.id,
        },
        template_id=f"replacement-{candidate.source_type}",
        rank_score=candidate.signal_quality_score or 0.0,
    )


def _candidate_label(candidate: CandidateSource) -> str:
    labels = {
        "github_issues_search": "GitHub issues",
        "github_discussions": "GitHub discussions",
        "hackernews_search": "Hacker News comments",
        "stackoverflow_search": "Stack Overflow questions",
    }
    return labels.get(candidate.source_type, candidate.source_type.replace("_", " ").title())


def _candidate_rationale(candidate: CandidateSource) -> str:
    rationales = {
        "github_issues_search": "Gate-free issue reports with concrete reproduction details and maintainer context.",
        "github_discussions": "Gate-free product discussions and feature requests from active users.",
        "hackernews_search": "Gate-free technical discussion source that can replace blocked social or review sources.",
        "stackoverflow_search": "Gate-free developer question source that surfaces implementation friction.",
    }
    return rationales.get(
        candidate.source_type,
        "Gate-free source candidate generated from source templates.",
    )


def _trigger_for_status(label: str) -> str | None:
    if label == "blocked":
        return "blocked_source"
    if label == "noisy":
        return "low_yield"
    if label == "stale":
        return "stale_source"
    return None


def _replacement_reason(label: str, reason: str) -> str:
    if label == "blocked":
        return f"Current source is blocked; suggest gate-free alternatives. {reason}"
    if label == "noisy":
        return f"Current source has low yield; suggest higher-signal alternatives. {reason}"
    return f"Current source is stale; suggest active gate-free alternatives. {reason}"


def _replacement_query(source: NicheSource, niche: UserNiche | None) -> str:
    if niche and niche.job.strip():
        return niche.job.strip()

    for key in ("query", "company_name", "market_name", "niche_name"):
        value = source.options.get(key)
        if isinstance(value, str) and value.strip():
            return unquote_plus(value.strip().replace("+", " "))

    parsed = urlparse(source.locator)
    params = parse_qs(parsed.query)
    for key in ("query", "q"):
        values = params.get(key)
        if values and values[0].strip():
            return unquote_plus(values[0].replace("+", " "))

    return parsed.netloc.replace("www.", "") or "product feedback"


def _github_repo(locator: str) -> str | None:
    parsed = urlparse(locator)
    if parsed.netloc not in {"github.com", "api.github.com"}:
        return None
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc == "api.github.com" and "repo:" in parsed.query:
        query = unquote_plus(parsed.query)
        repo_part = query.split("repo:", maxsplit=1)[1].split("+", maxsplit=1)[0]
        return repo_part if "/" in repo_part else None
    if len(path_parts) >= 2:
        return f"{path_parts[0]}/{path_parts[1]}"
    return None


def _normalize_locator(locator: str) -> str:
    return locator.strip().rstrip("/")
