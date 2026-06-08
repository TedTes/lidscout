"""Durable evidence finding domain model."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid

from domain.signal import Signal, Urgency
from domain.score import Severity


@dataclass(frozen=True)
class Finding:
    """Accumulated extracted evidence that can belong to a durable theme."""

    id: str
    user_niche_id: str
    post_id: str
    pain: str
    evidence_text: str
    structured_embedding_text: str
    urgency: Urgency
    severity: Severity
    confidence: float
    niche_id: str | None = None
    source_id: str | None = None
    company_id: str | None = None
    post_title: str | None = None
    source_url: str | None = None
    evidence_url: str | None = None
    affected_user: str | None = None
    job_to_be_done: str | None = None
    current_workaround: str | None = None
    category: str | None = None
    willingness_to_pay: bool | None = None
    detected_at: datetime | None = None
    extracted_at: datetime | None = None
    pipeline_run_id: str | None = None
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        user_niche_id: str,
        post_id: str,
        pain: str,
        evidence_text: str,
        structured_embedding_text: str,
        urgency: Urgency,
        severity: Severity,
        confidence: float,
        niche_id: str | None = None,
        source_id: str | None = None,
        company_id: str | None = None,
        post_title: str | None = None,
        source_url: str | None = None,
        evidence_url: str | None = None,
        affected_user: str | None = None,
        job_to_be_done: str | None = None,
        current_workaround: str | None = None,
        category: str | None = None,
        willingness_to_pay: bool | None = None,
        detected_at: datetime | None = None,
        extracted_at: datetime | None = None,
        pipeline_run_id: str | None = None,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Finding":
        finding_id = (id or str(uuid.uuid4())).strip()
        cleaned_user_niche_id = user_niche_id.strip()
        cleaned_post_id = post_id.strip()
        cleaned_pain = pain.strip()
        cleaned_evidence_text = evidence_text.strip()
        cleaned_embedding_text = structured_embedding_text.strip()

        if not finding_id:
            raise ValueError("id is required")
        if not cleaned_user_niche_id:
            raise ValueError("user_niche_id is required")
        if not cleaned_post_id:
            raise ValueError("post_id is required")
        if not cleaned_pain:
            raise ValueError("pain is required")
        if not cleaned_evidence_text:
            raise ValueError("evidence_text is required")
        if not cleaned_embedding_text:
            raise ValueError("structured_embedding_text is required")
        if urgency not in {"low", "medium", "high"}:
            raise ValueError("urgency must be low, medium, or high")
        if severity not in {"low", "medium", "high"}:
            raise ValueError("severity must be low, medium, or high")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        return cls(
            id=finding_id,
            user_niche_id=cleaned_user_niche_id,
            post_id=cleaned_post_id,
            pain=cleaned_pain,
            evidence_text=cleaned_evidence_text,
            structured_embedding_text=cleaned_embedding_text,
            urgency=urgency,
            severity=severity,
            confidence=round(confidence, 3),
            niche_id=_clean_optional(niche_id),
            source_id=_clean_optional(source_id),
            company_id=_clean_optional(company_id),
            post_title=_clean_optional(post_title),
            source_url=_clean_optional(source_url),
            evidence_url=_clean_optional(evidence_url),
            affected_user=_clean_optional(affected_user),
            job_to_be_done=_clean_optional(job_to_be_done),
            current_workaround=_clean_optional(current_workaround),
            category=_clean_optional(category),
            willingness_to_pay=willingness_to_pay,
            detected_at=detected_at,
            extracted_at=extracted_at or datetime.now(tz=UTC),
            pipeline_run_id=_clean_optional(pipeline_run_id),
            embedding=_clean_embedding(embedding),
            metadata=dict(metadata or {}),
        )

    @classmethod
    def from_signal(
        cls,
        *,
        user_niche_id: str,
        signal: Signal,
        source_id: str | None = None,
        post_title: str | None = None,
        source_url: str | None = None,
        pipeline_run_id: str | None = None,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Finding":
        """Create a durable finding from the current signal extraction model."""
        embedding_text = "\n".join(
            part
            for part in (
                signal.pain,
                signal.user_type,
                signal.job_to_be_done,
                signal.current_workaround,
                signal.category,
            )
            if part
        )
        return cls.create(
            user_niche_id=user_niche_id,
            post_id=signal.post_id,
            pain=signal.pain,
            evidence_text=signal.evidence_text or signal.pain,
            structured_embedding_text=embedding_text or signal.pain,
            urgency=signal.urgency,
            severity=signal.severity,
            confidence=signal.confidence,
            niche_id=signal.niche_id,
            source_id=source_id,
            company_id=signal.niche_company_id,
            post_title=post_title,
            source_url=source_url,
            evidence_url=signal.evidence_url,
            affected_user=signal.user_type,
            job_to_be_done=signal.job_to_be_done,
            current_workaround=signal.current_workaround,
            category=signal.category,
            willingness_to_pay=signal.willingness_to_pay,
            detected_at=signal.detected_at,
            pipeline_run_id=pipeline_run_id,
            embedding=embedding,
            metadata=metadata,
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
