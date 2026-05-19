"""Domain models for clustered signals."""
from dataclasses import dataclass

from domain.score.severity import Severity


@dataclass(frozen=True)
class SignalCluster:
    """Recurring signal cluster derived from public interactions."""

    theme: str
    frequency: int
    severity: Severity
    interaction_ids: list[str]
    excerpts: list[str]
