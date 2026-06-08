"""Synthesize opportunities from qualified accumulated themes."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from application.opportunity import OpportunitySynthesisContext
from domain.finding import Finding
from domain.opportunity import Opportunity
from domain.theme import Theme


@dataclass(frozen=True)
class ThemeOpportunitySynthesisResult:
    """Result of synthesizing one theme-backed opportunity."""

    opportunity: Opportunity | None
    reason: str | None = None


class ThemeOpportunitySynthesisService:
    """Builds product opportunities from qualified accumulated themes."""

    def synthesize(
        self,
        theme: Theme,
        findings: list[Finding],
        context: OpportunitySynthesisContext | None = None,
    ) -> ThemeOpportunitySynthesisResult:
        if theme.status != "qualified":
            return ThemeOpportunitySynthesisResult(None, "theme_not_qualified")
        if len(findings) < 2:
            return ThemeOpportunitySynthesisResult(None, "insufficient_evidence")

        source_count = len({finding.source_id for finding in findings if finding.source_id})
        target_user = _target_user(findings, context)
        category = _most_common(
            [finding.category for finding in findings if finding.category],
            fallback=theme.title,
        )
        confidence = _confidence(theme, findings, source_count)

        return ThemeOpportunitySynthesisResult(
            Opportunity.create(
                id=f"opportunity-theme-{theme.id}",
                cluster_id=None,
                source_theme_id=theme.id,
                title=_title_for(theme, target_user),
                target_user=target_user,
                pain_summary=theme.summary,
                why_it_matters=_why_it_matters(theme, findings, source_count, context),
                suggested_wedge=_suggested_wedge(category, findings),
                evidence_count=len(findings),
                confidence=confidence,
                evidence_signal_ids=[finding.id for finding in findings],
                unmet_need_type=_infer_unmet_need_type(theme, findings),
            )
        )


def _target_user(
    findings: list[Finding],
    context: OpportunitySynthesisContext | None,
) -> str:
    return _most_common(
        [finding.affected_user for finding in findings if finding.affected_user],
        fallback=context.target_user if context and context.target_user else "affected users",
    )


def _title_for(theme: Theme, target_user: str) -> str:
    title = theme.title.strip()
    if target_user.lower() in title.lower():
        return title
    return f"Reduce {title.lower()} friction for {target_user}"


def _why_it_matters(
    theme: Theme,
    findings: list[Finding],
    source_count: int,
    context: OpportunitySynthesisContext | None,
) -> str:
    base = (
        f"{len(findings)} evidence item(s) across {source_count} source(s) point "
        f"to a repeated unmet need: {theme.summary}"
    )
    if context and context.objective:
        return f"{base} This maps to the research objective: {context.objective}."
    return base


def _suggested_wedge(category: str | None, findings: list[Finding]) -> str:
    workaround = _most_common(
        [
            finding.current_workaround
            for finding in findings
            if finding.current_workaround
        ],
        fallback=None,
    )
    category = category or "workflow"
    if workaround:
        return (
            f"Build a focused {category.lower()} workflow that removes the "
            f"repeated workaround: {workaround}."
        )
    return f"Build a focused {category.lower()} workflow for this repeated pain."


def _confidence(theme: Theme, findings: list[Finding], source_count: int) -> float:
    evidence_component = min(len(findings), 5) / 5 * 0.35
    source_component = min(source_count, 3) / 3 * 0.25
    confidence_component = theme.average_confidence * 0.25
    pain_component = (
        sum(1 for finding in findings if finding.urgency == "high" or finding.severity == "high")
        / len(findings)
        * 0.15
    )
    return round(
        min(
            evidence_component
            + source_component
            + confidence_component
            + pain_component,
            1.0,
        ),
        2,
    )


def _infer_unmet_need_type(theme: Theme, findings: list[Finding]) -> str:
    text = " ".join(
        [
            theme.title,
            theme.summary,
            *[finding.pain for finding in findings],
            *[finding.category or "" for finding in findings],
            *[finding.current_workaround or "" for finding in findings],
        ]
    ).lower()
    if any(token in text for token in ("cost", "price", "pricing", "expensive", "budget")):
        return "money"
    if any(token in text for token in ("slow", "time", "hours", "manual", "delay")):
        return "time"
    if any(token in text for token in ("workaround", "tedious", "setup", "configure")):
        return "effort"
    if any(token in text for token in ("missing", "lack", "unsupported", "unable")):
        return "capability"
    return "fit"


def _most_common(values: list[str], *, fallback: str | None) -> str:
    if not values:
        return fallback or "affected users"
    return Counter(values).most_common(1)[0][0]
