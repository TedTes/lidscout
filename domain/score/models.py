"""Opportunity score domain model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.signal import Signal


LEVEL_SCORES = {
    "low": 1.0,
    "medium": 3.0,
    "high": 5.0,
}


@dataclass(frozen=True)
class OpportunityScore:
    """Opportunity score computed from a signal."""

    signal_id: str
    total_score: float
    urgency_score: float
    severity_score: float
    willingness_score: float
    confidence_score: float
    reasoning: str

    @classmethod
    def from_signal(cls, signal: Signal) -> "OpportunityScore":
        """Apply the opportunity scoring formula to a signal."""
        urgency_score = LEVEL_SCORES[signal.urgency]
        severity_score = LEVEL_SCORES[signal.severity]
        willingness_score = cls._willingness_score(signal.willingness_to_pay)
        confidence_score = round(signal.confidence * 5.0, 2)
        total_score = round(
            urgency_score + severity_score + willingness_score + confidence_score,
            2,
        )

        return cls(
            signal_id=signal.id,
            total_score=total_score,
            urgency_score=urgency_score,
            severity_score=severity_score,
            willingness_score=willingness_score,
            confidence_score=confidence_score,
            reasoning=(
                f"urgency={signal.urgency}, severity={signal.severity}, "
                f"willingness_to_pay={signal.willingness_to_pay}, "
                f"confidence={signal.confidence:.2f}"
            ),
        )

    @staticmethod
    def _willingness_score(willingness_to_pay: bool | None) -> float:
        if willingness_to_pay is True:
            return 5.0
        if willingness_to_pay is False:
            return 1.0
        return 0.0
