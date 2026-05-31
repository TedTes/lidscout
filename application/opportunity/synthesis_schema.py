"""Schema and prompt for LLM opportunity synthesis."""
from typing import Any

from pydantic import BaseModel, field_validator


OPPORTUNITY_SYNTHESIS_PROMPT = """
You are a product strategist. Given a cluster of public user evidence from a
watched market, write a concise, actionable opportunity card.

Return JSON only. The response must match this contract:
- title: sharp, specific opportunity title (not a template — name the actual problem)
- target_user: the specific user segment most affected
- pain_summary: 1-2 sentences summarising the core pain in plain language
- why_it_matters: business reasoning — the competitor weakness exposed and why
  the supplied evidence suggests a real opening
- suggested_wedge: a concrete, specific product approach to capture this gap

Use only the supplied evidence. Do not invent competitors, users, sources, or
market facts. If the evidence is thin, keep the claim conservative. Do not use
generic language. Do not repeat the cluster theme verbatim as the title. Be
direct and specific about what to build and why.

If there is only one evidence item, frame the opportunity as an early signal,
not a proven market gap. Make the claim narrow and cite the exact workflow or
failure mode visible in the evidence.
""".strip()


OPPORTUNITY_SYNTHESIS_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {
            "type": "string",
            "description": "Sharp, specific opportunity title naming the actual problem.",
        },
        "target_user": {
            "type": "string",
            "description": "The specific user segment most affected by this pain.",
        },
        "pain_summary": {
            "type": "string",
            "description": "1-2 sentences summarising the core pain in plain language.",
        },
        "why_it_matters": {
            "type": "string",
            "description": "Business reasoning for why this represents a real product opening.",
        },
        "suggested_wedge": {
            "type": "string",
            "description": "Concrete, specific product approach to capture this gap.",
        },
    },
    "required": [
        "title",
        "target_user",
        "pain_summary",
        "why_it_matters",
        "suggested_wedge",
    ],
}


class SynthesisCandidate(BaseModel):
    """Validated opportunity fields from an LLM synthesis response."""

    title: str
    target_user: str
    pain_summary: str
    why_it_matters: str
    suggested_wedge: str

    @field_validator("title", "target_user", "pain_summary", "why_it_matters", "suggested_wedge")
    @classmethod
    def must_not_be_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field must not be empty")
        return cleaned


def validate_synthesis_response(payload: dict[str, Any]) -> SynthesisCandidate:
    """Validate an LLM synthesis response envelope."""
    return SynthesisCandidate.model_validate(payload)
