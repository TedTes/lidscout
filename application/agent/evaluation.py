"""Evaluation helpers for adaptive agent behavior."""
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol

from domain.agent import AgentFeedback
from domain.opportunity import Opportunity


class OpportunityRanker(Protocol):
    """Evaluation contract for opportunity rankers."""

    def __call__(
        self,
        opportunities: list[Opportunity],
        feedback: list[AgentFeedback],
    ) -> list[Opportunity]:
        """Return ranked opportunities."""
        ...


@dataclass(frozen=True)
class LabeledAgentRankingExample:
    """One labeled adaptive ranking eval example."""

    id: str
    opportunities: list[Opportunity]
    feedback: list[AgentFeedback]
    expected_top_opportunity_id: str
    note: str = ""


@dataclass(frozen=True)
class AgentRankingEvalMistake:
    """One adaptive ranking eval mismatch."""

    id: str
    expected_top_opportunity_id: str
    actual_top_opportunity_id: str | None


@dataclass(frozen=True)
class AgentRankingEvalReport:
    """Aggregate adaptive ranking eval metrics."""

    total: int
    top_match_count: int
    mistakes: list[AgentRankingEvalMistake]

    @property
    def top_match_rate(self) -> float:
        return self.top_match_count / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        """Serialize report for CLI output."""
        return {
            "total": self.total,
            "top_match_count": self.top_match_count,
            "top_match_rate": self.top_match_rate,
            "mistakes": [
                {
                    "id": mistake.id,
                    "expected_top_opportunity_id": (
                        mistake.expected_top_opportunity_id
                    ),
                    "actual_top_opportunity_id": mistake.actual_top_opportunity_id,
                }
                for mistake in self.mistakes
            ],
        }


def load_labeled_agent_ranking_examples(
    path: str | Path,
) -> list[LabeledAgentRankingExample]:
    """Load labeled adaptive-ranking examples from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Agent eval fixture must be a JSON array")
    return [_example_from_payload(item) for item in payload]


def evaluate_agent_ranker(
    ranker: OpportunityRanker,
    examples: list[LabeledAgentRankingExample],
) -> AgentRankingEvalReport:
    """Run a ranker against labeled adaptive-ranking examples."""
    top_match_count = 0
    mistakes: list[AgentRankingEvalMistake] = []
    for example in examples:
        ranked = ranker(example.opportunities, example.feedback)
        actual_top_id = ranked[0].id if ranked else None
        if actual_top_id == example.expected_top_opportunity_id:
            top_match_count += 1
        else:
            mistakes.append(
                AgentRankingEvalMistake(
                    id=example.id,
                    expected_top_opportunity_id=example.expected_top_opportunity_id,
                    actual_top_opportunity_id=actual_top_id,
                )
            )
    return AgentRankingEvalReport(
        total=len(examples),
        top_match_count=top_match_count,
        mistakes=mistakes,
    )


def _example_from_payload(payload: object) -> LabeledAgentRankingExample:
    if not isinstance(payload, dict):
        raise ValueError("Agent eval example must be an object")
    opportunities_payload = payload.get("opportunities")
    feedback_payload = payload.get("feedback", [])
    if not isinstance(opportunities_payload, list):
        raise ValueError("opportunities must be an array")
    if not isinstance(feedback_payload, list):
        raise ValueError("feedback must be an array")

    return LabeledAgentRankingExample(
        id=_required_string(payload, "id"),
        opportunities=[
            _opportunity_from_payload(item)
            for item in opportunities_payload
        ],
        feedback=[
            _feedback_from_payload(item)
            for item in feedback_payload
        ],
        expected_top_opportunity_id=_required_string(
            payload,
            "expected_top_opportunity_id",
        ),
        note=_optional_string(payload, "note") or "",
    )


def _opportunity_from_payload(payload: object) -> Opportunity:
    if not isinstance(payload, dict):
        raise ValueError("opportunity must be an object")
    return Opportunity.create(
        id=_required_string(payload, "id"),
        cluster_id=_required_string(payload, "cluster_id"),
        title=_required_string(payload, "title"),
        target_user=_required_string(payload, "target_user"),
        pain_summary=_required_string(payload, "pain_summary"),
        why_it_matters=_required_string(payload, "why_it_matters"),
        suggested_wedge=_required_string(payload, "suggested_wedge"),
        evidence_count=_required_int(payload, "evidence_count"),
        confidence=_required_float(payload, "confidence"),
        evidence_signal_ids=_required_string_list(payload, "evidence_signal_ids"),
    )


def _feedback_from_payload(payload: object) -> AgentFeedback:
    if not isinstance(payload, dict):
        raise ValueError("feedback must be an object")
    return AgentFeedback.create(
        id=_required_string(payload, "id"),
        user_niche_id=_required_string(payload, "market_id"),
        opportunity_id=_required_string(payload, "opportunity_id"),
        action=_required_string(payload, "action"),
        reason=_optional_string(payload, "reason"),
    )


def _required_string(payload: dict, key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError(f"{key} must be a non-empty string")


def _optional_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"{key} must be a string or null")


def _required_int(payload: dict, key: str) -> int:
    value = payload.get(key)
    if isinstance(value, int):
        return value
    raise ValueError(f"{key} must be an integer")


def _required_float(payload: dict, key: str) -> float:
    value = payload.get(key)
    if isinstance(value, int | float):
        return float(value)
    raise ValueError(f"{key} must be a number")


def _required_string_list(payload: dict, key: str) -> list[str]:
    value = payload.get(key)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError(f"{key} must be a string array")
