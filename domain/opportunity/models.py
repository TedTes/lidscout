"""Domain models for synthesized product opportunities."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Opportunity:
    """Actionable product opportunity synthesized from a signal cluster."""

    id: str
    cluster_id: str
    title: str
    target_user: str
    pain_summary: str
    why_it_matters: str
    suggested_wedge: str
    evidence_count: int
    confidence: float
    evidence_signal_ids: list[str]
    unmet_need_type: str | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        cluster_id: str,
        title: str,
        target_user: str,
        pain_summary: str,
        why_it_matters: str,
        suggested_wedge: str,
        evidence_count: int,
        confidence: float,
        evidence_signal_ids: list[str],
        unmet_need_type: str | None = None,
    ) -> "Opportunity":
        """Create a validated synthesized opportunity entity."""
        opportunity_id = id.strip()
        normalized_cluster_id = cluster_id.strip()
        normalized_title = title.strip()
        normalized_target_user = target_user.strip()
        normalized_pain_summary = pain_summary.strip()
        normalized_why_it_matters = why_it_matters.strip()
        normalized_suggested_wedge = suggested_wedge.strip()
        normalized_signal_ids = [
            str(signal_id).strip()
            for signal_id in evidence_signal_ids
            if str(signal_id).strip()
        ]
        normalized_unmet_need_type = cls._clean_unmet_need_type(unmet_need_type)

        if not opportunity_id:
            raise ValueError("id is required")
        if not normalized_cluster_id:
            raise ValueError("cluster_id is required")
        if not normalized_title:
            raise ValueError("title is required")
        if not normalized_target_user:
            raise ValueError("target_user is required")
        if not normalized_pain_summary:
            raise ValueError("pain_summary is required")
        if not normalized_why_it_matters:
            raise ValueError("why_it_matters is required")
        if not normalized_suggested_wedge:
            raise ValueError("suggested_wedge is required")
        if evidence_count < 1:
            raise ValueError("evidence_count must be at least 1")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not normalized_signal_ids:
            raise ValueError("evidence_signal_ids is required")

        return cls(
            id=opportunity_id,
            cluster_id=normalized_cluster_id,
            title=normalized_title,
            target_user=normalized_target_user,
            pain_summary=normalized_pain_summary,
            why_it_matters=normalized_why_it_matters,
            suggested_wedge=normalized_suggested_wedge,
            evidence_count=evidence_count,
            confidence=round(confidence, 2),
            evidence_signal_ids=normalized_signal_ids,
            unmet_need_type=normalized_unmet_need_type,
        )

    @staticmethod
    def _clean_unmet_need_type(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned not in {"time", "money", "effort", "capability", "fit"}:
            raise ValueError("unmet_need_type must be time, money, effort, capability, or fit")
        return cleaned
