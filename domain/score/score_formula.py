"""Weighted opportunity score formula."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.signal import Signal


LEVEL_COMPONENT_SCORES = {
    "low": 2.0,
    "medium": 6.0,
    "high": 10.0,
}


def calculate_opportunity_score(signal: Signal) -> float:
    """Calculate a weighted opportunity score from 0.0 to 10.0."""
    urgency = LEVEL_COMPONENT_SCORES[signal.urgency]
    severity = LEVEL_COMPONENT_SCORES[signal.severity]
    willingness_to_pay = _willingness_component(signal.willingness_to_pay)
    confidence = signal.confidence * 10.0

    score = (
        urgency * 0.25
        + severity * 0.25
        + willingness_to_pay * 0.30
        + confidence * 0.20
    )
    return round(max(0.0, min(score, 10.0)), 2)


def _willingness_component(willingness_to_pay: bool | None) -> float:
    if willingness_to_pay is True:
        return 10.0
    return 0.0
