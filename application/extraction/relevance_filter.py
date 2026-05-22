"""Pre-extraction relevance filtering for raw posts."""
from dataclasses import dataclass
from typing import Literal

from domain.post import RawPost


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
