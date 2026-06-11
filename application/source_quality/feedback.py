"""Source quality adjustments derived from opportunity feedback."""
from collections import Counter
from dataclasses import dataclass

from domain.agent import AgentFeedback


SOURCE_CONFIDENCE_FLOOR = 0.3
SOURCE_CONFIDENCE_CEILING = 1.4


@dataclass(frozen=True)
class SourceFeedbackStats:
    """Feedback outcomes attributed to one source."""

    source_id: str
    saved_count: int
    dismissed_count: int
    dismiss_reasons: dict[str, int]

    @property
    def feedback_count(self) -> int:
        return self.saved_count + self.dismissed_count

    @property
    def saved_rate(self) -> float:
        return self.saved_count / self.feedback_count if self.feedback_count else 0.0

    @property
    def dismissed_rate(self) -> float:
        return (
            self.dismissed_count / self.feedback_count
            if self.feedback_count
            else 0.0
        )


def source_feedback_stats(
    *,
    feedback: list[AgentFeedback],
    opportunity_source_ids: dict[str, set[str]],
) -> list[SourceFeedbackStats]:
    """Aggregate save/dismiss feedback for sources backing opportunities."""
    stats: dict[str, dict[str, object]] = {}
    for item in feedback:
        if item.action not in {"save", "dismiss"}:
            continue
        source_ids = opportunity_source_ids.get(item.opportunity_id, set())
        for source_id in source_ids:
            entry = stats.setdefault(
                source_id,
                {
                    "saved_count": 0,
                    "dismissed_count": 0,
                    "dismiss_reasons": Counter(),
                },
            )
            if item.action == "save":
                entry["saved_count"] = int(entry["saved_count"]) + 1
            else:
                entry["dismissed_count"] = int(entry["dismissed_count"]) + 1
                if item.reason:
                    reasons = entry["dismiss_reasons"]
                    if isinstance(reasons, Counter):
                        reasons[item.reason] += 1

    return [
        SourceFeedbackStats(
            source_id=source_id,
            saved_count=int(entry["saved_count"]),
            dismissed_count=int(entry["dismissed_count"]),
            dismiss_reasons=dict(entry["dismiss_reasons"]),
        )
        for source_id, entry in sorted(stats.items())
    ]


def feedback_adjusted_source_confidence(
    *,
    base_confidence: float,
    stats: SourceFeedbackStats | None,
) -> float:
    """Return a bounded source confidence adjusted by attributed feedback."""
    bounded_base = max(0.0, min(1.0, base_confidence))
    if stats is None or stats.feedback_count == 0:
        return bounded_base
    multiplier = 1 + stats.saved_rate - stats.dismissed_rate
    adjusted = bounded_base * multiplier
    return round(
        max(SOURCE_CONFIDENCE_FLOOR, min(SOURCE_CONFIDENCE_CEILING, adjusted)),
        3,
    )
