"""Domain models for agent memory and preferences."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4


AgentFeedbackAction = Literal[
    "save",
    "dismiss",
    "more_like_this",
    "less_like_this",
]


@dataclass(frozen=True)
class AgentPreferences:
    """Persistent per-niche preferences that steer future agent runs."""

    market_id: str
    preferred_source_families: list[str] = field(default_factory=list)
    ignored_themes: list[str] = field(default_factory=list)
    ignored_categories: list[str] = field(default_factory=list)
    muted_source_ids: list[str] = field(default_factory=list)
    extra_instructions: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        market_id: str,
        preferred_source_families: list[str] | None = None,
        ignored_themes: list[str] | None = None,
        ignored_categories: list[str] | None = None,
        muted_source_ids: list[str] | None = None,
        extra_instructions: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "AgentPreferences":
        """Create validated agent preferences."""
        normalized_market_id = market_id.strip()
        if not normalized_market_id:
            raise ValueError("market_id is required")

        created = created_at or datetime.now(tz=UTC)
        return cls(
            market_id=normalized_market_id,
            preferred_source_families=_clean_list(preferred_source_families or []),
            ignored_themes=_clean_list(ignored_themes or []),
            ignored_categories=_clean_list(ignored_categories or []),
            muted_source_ids=_clean_list(muted_source_ids or []),
            extra_instructions=_clean_optional(extra_instructions),
            created_at=created,
            updated_at=updated_at or created,
        )


@dataclass(frozen=True)
class AgentFeedback:
    """A user feedback event that can steer future agent behavior."""

    id: str
    market_id: str
    opportunity_id: str
    action: AgentFeedbackAction
    reason: str | None = None
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        market_id: str,
        opportunity_id: str,
        action: str,
        id: str | None = None,
        reason: str | None = None,
        created_at: datetime | None = None,
    ) -> "AgentFeedback":
        """Create validated agent feedback."""
        feedback_id = (id or f"agent-feedback-{uuid4().hex}").strip()
        normalized_market_id = market_id.strip()
        normalized_opportunity_id = opportunity_id.strip()
        normalized_action = action.strip().lower()

        if not feedback_id:
            raise ValueError("id is required")
        if not normalized_market_id:
            raise ValueError("market_id is required")
        if not normalized_opportunity_id:
            raise ValueError("opportunity_id is required")
        if normalized_action not in {
            "save",
            "dismiss",
            "more_like_this",
            "less_like_this",
        }:
            raise ValueError("unsupported feedback action")

        return cls(
            id=feedback_id,
            market_id=normalized_market_id,
            opportunity_id=normalized_opportunity_id,
            action=normalized_action,  # type: ignore[arg-type]
            reason=_clean_optional(reason),
            created_at=created_at or datetime.now(tz=UTC),
        )


def _clean_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)
    return cleaned


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
