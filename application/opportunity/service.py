"""Opportunity synthesis service."""
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from application.opportunity.synthesis_schema import (
    OPPORTUNITY_SYNTHESIS_PROMPT,
    OPPORTUNITY_SYNTHESIS_RESPONSE_SCHEMA,
    validate_synthesis_response,
)
from application.ports import OpportunityRepository
from domain.cluster import SignalCluster
from domain.opportunity import Opportunity
from domain.signal import Signal
from infrastructure.llm import LLMClient
from shared.logger import get_logger, log_event


logger = get_logger(__name__)


@dataclass(frozen=True)
class ClusterQualification:
    """Decision explaining whether a theme can become a strategic gap."""

    cluster_id: str
    qualified: bool
    reason: str | None
    finding_count: int
    source_count: int
    company_count: int
    general_finding_count: int
    high_signal_source_count: int = 0
    buyer_context_signal_count: int = 0
    strong_pain_signal_count: int = 0
    average_signal_confidence: float = 0.0


@dataclass(frozen=True)
class OpportunitySynthesisResult:
    """Summary of one opportunity synthesis run."""

    synthesized_count: int
    inserted_count: int
    failed_count: int
    opportunities: list[Opportunity]
    rejected_qualifications: list[ClusterQualification]


@dataclass(frozen=True)
class OpportunitySynthesisContext:
    """Research brief and preferences that steer opportunity synthesis."""

    niche_name: str | None = None
    target_user: str | None = None
    objective: str | None = None
    extra_instructions: str | None = None
    ignored_themes: list[str] | None = None
    ignored_categories: list[str] | None = None


UnmetNeedType = Literal["time", "money", "effort", "capability", "fit"]


