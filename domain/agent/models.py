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
    "alert_created",
    "follow_up_recorded",
    "post_evaluating",
    "post_accepted",
    "post_filtered",
    "theme_promoted",
    "theme_rejected",
    "actions_executed",
]

AgentAlertSeverity = Literal["info", "warning", "critical"]
AgentAlertStatus = Literal["open", "acknowledged"]

AgentFeedbackAction = Literal[
    "save",
    "dismiss",
    "more_like_this",
    "less_like_this",
]

AgentFollowUpStatus = Literal["queued", "answered", "dismissed"]

AgentActionType = Literal[
    "scan_sources",
    "pause_source",
    "suggest_source",
    "answer_follow_up",
    "send_alert",
    "wait",
]

AgentActionStatus = Literal[
    "proposed",
    "approved",
    "dismissed",
    "completed",
    "failed",
]


@dataclass(frozen=True)
class AgentAction:
    """A planned action the agent can propose or execute."""

    id: str
    user_niche_id: str
    action_type: AgentActionType
    status: AgentActionStatus
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_niche_id: str,
        action_type: str,
        id: str | None = None,
        status: str = "proposed",
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> "AgentAction":
        """Create a validated planned agent action."""
        action_id = (id or f"agent-action-{uuid4().hex}").strip()
        normalized_user_niche_id = user_niche_id.strip()
        normalized_action_type = action_type.strip().lower()
        normalized_status = status.strip().lower()

        if not action_id:
            raise ValueError("id is required")
        if not normalized_user_niche_id:
            raise ValueError("user_niche_id is required")
        if not normalized_action_type:
            raise ValueError("action_type is required")
        if normalized_action_type not in {
            "scan_sources",
            "pause_source",
            "suggest_source",
            "answer_follow_up",
            "send_alert",
            "wait",
        }:
            raise ValueError("unsupported action_type")
        if not normalized_status:
            raise ValueError("status is required")
        if normalized_status not in {
            "proposed",
            "approved",
            "dismissed",
            "completed",
            "failed",
        }:
            raise ValueError("unsupported status")

        created = created_at or datetime.now(tz=UTC)
        return cls(
            id=action_id,
            user_niche_id=normalized_user_niche_id,
            action_type=normalized_action_type,  # type: ignore[arg-type]
            status=normalized_status,  # type: ignore[arg-type]
            reason=_clean_optional(reason),
            metadata=metadata or {},
            created_at=created,
            completed_at=completed_at,
        )


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
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_niche_id: str,
        opportunity_id: str,
        action: str,
        id: str | None = None,
        reason: str | None = None,
        created_at: datetime | None = None,
    ) -> "AgentFeedback":
        """Create validated agent feedback."""
        feedback_id = (id or f"agent-feedback-{uuid4().hex}").strip()
        normalized_user_niche_id = user_niche_id.strip()
        normalized_opportunity_id = opportunity_id.strip()
        normalized_action = action.strip().lower()

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

        return cls(
            id=feedback_id,
            user_niche_id=normalized_user_niche_id,
            opportunity_id=normalized_opportunity_id,
            action=normalized_action,  # type: ignore[arg-type]
            reason=_clean_optional(reason),
            created_at=created_at or datetime.now(tz=UTC),
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
            "alert_created",
            "follow_up_recorded",
            "post_evaluating",
            "post_accepted",
            "post_filtered",
            "theme_promoted",
            "theme_rejected",
            "actions_executed",
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


@dataclass(frozen=True)
class AgentAlert:
    """One proactive agent alert for a niche."""

    id: str
    user_niche_id: str
    alert_type: str
    title: str
    severity: AgentAlertSeverity = "info"
    status: AgentAlertStatus = "open"
    detail: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    acknowledged_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_niche_id: str,
        alert_type: str,
        title: str,
        id: str | None = None,
        severity: str = "info",
        status: str = "open",
        detail: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        acknowledged_at: datetime | None = None,
    ) -> "AgentAlert":
        """Create a validated proactive alert."""
        alert_id = (id or f"agent-alert-{uuid4().hex}").strip()
        normalized_user_niche_id = user_niche_id.strip()
        normalized_alert_type = alert_type.strip().lower()
        normalized_title = title.strip()
        normalized_severity = severity.strip().lower()
        normalized_status = status.strip().lower()

        if not alert_id:
            raise ValueError("id is required")
        if not normalized_user_niche_id:
            raise ValueError("user_niche_id is required")
        if not normalized_alert_type:
            raise ValueError("alert_type is required")
        if not normalized_title:
            raise ValueError("title is required")
        if normalized_severity not in {"info", "warning", "critical"}:
            raise ValueError("severity must be info, warning, or critical")
        if normalized_status not in {"open", "acknowledged"}:
            raise ValueError("status must be open or acknowledged")

        created = created_at or datetime.now(tz=UTC)
        return cls(
            id=alert_id,
            user_niche_id=normalized_user_niche_id,
            alert_type=normalized_alert_type,
            title=normalized_title,
            severity=normalized_severity,  # type: ignore[arg-type]
            status=normalized_status,  # type: ignore[arg-type]
            detail=_clean_optional(detail),
            metadata=metadata or {},
            created_at=created,
            acknowledged_at=(
                acknowledged_at
                if normalized_status == "acknowledged"
                else None
            ),
        )

    def acknowledge(self, acknowledged_at: datetime | None = None) -> "AgentAlert":
        """Return an acknowledged copy of this alert."""
        return AgentAlert.create(
            id=self.id,
            user_niche_id=self.user_niche_id,
            alert_type=self.alert_type,
            title=self.title,
            severity=self.severity,
            status="acknowledged",
            detail=self.detail,
            metadata=self.metadata,
            created_at=self.created_at,
            acknowledged_at=acknowledged_at or datetime.now(tz=UTC),
        )


