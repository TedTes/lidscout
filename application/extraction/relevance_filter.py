"""Pre-extraction relevance filtering for raw posts."""
import json
from dataclasses import dataclass
from typing import Any
from typing import Literal

from domain.post import RawPost
from infrastructure.llm import LLMClient


RELEVANCE_FILTER_PROMPT = """
Classify whether a raw online post should continue to signal extraction.

Return JSON only. The response must match this contract:
- is_relevant: boolean
- is_about_competitor: boolean
- has_pain_or_request: boolean
- rejection_category: one of empty, wrong_subject, tutorial_or_template,
  promotional, news, job_posting, no_pain_signal, other, or null
- reason: concise explanation
- confidence: number from 0.0 to 1.0

Set is_about_competitor=true only when the post is primarily about the provided
competitor's product experience. If no competitor is provided but market context
is provided, set is_about_competitor=true when the post is about that watched
market or niche. Do not mark incidental mentions, comparisons where another
product is the subject, or unrelated discussions as relevant.

Set has_pain_or_request=true only for dissatisfaction, missing features, pricing
friction, switching intent, workflow pain, reliability issues, or workaround
mentions. Generic praise, tutorials, news, promotions, and hiring posts are not
pain signals.

Set is_relevant=true only when both is_about_competitor and has_pain_or_request
are true.

When agent_ignored_themes or agent_ignored_categories are provided, treat them
as learned negative feedback from the user. Reject posts that mainly match those
patterns unless the post contains unusually concrete, recent, buyer-side pain
with severity or switching intent that should override the prior preference.

When agent_extra_instructions are provided, use them as the user's current
research brief for deciding whether the post belongs in this niche.
""".strip()


RELEVANCE_FILTER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "is_relevant": {"type": "boolean"},
        "is_about_competitor": {"type": "boolean"},
        "has_pain_or_request": {"type": "boolean"},
        "rejection_category": {
            "type": ["string", "null"],
            "enum": [
                "empty",
                "wrong_subject",
                "tutorial_or_template",
                "promotional",
                "news",
                "job_posting",
                "no_pain_signal",
                "other",
                None,
            ],
        },
        "reason": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": [
        "is_relevant",
        "is_about_competitor",
        "has_pain_or_request",
        "rejection_category",
        "reason",
        "confidence",
    ],
}


RejectionCategory = Literal[
    "empty",
    "wrong_subject",
    "tutorial_or_template",
    "promotional",
    "news",
    "job_posting",
    "no_pain_signal",
    "other",
]


@dataclass(frozen=True)
class RelevanceResult:
    """Structured decision from a pre-extraction relevance gate."""

    post_id: str
    is_relevant: bool
    is_about_competitor: bool
    has_pain_or_request: bool
    reason: str
    confidence: float
    rejection_category: RejectionCategory | None = None

    @classmethod
    def accept(
        cls,
        *,
        post_id: str,
        is_about_competitor: bool,
        has_pain_or_request: bool,
        reason: str,
        confidence: float,
    ) -> "RelevanceResult":
        """Build an accepted relevance decision."""
        return cls(
            post_id=post_id,
            is_relevant=True,
            is_about_competitor=is_about_competitor,
            has_pain_or_request=has_pain_or_request,
            reason=reason.strip(),
            confidence=_clamp_confidence(confidence),
        )

    @classmethod
    def reject(
        cls,
        *,
        post_id: str,
        category: RejectionCategory,
        reason: str,
        is_about_competitor: bool = False,
        has_pain_or_request: bool = False,
        confidence: float = 1.0,
    ) -> "RelevanceResult":
        """Build a rejected relevance decision."""
        return cls(
            post_id=post_id,
            is_relevant=False,
            is_about_competitor=is_about_competitor,
            has_pain_or_request=has_pain_or_request,
            reason=reason.strip(),
            confidence=_clamp_confidence(confidence),
            rejection_category=category,
        )


class RuleBasedRelevanceFilter:
    """Cheap first-pass filter that removes obvious non-signal content."""

    def evaluate(self, post: RawPost) -> RelevanceResult:
        """Return a relevance decision without calling an LLM."""
        content_text = _content_text(post)
        normalized_content = content_text.lower()
        if len(normalized_content) < 15:
            return RelevanceResult.reject(
                post_id=post.id,
                category="empty",
                reason="Post content is too short to evaluate.",
            )

        text = _post_text(post)
        normalized_text = text.lower()
        about_competitor = _mentions_competitor(post, normalized_text)
        if _has_competitor_context(post) and not about_competitor:
            return RelevanceResult.reject(
                post_id=post.id,
                category="wrong_subject",
                reason="Post does not mention the monitored competitor context.",
                confidence=0.9,
            )

        category = _obvious_rejection_category(normalized_text)
        if category is not None:
            return RelevanceResult.reject(
                post_id=post.id,
                category=category,
                reason=f"Post looks like {category.replace('_', ' ')} content.",
                is_about_competitor=about_competitor,
                confidence=0.85,
            )

        has_pain_or_request = _has_pain_marker(normalized_text)
        return RelevanceResult.accept(
            post_id=post.id,
            is_about_competitor=about_competitor,
            has_pain_or_request=has_pain_or_request,
            reason=(
                "Post passed hard rejection rules"
                if has_pain_or_request
                else "Post passed hard rejection rules but needs LLM relevance check"
            ),
            confidence=0.65 if has_pain_or_request else 0.4,
        )


