"""Frequency-to-severity scoring rules."""
from typing import Literal

Severity = Literal["low", "medium", "high"]


def severity_for_frequency(frequency: int) -> Severity:
    """Score a recurring signal by mention frequency."""
    if frequency >= 5:
        return "high"
    if frequency >= 2:
        return "medium"
    return "low"
