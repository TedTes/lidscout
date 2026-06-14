"""Aggregate feedback diagnostics for niche research agents."""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from domain.agent import AgentFeedback


@dataclass(frozen=True)
class FeedbackReasonCount:
    """Count for one structured feedback reason."""

    reason: str
    count: int


@dataclass(frozen=True)
class FeedbackComment:
    """Recent operator-facing qualitative feedback."""

    opportunity_id: str
    action: str
    comment: str
    reason: str | None
    created_at: str | None


@dataclass(frozen=True)
class AgentFeedbackSummary:
    """Feedback diagnostics for one user niche."""

    market_id: str
    feedback_count: int
    saved_count: int
    dismissed_count: int
    positive_training_count: int
    negative_training_count: int
    actioned_opportunity_count: int
    dismiss_rate: float
    dismiss_reasons: list[FeedbackReasonCount]
    recent_comments: list[FeedbackComment]


def build_agent_feedback_summary(
    *,
    market_id: str,
    feedback: list[AgentFeedback],
    recent_comment_limit: int = 5,
) -> AgentFeedbackSummary:
    """Build aggregate feedback diagnostics from persisted feedback."""
    saved_count = sum(1 for item in feedback if item.action == "save")
    dismissed_count = sum(1 for item in feedback if item.action == "dismiss")
    positive_training_count = sum(
        1 for item in feedback if item.action == "more_like_this"
    )
    negative_training_count = sum(
        1 for item in feedback if item.action == "less_like_this"
    )
    actioned_ids = {
        item.opportunity_id
        for item in feedback
        if item.action in {"save", "dismiss"}
    }
    actioned_count = len(actioned_ids)
    dismiss_rate = (
        round(dismissed_count / actioned_count, 4)
        if actioned_count
        else 0.0
    )
    reason_counts = Counter(
        item.reason
        for item in feedback
        if item.action == "dismiss" and item.reason
    )
    recent_comments = [
        FeedbackComment(
            opportunity_id=item.opportunity_id,
            action=item.action,
            comment=item.comment or "",
            reason=item.reason,
            created_at=item.created_at.isoformat() if item.created_at else None,
        )
        for item in sorted(
            feedback,
            key=lambda item: item.updated_at or item.created_at or datetime.min,
            reverse=True,
        )
        if item.comment
    ][:recent_comment_limit]
    return AgentFeedbackSummary(
        market_id=market_id,
        feedback_count=len(feedback),
        saved_count=saved_count,
        dismissed_count=dismissed_count,
        positive_training_count=positive_training_count,
        negative_training_count=negative_training_count,
        actioned_opportunity_count=actioned_count,
        dismiss_rate=dismiss_rate,
        dismiss_reasons=[
            FeedbackReasonCount(reason=reason, count=count)
            for reason, count in reason_counts.most_common()
        ],
        recent_comments=recent_comments,
    )