class LLMRelevanceFilter:
    """Second-pass relevance classifier for posts that pass hard rules."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def evaluate(self, post: RawPost) -> RelevanceResult:
        """Return a relevance decision from a structured LLM classifier."""
        raw_json = self.llm_client.generate_structured_response(
            RELEVANCE_FILTER_PROMPT,
            _llm_post_content(post),
            RELEVANCE_FILTER_RESPONSE_SCHEMA,
        )
        payload = _parse_relevance_json(raw_json)
        return _result_from_payload(post.id, payload)


def _parse_relevance_json(raw_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM relevance filter returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM relevance filter JSON must be an object")
    return payload


def _result_from_payload(post_id: str, payload: dict[str, Any]) -> RelevanceResult:
    is_relevant = _required_bool(payload, "is_relevant")
    is_about_competitor = _required_bool(payload, "is_about_competitor")
    has_pain_or_request = _required_bool(payload, "has_pain_or_request")
    reason = _required_string(payload, "reason")
    confidence = _required_number(payload, "confidence")
    category = _optional_rejection_category(payload.get("rejection_category"))

    accepted = is_relevant and is_about_competitor and has_pain_or_request
    if accepted:
        return RelevanceResult.accept(
            post_id=post_id,
            is_about_competitor=True,
            has_pain_or_request=True,
            reason=reason,
            confidence=confidence,
        )

    return RelevanceResult.reject(
        post_id=post_id,
        category=category or _infer_rejection_category(
            is_about_competitor,
            has_pain_or_request,
        ),
        reason=reason,
        is_about_competitor=is_about_competitor,
        has_pain_or_request=has_pain_or_request,
        confidence=confidence,
    )


def _llm_post_content(post: RawPost) -> str:
    return "\n".join(
        [
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
            f"url: {post.url or ''}",
            f"title: {post.title}",
            f"body: {post.body}",
        ]
    )


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    raise ValueError(f"LLM relevance filter field {key} must be a boolean")


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"LLM relevance filter field {key} must be a non-empty string")


def _required_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0:
        return float(value)
    raise ValueError(f"LLM relevance filter field {key} must be between 0.0 and 1.0")


def _optional_rejection_category(value: Any) -> RejectionCategory | None:
    if value is None:
        return None
    categories = {
        "empty",
        "wrong_subject",
        "tutorial_or_template",
        "promotional",
        "news",
        "job_posting",
        "no_pain_signal",
        "other",
    }
    if isinstance(value, str) and value in categories:
        return value  # type: ignore[return-value]
    raise ValueError("LLM relevance filter rejection_category is invalid")


def _infer_rejection_category(
    is_about_competitor: bool,
    has_pain_or_request: bool,
) -> RejectionCategory:
    if not is_about_competitor:
        return "wrong_subject"
    if not has_pain_or_request:
        return "no_pain_signal"
    return "other"


def _content_text(post: RawPost) -> str:
    return "\n".join(
        part
        for part in (
            post.title,
            post.body,
        )
        if part
    ).strip()


def _post_text(post: RawPost) -> str:
    return "\n".join(
        part
        for part in (
            _content_text(post),
            post.url or "",
            _metadata_text(post, "domain") or "",
            _metadata_text(post, "source_type") or "",
        )
        if part
    ).strip()


def _has_competitor_context(post: RawPost) -> bool:
    return any(
        _metadata_text(post, key)
        for key in ("competitor_id", "competitor_name", "competitor_domain")
    )


def _mentions_competitor(post: RawPost, normalized_text: str) -> bool:
    terms = _competitor_terms(post)
    if not terms:
        return True
    return any(term in normalized_text for term in terms)


def _competitor_terms(post: RawPost) -> set[str]:
    terms: set[str] = set()
    for key in ("competitor_name", "competitor_domain", "competitor_id"):
        value = _metadata_text(post, key)
        if not value:
            continue
        cleaned = value.lower().replace("https://", "").replace("http://", "")
        cleaned = cleaned.removeprefix("www.").strip().strip("/")
        if cleaned:
            terms.add(cleaned)
        root = cleaned.split(".")[0].replace("-", " ").strip()
        if root and len(root) > 2:
            terms.add(root)
    return terms


def _obvious_rejection_category(text: str) -> RejectionCategory | None:
    if _contains_any(
        text,
        (
            "we're hiring",
            "we are hiring",
            "hiring for",
            "job opening",
            "job posting",
            "apply now",
        ),
    ):
        return "job_posting"
    if _contains_any(
        text,
        (
            "tutorial",
            "template pack",
            "free template",
            "how to build",
            "step by step guide",
        ),
    ):
        return "tutorial_or_template"
    if _contains_any(
        text,
        (
            "launching",
            "we launched",
            "i built",
            "check out my",
            "use code",
            "limited time offer",
        ),
    ):
        return "promotional"
    if _contains_any(
        text,
        (
            "announced today",
            "press release",
            "raises $",
            "raised $",
            "series a",
            "series b",
            "acquired by",
        ),
    ):
        return "news"
    return None


def _has_pain_marker(text: str) -> bool:
    return _contains_any(
        text,
        (
            "can't",
            "cannot",
            "couldn't",
            "doesn't",
            "does not",
            "broken",
            "bug",
            "issue",
            "problem",
            "frustrating",
            "annoying",
            "confusing",
            "hard to",
            "too expensive",
            "pricing",
            "missing",
            "wish",
            "feature request",
            "workaround",
            "manual",
            "switching",
            "alternative",
            "fails",
            "failed",
            "slow",
        ),
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _metadata_text(post: RawPost, key: str) -> str | None:
    value = post.metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))
