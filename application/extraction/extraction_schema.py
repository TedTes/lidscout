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


class SignalExtractionPayload(BaseModel):
    """Validated LLM response envelope for signal extraction."""

    has_signal: bool
    signal: SignalCandidate | None = None


SIGNAL_EXTRACTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "has_signal": {
            "type": "boolean",
            "description": "True only when the post contains a concrete complaint or pain signal.",
        },
        "signal": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "pain": {"type": "string"},
                "user_type": {"type": ["string", "null"]},
                "job_to_be_done": {"type": ["string", "null"]},
                "current_workaround": {"type": ["string", "null"]},
                "urgency": {"type": "integer", "minimum": 1, "maximum": 5},
                "severity": {"type": "integer", "minimum": 1, "maximum": 5},
                "willingness_to_pay": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                },
                "category": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "required": [
                "pain",
                "user_type",
                "job_to_be_done",
                "current_workaround",
                "urgency",
                "severity",
                "willingness_to_pay",
                "category",
                "confidence",
            ],
        },
    },
    "required": ["has_signal", "signal"],
}


def validate_extraction_response(payload: dict[str, Any]) -> SignalCandidate | None:
    """Validate an LLM extraction envelope and return its signal candidate."""
    response = SignalExtractionPayload.model_validate(payload)
    if not response.has_signal:
        return None
    if response.signal is None:
        raise ValueError("Extraction JSON must include a signal object")
    return response.signal