class OpportunitySynthesisService:
    """Synthesizes actionable product opportunities from pain clusters."""

    def __init__(
        self,
        repository: OpportunityRepository,
        *,
        minimum_average_score: float = 7.0,
        llm_client: LLMClient | None = None,
    ):
        if not 0.0 <= minimum_average_score <= 10.0:
            raise ValueError("minimum_average_score must be between 0.0 and 10.0")
        self.repository = repository
        self.minimum_average_score = minimum_average_score
        self.llm_client = llm_client

    def synthesize(
        self,
        clusters: list[SignalCluster],
        signals: list[Signal],
        *,
        context: OpportunitySynthesisContext | None = None,
    ) -> OpportunitySynthesisResult:
        signal_index = {signal.id: signal for signal in signals}
        opportunities: list[Opportunity] = []
        rejected_qualifications: list[ClusterQualification] = []
        failed_count = 0

        for cluster in clusters:
            if cluster.average_score < self.minimum_average_score:
                continue

            cluster_signals = [
                signal_index[signal_id]
                for signal_id in cluster.signal_ids
                if signal_id in signal_index
            ]
            if not cluster_signals:
                failed_count += 1
                continue
            if _context_ignores_cluster(context, cluster, cluster_signals):
                continue

            qualification = qualify_cluster_for_opportunity(
                cluster,
                cluster_signals,
                context,
            )
            if not qualification.qualified:
                rejected_qualifications.append(qualification)
                continue

            try:
                opportunities.append(
                    self._build_opportunity(cluster, cluster_signals, context)
                )
            except ValueError:
                failed_count += 1

        opportunities = merge_near_duplicate_opportunities(opportunities)
        inserted_count = self.repository.save_opportunities(opportunities)
        failed_count += len(opportunities) - inserted_count

        result = OpportunitySynthesisResult(
            synthesized_count=len(opportunities),
            inserted_count=inserted_count,
            failed_count=failed_count,
            opportunities=opportunities,
            rejected_qualifications=rejected_qualifications,
        )
        log_event(
            logger,
            "opportunity_synthesis_completed",
            synthesized_count=result.synthesized_count,
            inserted_count=result.inserted_count,
            failed_count=result.failed_count,
        )
        return result

    def _build_opportunity(
        self,
        cluster: SignalCluster,
        signals: list[Signal],
        context: OpportunitySynthesisContext | None,
    ) -> Opportunity:
        if self.llm_client is not None:
            try:
                return self._build_opportunity_with_llm(cluster, signals, context)
            except Exception as exc:
                log_event(
                    logger,
                    "opportunity_synthesis_llm_failed",
                    level=logging.WARNING,
                    cluster_id=cluster.id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
        return self._build_opportunity_from_templates(cluster, signals, context)

    def _build_opportunity_with_llm(
        self,
        cluster: SignalCluster,
        signals: list[Signal],
        context: OpportunitySynthesisContext | None,
    ) -> Opportunity:
        raw_json = self.llm_client.generate_structured_response(
            OPPORTUNITY_SYNTHESIS_PROMPT,
            _cluster_content(cluster, signals, context),
            OPPORTUNITY_SYNTHESIS_RESPONSE_SCHEMA,
        )
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM synthesis returned invalid JSON") from exc

        candidate = validate_synthesis_response(payload)
        return Opportunity.create(
            id=f"opportunity-{cluster.id}",
            cluster_id=cluster.id,
            title=candidate.title,
            target_user=candidate.target_user,
            pain_summary=candidate.pain_summary,
            why_it_matters=candidate.why_it_matters,
            suggested_wedge=candidate.suggested_wedge,
            evidence_count=cluster.frequency,
            confidence=_confidence_for(cluster, signals),
            evidence_signal_ids=[signal.id for signal in signals],
            unmet_need_type=candidate.unmet_need_type,
        )

    def _build_opportunity_from_templates(
        self,
        cluster: SignalCluster,
        signals: list[Signal],
        context: OpportunitySynthesisContext | None,
    ) -> Opportunity:
        target_user = _most_common(
            [signal.user_type for signal in signals if signal.user_type],
            fallback=context.target_user if context and context.target_user else "affected users",
        )
        workaround = _most_common(
            [
                signal.current_workaround
                for signal in signals
                if signal.current_workaround
            ],
            fallback=None,
        )
        category = _most_common(
            [signal.category for signal in signals if signal.category],
            fallback=cluster.theme,
        )

        return Opportunity.create(
            id=f"opportunity-{cluster.id}",
            cluster_id=cluster.id,
            title=f"Reduce {cluster.theme.lower()} friction for {target_user}",
            target_user=target_user,
            pain_summary=_pain_summary(cluster, signals),
            why_it_matters=_why_it_matters(cluster, signals, context),
            suggested_wedge=_suggested_wedge(category, workaround),
            evidence_count=cluster.frequency,
            confidence=_confidence_for(cluster, signals),
            evidence_signal_ids=[signal.id for signal in signals],
            unmet_need_type=_infer_unmet_need_type(cluster, signals),
        )


def qualify_cluster_for_opportunity(
    cluster: SignalCluster,
    signals: list[Signal],
    context: OpportunitySynthesisContext | None = None,
) -> ClusterQualification:
    """Return whether a cluster is strong enough to become a strategic gap."""
    finding_count = len(signals)
    source_count = _source_diversity(signals)
    high_signal_source_count = _high_signal_source_diversity(signals)
    company_ids = {
        signal.niche_company_id
        for signal in signals
        if signal.niche_company_id
    }
    company_count = len(company_ids)
    general_signals = [signal for signal in signals if not signal.niche_company_id]
    general_source_count = _source_diversity(general_signals)
    buyer_context_signal_count = _buyer_context_signal_count(signals)
    strong_pain_signal_count = _strong_pain_signal_count(signals)
    average_signal_confidence = _average_signal_confidence(signals)

    def qualification(qualified: bool, reason: str | None) -> ClusterQualification:
        return ClusterQualification(
            cluster_id=cluster.id,
            qualified=qualified,
            reason=reason,
            finding_count=finding_count,
            source_count=source_count,
            company_count=company_count,
            general_finding_count=len(general_signals),
            high_signal_source_count=high_signal_source_count,
            buyer_context_signal_count=buyer_context_signal_count,
            strong_pain_signal_count=strong_pain_signal_count,
            average_signal_confidence=average_signal_confidence,
        )

    if finding_count < 2 or source_count < 2:
        return qualification(False, "insufficient_evidence")

    if high_signal_source_count == 0 and finding_count < 3:
        return qualification(False, "weak_source_mix")

    if average_signal_confidence < 0.55:
        return qualification(False, "low_extraction_confidence")

    if buyer_context_signal_count == 0:
        return qualification(False, "thin_buyer_context")

    if strong_pain_signal_count == 0:
        return qualification(False, "low_pain_intensity")

    if company_count <= 1 and _looks_vendor_fix_only(cluster, signals):
        return qualification(False, "vendor_fix_only")

    has_cross_tool_pattern = company_count >= 2 or (
        len(general_signals) >= 3 and general_source_count >= 2
    )
    if not has_cross_tool_pattern:
        return qualification(False, "no_cross_tool_pattern")

    if _looks_off_niche(cluster, signals, context):
        return qualification(False, "off_niche")

    return qualification(True, None)


def _buyer_context_signal_count(signals: list[Signal]) -> int:
    return sum(
        1
        for signal in signals
        if signal.user_type
        or signal.job_to_be_done
        or signal.current_workaround
        or signal.willingness_to_pay is True
    )


def _strong_pain_signal_count(signals: list[Signal]) -> int:
    return sum(
        1
        for signal in signals
        if signal.urgency in {"medium", "high"}
        or signal.severity in {"medium", "high"}
        or signal.willingness_to_pay is True
    )


def _average_signal_confidence(signals: list[Signal]) -> float:
    if not signals:
        return 0.0
    return round(sum(signal.confidence for signal in signals) / len(signals), 3)


def _most_common(values: list[str], *, fallback: str | None) -> str | None:
    if not values:
        return fallback
    return Counter(values).most_common(1)[0][0]


def _pain_summary(cluster: SignalCluster, signals: list[Signal]) -> str:
    if cluster.summary:
        return cluster.summary
    return signals[0].pain


def _why_it_matters(
    cluster: SignalCluster,
    signals: list[Signal],
    context: OpportunitySynthesisContext | None,
) -> str:
    willing_count = sum(
        1 for signal in signals if signal.willingness_to_pay is True
    )
    base = (
        f"{cluster.frequency} evidence item(s) cluster around {cluster.theme} "
        f"with an average opportunity score of {cluster.average_score:.1f}. "
        f"{willing_count} signal(s) include willingness-to-pay evidence."
    )
    if context and context.objective:
        return f"{base} This maps to the current research objective: {context.objective}."
    return base


def _suggested_wedge(category: str | None, workaround: str | None) -> str:
    if workaround:
        return (
            f"Build a focused {category.lower()} workflow that removes the "
            f"repeated workaround: {workaround}."
        )
    return f"Build a focused {category.lower()} workflow for this repeated pain."


def _infer_unmet_need_type(
    cluster: SignalCluster,
    signals: list[Signal],
) -> UnmetNeedType:
    text = _normalized_text(
        " ".join(
            [
                cluster.theme,
                cluster.summary,
                *[signal.pain for signal in signals],
                *[signal.job_to_be_done or "" for signal in signals],
                *[signal.current_workaround or "" for signal in signals],
                *[signal.category or "" for signal in signals],
            ]
        )
    )
    if re.search(r"\b(cost|price|pricing|expensive|budget|pay|paid|money|margin|revenue)\b", text):
        return "money"
    if re.search(r"\b(slow|hours?|minutes?|time|manual|delay|wait|deadline|weekly|daily)\b", text):
        return "time"
    if re.search(r"\b(workaround|manual|tedious|effort|complex|setup|configure|copy|export|import)\b", text):
        return "effort"
    if re.search(r"\b(can'?t|cannot|missing|lack|unsupported|unable|limit|capability|feature)\b", text):
        return "capability"
    return "fit"


def _confidence_for(cluster: SignalCluster, signals: list[Signal]) -> float:
    score_component = min(cluster.average_score / 10.0, 1.0) * 0.45
    evidence_count = max(cluster.frequency, len(signals))
    source_diversity = _source_diversity(signals)
    evidence_component = min(evidence_count, 5) / 5 * 0.25
    source_component = min(source_diversity, 3) / 3 * 0.20
    average_signal_confidence = (
        sum(signal.confidence for signal in signals) / len(signals)
        if signals
        else 0.0
    )
    quality_component = min(average_signal_confidence, 1.0) * 0.10
    confidence = min(
        score_component
        + evidence_component
        + source_component
        + quality_component,
        1.0,
    )
    if evidence_count < 2:
        confidence = min(confidence, 0.39)
    elif evidence_count < 3 and source_diversity < 2:
        confidence = min(confidence, 0.55)
    return round(confidence, 2)


def _cluster_content(
    cluster: SignalCluster,
    signals: list[Signal],
    context: OpportunitySynthesisContext | None,
) -> str:
    user_types = list({s.user_type for s in signals if s.user_type})
    categories = list({s.category for s in signals if s.category})
    workarounds = list({s.current_workaround for s in signals if s.current_workaround})
    wtp_count = sum(1 for s in signals if s.willingness_to_pay is True)
    competitor_ids = list({s.niche_company_id for s in signals if s.niche_company_id})
    market_ids = list({s.niche_id for s in signals if s.niche_id})

    lines = [
        "research_context:",
        f"niche_name: {context.niche_name if context and context.niche_name else 'unknown'}",
        f"target_user: {context.target_user if context and context.target_user else 'unknown'}",
        f"objective: {context.objective if context and context.objective else 'unknown'}",
        (
            "extra_instructions: "
            f"{context.extra_instructions if context and context.extra_instructions else 'none'}"
        ),
        "cluster:",
        f"theme: {cluster.theme}",
        f"summary: {cluster.summary}",
        f"frequency: {cluster.frequency}",
        f"average_score: {cluster.average_score:.1f}",
        f"source_diversity: {_source_diversity(signals)}",
        f"wtp_signals: {wtp_count}",
        f"market_ids: {', '.join(market_ids) or 'unknown'}",
        f"competitor_ids: {', '.join(competitor_ids) or 'unknown'}",
        f"user_types: {', '.join(user_types) or 'unknown'}",
        f"categories: {', '.join(categories) or 'unknown'}",
        f"workarounds: {', '.join(workarounds) or 'none mentioned'}",
        "evidence_items:",
    ]
    for signal in signals:
        lines.extend(_signal_evidence_lines(signal))
    return "\n".join(lines)


def _context_ignores_cluster(
    context: OpportunitySynthesisContext | None,
    cluster: SignalCluster,
    signals: list[Signal],
) -> bool:
    if context is None:
        return False
    ignored_themes = {
        item.strip().lower()
        for item in context.ignored_themes or []
        if item.strip()
    }
    ignored_categories = {
        item.strip().lower()
        for item in context.ignored_categories or []
        if item.strip()
    }
    theme = cluster.theme.strip().lower()
    if theme in ignored_themes:
        return True
    signal_categories = {
        signal.category.strip().lower()
        for signal in signals
        if signal.category and signal.category.strip()
    }
    return bool(signal_categories.intersection(ignored_categories))


def _looks_off_niche(
    cluster: SignalCluster,
    signals: list[Signal],
    context: OpportunitySynthesisContext | None,
) -> bool:
    if context is None:
        return False
    context_keywords = _keywords(
        " ".join(
            item
            for item in [
                context.niche_name,
                context.target_user,
                context.objective,
                context.extra_instructions,
            ]
            if item
        )
    )
    if len(context_keywords) < 2:
        return False

    evidence_keywords = _keywords(
        " ".join(
            [
                cluster.theme,
                cluster.summary,
                *[signal.pain for signal in signals],
                *[signal.job_to_be_done or "" for signal in signals],
                *[signal.user_type or "" for signal in signals],
                *[signal.category or "" for signal in signals],
                *[signal.evidence_text or "" for signal in signals],
            ]
        )
    )
    if len(evidence_keywords) < 3:
        return False
    return not bool(context_keywords.intersection(evidence_keywords))


def _looks_vendor_fix_only(cluster: SignalCluster, signals: list[Signal]) -> bool:
    text = _normalized_text(
        " ".join(
            [
                cluster.theme,
                cluster.summary,
                *[signal.pain for signal in signals],
                *[signal.current_workaround or "" for signal in signals],
                *[signal.category or "" for signal in signals],
                *[signal.evidence_text or "" for signal in signals],
            ]
        )
    )
    return bool(
        re.search(
            r"\b(bug|broken|crash|crashes|defect|fix|glitch|issue|regression)\b",
            text,
        )
        or re.search(r"\b(add|allow|customi[sz]e|support|improve)\b.{0,60}\b(feature|setting|button|field|export|import|title|ui)\b", text)
    )


def _keywords(text: str) -> set[str]:
    stopwords = {
        "about",
        "across",
        "and",
        "are",
        "build",
        "for",
        "from",
        "into",
        "market",
        "niche",
        "over",
        "product",
        "products",
        "teams",
        "that",
        "the",
        "their",
        "this",
        "tool",
        "tools",
        "users",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 3 and token not in stopwords
    }


def _normalized_text(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def _signal_evidence_lines(signal: Signal) -> list[str]:
    lines = [
        f"  - signal_id: {signal.id}",
        f"    company_id: {signal.niche_company_id or 'unknown'}",
        f"    market_id: {signal.niche_id or 'unknown'}",
        f"    pain: {signal.pain}",
        f"    user_type: {signal.user_type or 'unknown'}",
        f"    job_to_be_done: {signal.job_to_be_done or 'unknown'}",
        f"    current_workaround: {signal.current_workaround or 'none mentioned'}",
        f"    urgency: {signal.urgency}",
        f"    severity: {signal.severity}",
        f"    willingness_to_pay: {_format_bool(signal.willingness_to_pay)}",
        f"    category: {signal.category or 'unknown'}",
        f"    extraction_confidence: {signal.confidence:.2f}",
    ]
    if signal.evidence_text:
        lines.append(f"    evidence_text: {signal.evidence_text}")
    if signal.evidence_url:
        lines.append(f"    evidence_url: {signal.evidence_url}")
    return lines


def _source_diversity(signals: list[Signal]) -> int:
    sources = {_source_key(signal) for signal in signals}
    sources.discard(None)
    if not sources and signals:
        return 1
    return len(sources)


def _high_signal_source_diversity(signals: list[Signal]) -> int:
    sources = {
        _source_key(signal)
        for signal in signals
        if _is_high_signal_source(signal)
    }
    sources.discard(None)
    return len(sources)


def _is_high_signal_source(signal: Signal) -> bool:
    source_key = _source_key(signal) or ""
    post_source = signal.post_id.split(":", 1)[0].lower() if ":" in signal.post_id else ""
    combined = f"{source_key} {post_source}"
    high_signal_hints = {
        "github.com",
        "api.github.com",
        "stackoverflow.com",
        "stackexchange.com",
        "g2.com",
        "capterra.com",
        "trustradius.com",
        "trustpilot.com",
        "reddit.com",
        "news.ycombinator.com",
        "hn.algolia.com",
        "producthunt.com",
    }
    if any(hint in combined for hint in high_signal_hints):
        return True
    return any(
        token in combined
        for token in {
            "github",
            "stackoverflow",
            "hackernews",
            "reddit",
            "discourse",
            "forum",
            "reviews",
        }
    )


def _source_key(signal: Signal) -> str | None:
    if signal.evidence_url:
        parsed = urlparse(signal.evidence_url)
        if parsed.netloc:
            return parsed.netloc.lower()
    if ":" in signal.post_id:
        return signal.post_id.split(":", 1)[0].lower()
    return None


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "true" if value else "false"


def merge_near_duplicate_opportunities(
    opportunities: list[Opportunity],
) -> list[Opportunity]:
    merged: list[Opportunity] = []
    for candidate in opportunities:
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(merged)
                if _opportunity_similarity(existing, candidate) >= 0.52
            ),
            None,
        )
        if duplicate_index is None:
            merged.append(candidate)
            continue
        merged[duplicate_index] = _merge_opportunity(
            merged[duplicate_index],
            candidate,
        )
    return merged


