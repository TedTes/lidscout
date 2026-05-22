"""Evaluation helpers for relevance filters."""
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol

from application.extraction.relevance_filter import RelevanceResult
from domain.post import RawPost


class RelevanceFilter(Protocol):
    """Evaluation contract for relevance filters."""

    def evaluate(self, post: RawPost) -> RelevanceResult:
        """Return a relevance decision for a post."""
        ...


@dataclass(frozen=True)
class LabeledRelevanceExample:
    """One labeled relevance-filter eval example."""

    id: str
    post: RawPost
    expected_relevant: bool
    expected_rejection_category: str | None
    note: str = ""


@dataclass(frozen=True)
class RelevanceEvalMistake:
    """One relevance eval mismatch."""

    id: str
    expected_relevant: bool
    actual_relevant: bool
    expected_rejection_category: str | None
    actual_rejection_category: str | None
    reason: str


@dataclass(frozen=True)
class RelevanceEvalReport:
    """Aggregate relevance eval metrics."""

    total: int
    true_positive: int
    true_negative: int
    false_positive: int
    false_negative: int
    mistakes: list[RelevanceEvalMistake]

    @property
    def precision(self) -> float:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else 0.0

    @property
    def accuracy(self) -> float:
        return (
            (self.true_positive + self.true_negative) / self.total
            if self.total
            else 0.0
        )

    def to_dict(self) -> dict:
        """Serialize report for CLI output."""
        return {
            "total": self.total,
            "precision": self.precision,
            "recall": self.recall,
            "accuracy": self.accuracy,
            "confusion_matrix": {
                "true_positive": self.true_positive,
                "true_negative": self.true_negative,
                "false_positive": self.false_positive,
                "false_negative": self.false_negative,
            },
            "mistakes": [
                {
                    "id": mistake.id,
                    "expected_relevant": mistake.expected_relevant,
                    "actual_relevant": mistake.actual_relevant,
                    "expected_rejection_category": (
                        mistake.expected_rejection_category
                    ),
                    "actual_rejection_category": mistake.actual_rejection_category,
                    "reason": mistake.reason,
                }
                for mistake in self.mistakes
            ],
        }


def load_labeled_relevance_examples(path: str | Path) -> list[LabeledRelevanceExample]:
    """Load labeled relevance examples from a JSON fixture file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Relevance eval fixture must be a JSON array")
    return [_example_from_payload(item) for item in payload]


def evaluate_relevance_filter(
    relevance_filter: RelevanceFilter,
    examples: list[LabeledRelevanceExample],
) -> RelevanceEvalReport:
    """Run a relevance filter against labeled examples."""
    true_positive = true_negative = false_positive = false_negative = 0
    mistakes: list[RelevanceEvalMistake] = []

    for example in examples:
        result = relevance_filter.evaluate(example.post)
        if example.expected_relevant and result.is_relevant:
            true_positive += 1
        elif not example.expected_relevant and not result.is_relevant:
            true_negative += 1
        elif not example.expected_relevant and result.is_relevant:
            false_positive += 1
        else:
            false_negative += 1

        category_matches = (
            example.expected_relevant
            or example.expected_rejection_category == result.rejection_category
        )
        if (
            example.expected_relevant != result.is_relevant
            or not category_matches
        ):
            mistakes.append(
                RelevanceEvalMistake(
                    id=example.id,
                    expected_relevant=example.expected_relevant,
                    actual_relevant=result.is_relevant,
                    expected_rejection_category=(
                        example.expected_rejection_category
                    ),
                    actual_rejection_category=result.rejection_category,
                    reason=result.reason,
                )
            )

    return RelevanceEvalReport(
        total=len(examples),
        true_positive=true_positive,
        true_negative=true_negative,
        false_positive=false_positive,
        false_negative=false_negative,
        mistakes=mistakes,
    )


def _example_from_payload(payload: object) -> LabeledRelevanceExample:
    if not isinstance(payload, dict):
        raise ValueError("Relevance eval example must be an object")
    post_payload = payload.get("post")
    if not isinstance(post_payload, dict):
        raise ValueError("Relevance eval example post must be an object")
    expected_relevant = payload.get("expected_relevant")
    if not isinstance(expected_relevant, bool):
        raise ValueError("expected_relevant must be a boolean")

    return LabeledRelevanceExample(
        id=_required_string(payload, "id"),
        post=RawPost.create(
            source=_required_string(post_payload, "source"),
            source_id=_required_string(post_payload, "source_id"),
            title=_optional_string(post_payload, "title") or "",
            body=_optional_string(post_payload, "body") or "",
            url=_optional_string(post_payload, "url"),
            metadata=_optional_dict(post_payload, "metadata"),
        ),
        expected_relevant=expected_relevant,
        expected_rejection_category=_optional_string(
            payload,
            "expected_rejection_category",
        ),
        note=_optional_string(payload, "note") or "",
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


def _optional_dict(payload: dict, key: str) -> dict:
    value = payload.get(key, {})
    if isinstance(value, dict):
        return value
    raise ValueError(f"{key} must be an object")
