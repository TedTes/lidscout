"""Signal domain entities."""
from dataclasses import dataclass
from typing import Literal

from domain.score import Severity

Urgency = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class Signal:
    """Market or pain signal extracted from a raw post."""

    id: str
    post_id: str
    pain: str
    user_type: str | None
    job_to_be_done: str | None
    current_workaround: str | None
    urgency: Urgency
    severity: Severity
    willingness_to_pay: bool | None
    category: str | None
    confidence: float

    @classmethod
    def create(
        cls,
        *,
        id: str,
        post_id: str,
        pain: str,
        user_type: str | None = None,
        job_to_be_done: str | None = None,
        current_workaround: str | None = None,
        urgency: Urgency = "low",
        severity: Severity = "low",
        willingness_to_pay: bool | None = None,
        category: str | None = None,
        confidence: float = 0.0,
    ) -> "Signal":
        """Create a validated signal entity."""
        signal_id = id.strip()
        normalized_post_id = post_id.strip()
        normalized_pain = pain.strip()

        if not signal_id:
            raise ValueError("id is required")
        if not normalized_post_id:
            raise ValueError("post_id is required")
        if not normalized_pain:
            raise ValueError("pain is required")
        if urgency not in {"low", "medium", "high"}:
            raise ValueError("urgency must be low, medium, or high")
        if severity not in {"low", "medium", "high"}:
            raise ValueError("severity must be low, medium, or high")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        return cls(
            id=signal_id,
            post_id=normalized_post_id,
            pain=normalized_pain,
            user_type=cls._clean_optional(user_type),
            job_to_be_done=cls._clean_optional(job_to_be_done),
            current_workaround=cls._clean_optional(current_workaround),
            urgency=urgency,
            severity=severity,
            willingness_to_pay=willingness_to_pay,
            category=cls._clean_optional(category),
            confidence=confidence,
        )

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
