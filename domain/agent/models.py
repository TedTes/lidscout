"""Domain models for agent memory and preferences."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from typing import Literal
from uuid import uuid4


AgentActivityType = Literal[
    "run_started",
    "run_completed",
    "sources_scanned",
    "posts_filtered",
    "signals_extracted",
    "clusters_formed",
    "gaps_synthesized",
    "source_failed",
    "feedback_recorded",
    "preferences_updated",
    "brief_updated",
    "post_evaluating",
    "post_accepted",
    "post_filtered",
    "theme_promoted",
    "theme_rejected",
]

AgentFeedbackAction = Literal[
    "save",
    "dismiss",
    "more_like_this",
    "less_like_this",
]



@dataclass(frozen=True)
class AgentPreferences:
    """Persistent per-niche preferences that steer future agent runs."""

    user_niche_id: str
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
        user_niche_id: str,
        preferred_source_families: list[str] | None = None,
        ignored_themes: list[str] | None = None,
        ignored_categories: list[str] | None = None,
        muted_source_ids: list[str] | None = None,
        extra_instructions: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "AgentPreferences":
        """Create validated agent preferences."""
        normalized_id = user_niche_id.strip()
        if not normalized_id:
            raise ValueError("user_niche_id is required")

        created = created_at or datetime.now(tz=UTC)
        return cls(
            user_niche_id=normalized_id,
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
    user_niche_id: str
    opportunity_id: str
    action: AgentFeedbackAction
    reason: str | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_niche_id: str,
        opportunity_id: str,
        action: str,
        id: str | None = None,
        reason: str | None = None,
        comment: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "AgentFeedback":
        """Create validated agent feedback."""
        feedback_id = (id or f"agent-feedback-{uuid4().hex}").strip()
        normalized_user_niche_id = user_niche_id.strip()
        normalized_opportunity_id = opportunity_id.strip()
        normalized_action = action.strip().lower()
        normalized_reason = _clean_optional(reason)
        normalized_comment = _clean_optional(comment)
        created = created_at or datetime.now(tz=UTC)

        if not feedback_id:
            raise ValueError("id is required")
        if not normalized_user_niche_id:
            raise ValueError("user_niche_id is required")
        if not normalized_opportunity_id:
            raise ValueError("opportunity_id is required")
        if normalized_action not in {
            "save",
            "dismiss",
            "more_like_this",
            "less_like_this",
        }:
            raise ValueError("unsupported feedback action")
        if normalized_reason is not None and len(normalized_reason) > 80:
            raise ValueError("reason must be 80 characters or fewer")
        if normalized_comment is not None and len(normalized_comment) > 1000:
            raise ValueError("comment must be 1000 characters or fewer")

        return cls(
            id=feedback_id,
            user_niche_id=normalized_user_niche_id,
            opportunity_id=normalized_opportunity_id,
            action=normalized_action,  # type: ignore[arg-type]
            reason=normalized_reason,
            comment=normalized_comment,
            created_at=created,
            updated_at=updated_at or created,
        )


@dataclass(frozen=True)
class AgentActivity:
    """One user-visible event from a niche research agent."""

    id: str
    user_niche_id: str
    event_type: AgentActivityType
    title: str
    detail: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_niche_id: str,
        event_type: str,
        title: str,
        id: str | None = None,
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> "AgentActivity":
        """Create a validated agent activity event."""
        activity_id = (id or f"agent-activity-{uuid4().hex}").strip()
        normalized_user_niche_id = user_niche_id.strip()
        normalized_event_type = event_type.strip().lower()
        normalized_title = title.strip()

        if not activity_id:
            raise ValueError("id is required")
        if not normalized_user_niche_id:
            raise ValueError("user_niche_id is required")
        if normalized_event_type not in {
            "run_started",
            "run_completed",
            "sources_scanned",
            "posts_filtered",
            "signals_extracted",
            "clusters_formed",
            "gaps_synthesized",
            "source_failed",
            "feedback_recorded",
            "preferences_updated",
            "brief_updated",
            "post_evaluating",
            "post_accepted",
            "post_filtered",
            "theme_promoted",
            "theme_rejected",
        }:
            raise ValueError("unsupported activity event type")
        if not normalized_title:
            raise ValueError("title is required")

        return cls(
            id=activity_id,
            user_niche_id=normalized_user_niche_id,
            event_type=normalized_event_type,  # type: ignore[arg-type]
            title=normalized_title,
            detail=_clean_optional(detail),
            metadata=metadata or {},
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
