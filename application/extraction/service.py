"""Signal extraction service."""
import json
from dataclasses import dataclass
from datetime import UTC, datetime
import logging

from application.extraction.extraction_schema import (
    SIGNAL_EXTRACTION_RESPONSE_SCHEMA,
    SignalCandidate,
    validate_extraction_response,
)
from domain.post import RawPost
from domain.signal import Signal
from infrastructure.llm import LLMClient
from shared.errors import ExtractionError
from shared.logger import get_logger, log_event


SIGNAL_EXTRACTION_PROMPT = """
Extract one competitor customer complaint or market pain signal from the post.

Return JSON only. The response must match this contract:
- has_signal: boolean
- is_about_competitor: boolean
- competitor_match_reason: string or null
- signal: object when has_signal is true, otherwise null

Set has_signal to true only for concrete evidence of product pain, missing
features, pricing friction, switching intent, unmet workflow needs, or current
workarounds. If the post is generic news, praise, spam, meta discussion, or lacks
a clear pain, return has_signal=false, is_about_competitor=false,
competitor_match_reason=null, and signal=null.

If agent_ignored_themes or agent_ignored_categories are present in the post
context, treat them as learned negative feedback. Do not extract a signal when
the post mainly matches those ignored patterns unless it contains unusually
concrete, recent buyer pain with severity or switching intent.

If agent_extra_instructions are present, use them as the user's current research
brief when deciding whether the post is in scope.

When competitor context is provided, set is_about_competitor to true only if the
pain is about that competitor, its product, or a direct customer workaround for
that competitor. Do not mark unrelated products mentioned inside a monitored
source as competitor pain.

When has_signal is true, signal must include:
- pain: non-empty concise complaint
- user_type: affected user segment or null
- job_to_be_done: what the user is trying to accomplish or null
- current_workaround: workaround mentioned or null
- urgency: integer 1-5
- severity: integer 1-5
- willingness_to_pay: integer 1-5
- category: short product/problem category or null
- confidence: number from 0.0 to 1.0
""".strip()

logger = get_logger(__name__)


@dataclass(frozen=True)
class SignalExtractionResult:
    """Result of extracting a signal candidate from a raw post."""

    post_id: str
    has_signal: bool
    signal: Signal | None = None