@dataclass(frozen=True)
class AgentFollowUp:
    """A user follow-up question or research instruction for the agent."""

    id: str
    user_niche_id: str
    question: str
    opportunity_id: str | None = None
    cluster_id: str | None = None
    status: AgentFollowUpStatus = "queued"
    response: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        user_niche_id: str,
        question: str,
        id: str | None = None,
        opportunity_id: str | None = None,
        cluster_id: str | None = None,
        status: str = "queued",
        response: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "AgentFollowUp":
        """Create a validated follow-up intent."""
        follow_up_id = (id or f"agent-follow-up-{uuid4().hex}").strip()
        normalized_user_niche_id = user_niche_id.strip()
        normalized_question = question.strip()
        normalized_status = status.strip().lower()

        if not follow_up_id:
            raise ValueError("id is required")
        if not normalized_user_niche_id:
            raise ValueError("user_niche_id is required")
        if not normalized_question:
            raise ValueError("question is required")
        if normalized_status not in {"queued", "answered", "dismissed"}:
            raise ValueError("status must be queued, answered, or dismissed")

        created = created_at or datetime.now(tz=UTC)
        return cls(
            id=follow_up_id,
            user_niche_id=normalized_user_niche_id,
            question=normalized_question,
            opportunity_id=_clean_optional(opportunity_id),
            cluster_id=_clean_optional(cluster_id),
            status=normalized_status,  # type: ignore[arg-type]
            response=_clean_optional(response),
            metadata=metadata or {},
            created_at=created,
            updated_at=updated_at or created,
        )

    def answer(
        self,
        response: str,
        *,
        metadata: dict[str, Any] | None = None,
        updated_at: datetime | None = None,
    ) -> "AgentFollowUp":
        """Return an answered copy of this follow-up."""
        return AgentFollowUp.create(
            id=self.id,
            user_niche_id=self.user_niche_id,
            question=self.question,
            opportunity_id=self.opportunity_id,
            cluster_id=self.cluster_id,
            status="answered",
            response=response,
            metadata={**self.metadata, **(metadata or {})},
            created_at=self.created_at,
            updated_at=updated_at or datetime.now(tz=UTC),
        )

    def dismiss(
        self,
        *,
        metadata: dict[str, Any] | None = None,
        updated_at: datetime | None = None,
    ) -> "AgentFollowUp":
        """Return a dismissed copy of this follow-up."""
        return AgentFollowUp.create(
            id=self.id,
            user_niche_id=self.user_niche_id,
            question=self.question,
            opportunity_id=self.opportunity_id,
            cluster_id=self.cluster_id,
            status="dismissed",
            response=self.response,
            metadata={**self.metadata, **(metadata or {})},
            created_at=self.created_at,
            updated_at=updated_at or datetime.now(tz=UTC),
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
