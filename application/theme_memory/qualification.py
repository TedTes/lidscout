"""Qualification gates for accumulated themes."""
from __future__ import annotations

from dataclasses import dataclass
import re

from application.opportunity import OpportunitySynthesisContext
from domain.finding import Finding
from domain.theme import Theme


@dataclass(frozen=True)
class ThemeQualification:
    """Decision explaining whether an accumulated theme can become an opportunity."""

    theme_id: str
    qualified: bool
    reason: str | None
    finding_count: int
    source_count: int
    company_count: int
    buyer_context_count: int
    strong_pain_count: int
    high_signal_source_count: int
    average_confidence: float


def qualify_theme_for_opportunity(
    theme: Theme,
    findings: list[Finding],
    context: OpportunitySynthesisContext | None = None,
) -> ThemeQualification:
    """Return whether an accumulated theme is strong enough to promote."""
    finding_count = len(findings)
    source_count = len({finding.source_id for finding in findings if finding.source_id})
    company_count = len({finding.company_id for finding in findings if finding.company_id})
    buyer_context_count = _buyer_context_count(findings)
    strong_pain_count = _strong_pain_count(findings)
    high_signal_source_count = _high_signal_source_count(findings)
    average_confidence = _average_confidence(findings)

    def result(qualified: bool, reason: str | None) -> ThemeQualification:
        return ThemeQualification(
            theme_id=theme.id,
            qualified=qualified,
            reason=reason,
            finding_count=finding_count,
            source_count=source_count,
            company_count=company_count,
            buyer_context_count=buyer_context_count,
            strong_pain_count=strong_pain_count,
            high_signal_source_count=high_signal_source_count,
            average_confidence=average_confidence,
        )

    if finding_count < 2:
        return result(False, "insufficient_evidence")

    has_source_diversity = source_count >= 2
    high_signal_exception = high_signal_source_count > 0 and finding_count >= 3
    if not has_source_diversity and not high_signal_exception:
        return result(False, "insufficient_source_diversity")

    if average_confidence < 0.55:
        return result(False, "low_extraction_confidence")

    if buyer_context_count == 0:
        return result(False, "thin_buyer_context")

    if strong_pain_count == 0:
        return result(False, "low_pain_intensity")

    if _looks_vendor_fix_only(theme, findings) and company_count <= 1:
        return result(False, "vendor_fix_only")

    if _looks_off_niche(theme, findings, context):
        return result(False, "off_niche")

    return result(True, "qualified_high_signal_exception" if high_signal_exception else None)


def _buyer_context_count(findings: list[Finding]) -> int:
    return sum(
        1
        for finding in findings
        if finding.affected_user
        or finding.job_to_be_done
        or finding.current_workaround
        or finding.willingness_to_pay is True
    )


def _strong_pain_count(findings: list[Finding]) -> int:
    return sum(
        1
        for finding in findings
        if finding.urgency in {"medium", "high"}
        or finding.severity in {"medium", "high"}
        or finding.willingness_to_pay is True
        or finding.current_workaround
    )


def _high_signal_source_count(findings: list[Finding]) -> int:
    source_ids = set()
    for finding in findings:
        if not finding.source_id:
            continue
        if _is_high_signal_source(finding):
            source_ids.add(finding.source_id)
    return len(source_ids)


def _is_high_signal_source(finding: Finding) -> bool:
    try:
        quality = float(finding.metadata.get("source_quality_score", 0))
    except (TypeError, ValueError):
        quality = 0.0
    try:
        tier = int(finding.metadata.get("source_tier", 99))
    except (TypeError, ValueError):
        tier = 99
    family = str(finding.metadata.get("source_family", "")).lower()
    source_type = str(finding.metadata.get("source_type", "")).lower()
    return quality >= 0.75 or tier <= 2 or any(
        token in f"{family} {source_type}"
        for token in ("github", "stackoverflow", "discourse", "roadmap", "reviews")
    )


def _average_confidence(findings: list[Finding]) -> float:
    if not findings:
        return 0.0
    return round(sum(finding.confidence for finding in findings) / len(findings), 3)


def _looks_vendor_fix_only(theme: Theme, findings: list[Finding]) -> bool:
    text = _normalized_text(
        " ".join(
            [
                theme.title,
                theme.summary,
                *[finding.pain for finding in findings],
                *[finding.evidence_text for finding in findings],
            ]
        )
    )
    has_bug_terms = re.search(r"\b(bug|broken|crash|error|fix|issue|regression)\b", text)
    has_market_terms = re.search(
        r"\b(workflow|alternative|switch|workaround|manual|missing|lack|need|unable)\b",
        text,
    )
    return bool(has_bug_terms and not has_market_terms)


def _looks_off_niche(
    theme: Theme,
    findings: list[Finding],
    context: OpportunitySynthesisContext | None,
) -> bool:
    if context is None:
        return False
    scope_terms = _important_terms(
        " ".join(
            item
            for item in (
                context.niche_name,
                context.target_user,
                context.objective,
                context.extra_instructions,
            )
            if item
        )
    )
    if not scope_terms:
        return False
    evidence_terms = _important_terms(
        " ".join(
            [
                theme.title,
                theme.summary,
                *[finding.pain for finding in findings],
                *[finding.affected_user or "" for finding in findings],
                *[finding.job_to_be_done or "" for finding in findings],
                *[finding.category or "" for finding in findings],
            ]
        )
    )
    if not evidence_terms:
        return True
    return scope_terms.isdisjoint(evidence_terms)


def _important_terms(text: str) -> set[str]:
    stopwords = {
        "and",
        "for",
        "the",
        "with",
        "that",
        "this",
        "from",
        "into",
        "their",
        "users",
        "teams",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]{4,}", text.lower())
        if token not in stopwords
    }


def _normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()