class ExtractionService:
    """Extracts structured signal candidates from raw posts using an LLM client."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def extract(self, post: RawPost) -> SignalExtractionResult:
        try:
            raw_json = self.llm_client.generate_structured_response(
                SIGNAL_EXTRACTION_PROMPT,
                self._post_content(post),
                SIGNAL_EXTRACTION_RESPONSE_SCHEMA,
            )
            payload = self._parse_json(raw_json)
            try:
                extraction = validate_extraction_response(payload)
            except ValueError as exc:
                raise ExtractionError(str(exc)) from exc

            if not extraction.has_signal:
                return SignalExtractionResult(post_id=post.id, has_signal=False)
            if _has_competitor_context(post) and not extraction.is_about_competitor:
                return SignalExtractionResult(post_id=post.id, has_signal=False)
            if extraction.signal is None:
                raise ExtractionError("Extraction JSON must include a signal object")

            try:
                signal = self._signal_from_candidate(post, extraction.signal)
            except ValueError as exc:
                raise ExtractionError(str(exc)) from exc
        except ExtractionError as exc:
            log_event(
                logger,
                "extraction_failed",
                level=logging.ERROR,
                post_id=post.id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        except Exception as exc:
            log_event(
                logger,
                "extraction_failed",
                level=logging.ERROR,
                post_id=post.id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

        return SignalExtractionResult(
            post_id=post.id,
            has_signal=True,
            signal=signal,
        )

    def _signal_from_candidate(self, post: RawPost, candidate: SignalCandidate) -> Signal:
        return Signal.create(
            id=f"signal:{post.id}",
            post_id=post.id,
            pain=candidate.pain,
            user_type=candidate.user_type,
            job_to_be_done=candidate.job_to_be_done,
            current_workaround=candidate.current_workaround,
            urgency=_level_from_score(candidate.urgency),
            severity=_level_from_score(candidate.severity),
            willingness_to_pay=_willingness_from_score(candidate.willingness_to_pay),
            category=candidate.category,
            confidence=candidate.confidence,
            niche_company_id=_metadata_text(post, "competitor_id"),
            niche_id=_metadata_text(post, "market_id"),
            evidence_url=post.url,
            evidence_text=self._evidence_text(post),
            detected_at=datetime.now(tz=UTC),
        )

    def _parse_json(self, raw_json: str) -> dict:
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ExtractionError("LLM returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise ExtractionError("Extraction JSON must be an object")

        return payload

    def _post_content(self, post: RawPost) -> str:
        return "\n".join(
            [
                f"source: {post.source}",
                f"competitor_id: {_metadata_text(post, 'competitor_id') or ''}",
                f"competitor_name: {_metadata_text(post, 'competitor_name') or ''}",
                f"market_id: {_metadata_text(post, 'market_id') or ''}",
                f"market_name: {_metadata_text(post, 'market_name') or ''}",
                f"market_target_user: {_metadata_text(post, 'market_target_user') or ''}",
                f"market_idea_prompt: {_metadata_text(post, 'market_idea_prompt') or ''}",
                f"agent_extra_instructions: {_metadata_text(post, 'agent_extra_instructions') or ''}",
                f"agent_ignored_themes: {_metadata_text(post, 'agent_ignored_themes') or ''}",
                f"agent_ignored_categories: {_metadata_text(post, 'agent_ignored_categories') or ''}",
                f"competitor_domain: {_metadata_text(post, 'competitor_domain') or ''}",
                f"competitor_website: {_metadata_text(post, 'competitor_website') or ''}",
                f"source_type: {_metadata_text(post, 'source_type') or ''}",
                f"source_guidance: {_source_guidance(post)}",
                f"url: {post.url or ''}",
                f"title: {post.title}",
                f"body: {post.body}",
            ]
        )

    def _evidence_text(self, post: RawPost) -> str:
        body = post.body.strip()
        if body:
            return body[:1000]
        return post.title[:1000]


def _metadata_text(post: RawPost, key: str) -> str | None:
    value = post.metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _has_competitor_context(post: RawPost) -> bool:
    return any(
        _metadata_text(post, key)
        for key in ("competitor_id", "competitor_name", "competitor_domain")
    )


def _source_guidance(post: RawPost) -> str:
    source_type = (_metadata_text(post, "source_type") or post.source).lower()
    locator = (post.url or "").lower()
    combined = f"{source_type} {locator}"
    if "github" in combined:
        return (
            "Treat issue reports, reproduction steps, maintainer won't-fix replies, "
            "and repeated feature requests as strong evidence. Ignore routine pull "
            "request/changelog noise."
        )
    if "stackoverflow" in combined or "stackexchange" in combined:
        return (
            "Treat blocked implementation questions and repeated workarounds as "
            "evidence of unmet workflow needs. Ignore solved syntax-only questions."
        )
    if any(token in combined for token in ("g2", "capterra", "trustradius", "trustpilot", "review")):
        return (
            "Prioritize dislike, switching, comparison, pricing, and support complaints "
            "from buyer/user review text."
        )
    if any(token in combined for token in ("reddit", "hackernews", "ycombinator", "forum", "discourse")):
        return (
            "Extract concrete user pain, switching intent, and workaround discussions. "
            "Ignore jokes, broad opinions, hiring posts, tutorials, and hype."
        )
    if any(token in combined for token in ("changelog", "release", "pricing", "roadmap")):
        return (
            "Use owned-content signals as competitive context only. Extract a pain "
            "signal only when unmet user need or customer demand is explicit."
        )
    return (
        "Extract only concrete buyer/user pain with evidence. Ignore generic marketing, "
        "SEO summaries, news, or vague commentary."
    )


def _level_from_score(score: int) -> str:
    if score >= 4:
        return "high"
    if score == 3:
        return "medium"
    return "low"


def _willingness_from_score(score: int) -> bool | None:
    if score >= 4:
        return True
    if score <= 2:
        return False
    return None
