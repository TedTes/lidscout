"""Durable accumulated theme domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
import uuid

ThemeStatus = Literal["emerging", "qualified", "rejected", "archived"]
ThemeAssignmentMethod = Literal[
    "auto_high_confidence",
    "auto_borderline_llm",
    "seed_new_theme",
    "manual",
]


@dataclass(frozen=True)
class Theme:
    """Durable unmet-need cluster accumulated across pipeline runs."""

    id: str
    user_niche_id: str
    title: str
    summary: str
    status: ThemeStatus = "emerging"
    niche_id: str | None = None
    qualification_reason: str | None = None
    finding_count: int = 0
    source_count: int = 0
    company_count: int = 0
    average_confidence: float = 0.0
    latest_finding_at: datetime | None = None
    last_qualified_at: datetime | None = None
    last_synthesized_at: datetime | None = None
    centroid_embedding: list[float] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        user_niche_id: str,
        title: str,
        summary: str,
        status: ThemeStatus = "emerging",
        niche_id: str | None = None,
        qualification_reason: str | None = None,
        finding_count: int = 0,
        source_count: int = 0,
        company_count: int = 0,
        average_confidence: float = 0.0,
        latest_finding_at: datetime | None = None,
        last_qualified_at: datetime | None = None,
        last_synthesized_at: datetime | None = None,
        centroid_embedding: list[float] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Theme":
        theme_id = (id or str(uuid.uuid4())).strip()
        cleaned_user_niche_id = user_niche_id.strip()
        cleaned_title = title.strip()
        cleaned_summary = summary.strip()

        if not theme_id:
            raise ValueError("id is required")
        if not cleaned_user_niche_id:
            raise ValueError("user_niche_id is required")
        if not cleaned_title:
            raise ValueError("title is required")
        if not cleaned_summary:
            raise ValueError("summary is required")
        if status not in {"emerging", "qualified", "rejected", "archived"}:
            raise ValueError("unsupported theme status")
        if finding_count < 0 or source_count < 0 or company_count < 0:
            raise ValueError("theme counts must be non-negative")
        if not 0.0 <= average_confidence <= 1.0:
            raise ValueError("average_confidence must be between 0.0 and 1.0")

        now = datetime.now(tz=UTC)
        return cls(
            id=theme_id,
            user_niche_id=cleaned_user_niche_id,
            title=cleaned_title,
            summary=cleaned_summary,
            status=status,
            niche_id=_clean_optional(niche_id),
            qualification_reason=_clean_optional(qualification_reason),
            finding_count=finding_count,
            source_count=source_count,
            company_count=company_count,
            average_confidence=round(average_confidence, 3),
            latest_finding_at=latest_finding_at,
            last_qualified_at=last_qualified_at,
            last_synthesized_at=last_synthesized_at,
            centroid_embedding=_clean_embedding(centroid_embedding),
            created_at=created_at or now,
            updated_at=updated_at or now,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class ThemeFinding:
    """Assignment/provenance link between a durable theme and finding."""

    theme_id: str
    finding_id: str
    assignment_method: ThemeAssignmentMethod
    assigned_at: datetime | None = None
    similarity_score: float | None = None
    llm_decision: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        theme_id: str,
        finding_id: str,
        assignment_method: ThemeAssignmentMethod,
        assigned_at: datetime | None = None,
        similarity_score: float | None = None,
        llm_decision: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ThemeFinding":
        cleaned_theme_id = theme_id.strip()
        cleaned_finding_id = finding_id.strip()
        if not cleaned_theme_id:
            raise ValueError("theme_id is required")
        if not cleaned_finding_id:
            raise ValueError("finding_id is required")
        if assignment_method not in {
            "auto_high_confidence",
            "auto_borderline_llm",
            "seed_new_theme",
            "manual",
        }:
            raise ValueError("unsupported assignment_method")
        if similarity_score is not None and not -1.0 <= similarity_score <= 1.0:
            raise ValueError("similarity_score must be between -1.0 and 1.0")

        return cls(
            theme_id=cleaned_theme_id,
            finding_id=cleaned_finding_id,
            assignment_method=assignment_method,
            assigned_at=assigned_at or datetime.now(tz=UTC),
            similarity_score=similarity_score,
            llm_decision=dict(llm_decision) if llm_decision else None,
            metadata=dict(metadata or {}),
        )


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_embedding(embedding: list[float] | None) -> list[float] | None:
    if embedding is None:
        return None
    return [float(value) for value in embedding]
