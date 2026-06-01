"""Schema and prompt for LLM opportunity synthesis."""
from typing import Any

from pydantic import BaseModel, field_validator


OPPORTUNITY_SYNTHESIS_PROMPT = """
You are a product strategist. Given a cluster of public user evidence from a
watched market, write a concise, actionable strategic gap card.

Return JSON only. The response must match this contract:
- title: sharp, specific opportunity title in sentence case (not title case)
- target_user: the specific user segment most affected
- pain_summary: 1-2 sentences summarising the core pain in plain language
- why_it_matters: business reasoning — the competitor weakness exposed and why
  the supplied evidence suggests a real opening
- suggested_wedge: a concrete, specific product approach to capture this gap
- unmet_need_type: exactly one of time, money, effort, capability, fit

Use only the supplied evidence. Do not invent competitors, users, sources, or
market facts. If the evidence is thin, keep the claim conservative. Do not use
generic language. Do not repeat the cluster theme verbatim as the title. Be
direct and specific about what to build and why.

A strategic gap is a market-level unmet need that a new product or company
could credibly address. It is not a bug report, missing feature, or UI issue
for one vendor.

Qualifies:
- Across multiple product-analytics tools, users describe data fragmentation
  between warehouses and analytics tools. Wedge: warehouse-native analytics
  that operates without exports.

Does not qualify:
- Mixpanel's data export to BigQuery is slow. Wedge: improve Mixpanel's export
  performance. This is a vendor fix, not a strategic gap.
- Default page titles in a website builder are all the same. Wedge: let users
  customize page titles. This is a single-vendor feature request and off-niche
  for product analytics.

Reject mentally before writing: if the wedge cannot be written without naming
a specific vendor as the subject of the fix, do not turn it into a vendor patch.
Write a vendor-agnostic category-level wedge instead. If the evidence does not
describe friction in accomplishing the watched market's job-to-be-done, keep
the claim narrow and explain the on-niche workflow visible in evidence only.

Classify unmet_need_type as one of:
- time: delays, slow work, waiting, repeated manual time
- money: cost, pricing, waste, revenue, budget, willingness to pay
- effort: manual work, coordination, setup, maintenance, operational toil
- capability: missing ability, unsupported workflow, hard limitation
- fit: poor fit for a user segment, workflow, or context
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
        "unmet_need_type": {
            "type": "string",
            "enum": ["time", "money", "effort", "capability", "fit"],
            "description": "The unmet-need dimension best supported by the evidence.",
        },
    },
    "required": [
        "title",
        "target_user",
        "pain_summary",
        "why_it_matters",
        "suggested_wedge",
        "unmet_need_type",
    ],
}


class SynthesisCandidate(BaseModel):
    """Validated opportunity fields from an LLM synthesis response."""

    title: str
    target_user: str
    pain_summary: str
    why_it_matters: str
    suggested_wedge: str
    unmet_need_type: str

    @field_validator("title", "target_user", "pain_summary", "why_it_matters", "suggested_wedge")
    @classmethod
    def must_not_be_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field must not be empty")
        return cleaned

    @field_validator("unmet_need_type")
    @classmethod
    def unmet_need_type_must_be_supported(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"time", "money", "effort", "capability", "fit"}:
            raise ValueError("unsupported unmet_need_type")
        return cleaned


def validate_synthesis_response(payload: dict[str, Any]) -> SynthesisCandidate:
    """Validate an LLM synthesis response envelope."""
    return SynthesisCandidate.model_validate(payload)
