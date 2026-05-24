"""Validation helpers for rendered source candidates."""
from urllib.parse import urlparse

from domain.source import SourceCandidate


def validate_source_candidate(candidate: SourceCandidate) -> SourceCandidate:
    """Mark a source candidate valid or invalid using local URL checks."""
    parsed = urlparse(candidate.locator)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return _replace_validation(
            candidate,
            validation_status="valid",
            validation_error=None,
        )
    return _replace_validation(
        candidate,
        validation_status="invalid",
        validation_error="locator must be an http or https URL",
    )


def validate_source_candidates(
    candidates: list[SourceCandidate],
) -> list[SourceCandidate]:
    """Validate a list of rendered candidates."""
    return [validate_source_candidate(candidate) for candidate in candidates]


def _replace_validation(
    candidate: SourceCandidate,
    *,
    validation_status: str,
    validation_error: str | None,
) -> SourceCandidate:
    return SourceCandidate.create(
        locator=candidate.locator,
        source_type=candidate.source_type,
        label=candidate.label,
        rationale=candidate.rationale,
        source_family=candidate.source_family,
        competitor_id=candidate.competitor_id,
        competitor_name=candidate.competitor_name,
        market_id=candidate.market_id,
        market_name=candidate.market_name,
        limit=candidate.limit,
        options=candidate.options,
        template_id=candidate.template_id,
        already_monitored=candidate.already_monitored,
        rank_score=candidate.rank_score,
        validation_status=validation_status,
        validation_error=validation_error,
    )
