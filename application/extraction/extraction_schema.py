"""Schema validation for LLM signal extraction responses."""
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SignalCandidate(BaseModel):
    """Validated signal candidate from an LLM response."""

    pain: str
    user_type: str | None = None
    job_to_be_done: str | None = None
    current_workaround: str | None = None
    urgency: int = Field(..., ge=1, le=5)
    severity: int = Field(..., ge=1, le=5)
    willingness_to_pay: int = Field(..., ge=1, le=5)
    category: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("pain")
    @classmethod
    def pain_must_not_be_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("pain must not be empty")
        return cleaned


def validate_signal_candidate(payload: dict[str, Any]) -> SignalCandidate:
    """Validate raw LLM response data as a signal candidate."""
    return SignalCandidate.model_validate(payload)