def _merge_opportunity(existing: Opportunity, duplicate: Opportunity) -> Opportunity:
    evidence_signal_ids = list(
        dict.fromkeys(existing.evidence_signal_ids + duplicate.evidence_signal_ids)
    )
    return Opportunity.create(
        id=existing.id,
        cluster_id=existing.cluster_id,
        title=existing.title,
        target_user=existing.target_user,
        pain_summary=existing.pain_summary,
        why_it_matters=existing.why_it_matters,
        suggested_wedge=existing.suggested_wedge,
        evidence_count=max(
            existing.evidence_count + duplicate.evidence_count,
            len(evidence_signal_ids),
        ),
        confidence=max(existing.confidence, duplicate.confidence),
        evidence_signal_ids=evidence_signal_ids,
        unmet_need_type=existing.unmet_need_type or duplicate.unmet_need_type,
    )


def _opportunity_similarity(left: Opportunity, right: Opportunity) -> float:
    left_tokens = _opportunity_tokens(left)
    right_tokens = _opportunity_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens.intersection(right_tokens))
    return overlap / len(left_tokens.union(right_tokens))


def _opportunity_tokens(opportunity: Opportunity) -> set[str]:
    text = " ".join(
        [
            opportunity.title,
            opportunity.pain_summary,
            opportunity.suggested_wedge,
        ]
    )
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "for",
        "from",
        "in",
        "is",
        "of",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
        "users",
        "user",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in stopwords
    }
