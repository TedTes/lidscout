"""Niche domain entities."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

NicheStatus = Literal["defined", "sourced", "active"]
NicheSourceHealth = Literal["unknown", "active", "failing", "paused"]
UnmetNeedType = Literal["time", "money", "effort", "capability", "fit"]
GapSignalStrength = Literal["weak", "moderate", "strong"]


@dataclass(frozen=True)
class Niche:
    """Shared operator-curated template niche.

    Represents a job-to-be-done + buyer pair. Serves as the template catalog
    shown to users AND the agent's mission definition.

    opportunity_score is always None at definition time — it is computed from
    synthesised gaps after monitoring produces findings. Never assign a value
    at seed time.
    """

    id: str
    job: str
    buyer: str
    category: str
    description: str | None = None
    status: NicheStatus = "defined"
    monitorability_score: float | None = None
    opportunity_score: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        job: str,
        buyer: str,
        category: str,
        description: str | None = None,
        status: NicheStatus = "defined",
        monitorability_score: float | None = None,
        opportunity_score: float | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "Niche":
        niche_id = (id or str(uuid.uuid4())).strip()
        if not niche_id:
            raise ValueError("id is required")
        if not job.strip():
            raise ValueError("job is required")
        if not buyer.strip():
            raise ValueError("buyer is required")
        if not category.strip():
            raise ValueError("category is required")
        now = datetime.now(tz=UTC)
        return cls(
            id=niche_id,
            job=job.strip(),
            buyer=buyer.strip(),
            category=category.strip(),
            description=description.strip() if description else None,
            status=status,
            monitorability_score=monitorability_score,
            opportunity_score=opportunity_score,
            created_at=created_at or now,
            updated_at=updated_at or now,
        )


@dataclass(frozen=True)
class NicheCompany:
    """A tool / competitor serving the niche's job-to-be-done.

    Modelled per-niche for MVP simplicity — a company appearing in multiple
    niches gets duplicate rows. If cross-niche company reuse becomes common,
    replace with a shared companies table + many-to-many join.
    """

    id: str
    niche_id: str
    name: str
    website: str | None = None
    is_primary: bool = True
    created_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        niche_id: str,
        name: str,
        website: str | None = None,
        is_primary: bool = True,
        created_at: datetime | None = None,
    ) -> "NicheCompany":
        if not niche_id.strip():
            raise ValueError("niche_id is required")
        if not name.strip():
            raise ValueError("name is required")
        return cls(
            id=(id or str(uuid.uuid4())).strip(),
            niche_id=niche_id.strip(),
            name=name.strip(),
            website=website.strip() if website else None,
            is_primary=is_primary,
            created_at=created_at or datetime.now(tz=UTC),
        )


@dataclass(frozen=True)
class NicheSource:
    """A candidate monitoring source bound to a niche.

    Sources are bound progressively after niche definition — a niche can exist
    in 'defined' state with zero sources. buyer_voice_verified is set only
    after confirmation that this source contains buyer complaints, not noise.
    """

    id: str
    niche_id: str
    locator: str
    source_type: str
    source_family: str
    is_gate_free: bool
    company_id: str | None = None
    buyer_voice_verified: bool = False
    health_status: NicheSourceHealth = "unknown"
    last_scanned_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        niche_id: str,
        locator: str,
        source_type: str,
        source_family: str,
        is_gate_free: bool,
        company_id: str | None = None,
        buyer_voice_verified: bool = False,
        health_status: NicheSourceHealth = "unknown",
        last_scanned_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "NicheSource":
        if not niche_id.strip():
            raise ValueError("niche_id is required")
        if not locator.strip():
            raise ValueError("locator is required")
        if not source_type.strip():
            raise ValueError("source_type is required")
        if not source_family.strip():
            raise ValueError("source_family is required")
        now = datetime.now(tz=UTC)
        return cls(
            id=(id or str(uuid.uuid4())).strip(),
            niche_id=niche_id.strip(),
            locator=locator.strip(),
            source_type=source_type.strip(),
            source_family=source_family.strip(),
            is_gate_free=is_gate_free,
            company_id=company_id,
            buyer_voice_verified=buyer_voice_verified,
            health_status=health_status,
            last_scanned_at=last_scanned_at,
            created_at=created_at or now,
            updated_at=updated_at or now,
        )


@dataclass(frozen=True)
class Gap:
    """A synthesised product gap — the strategic output of monitoring a niche.

    signal_strength is computed from breadth + depth + recency + source
    diversity. It is never assigned directly by an LLM.
    """

    id: str
    niche_id: str
    title: str
    pain_summary: str
    unmet_need_type: UnmetNeedType
    affected_buyer: str
    suggested_wedge: str
    signal_strength: GapSignalStrength
    breadth: int = 1
    depth: int = 1
    evidence_finding_ids: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        niche_id: str,
        title: str,
        pain_summary: str,
        unmet_need_type: UnmetNeedType,
        affected_buyer: str,
        suggested_wedge: str,
        signal_strength: GapSignalStrength,
        breadth: int = 1,
        depth: int = 1,
        evidence_finding_ids: list[str] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "Gap":
        if not niche_id.strip():
            raise ValueError("niche_id is required")
        if not title.strip():
            raise ValueError("title is required")
        if not pain_summary.strip():
            raise ValueError("pain_summary is required")
        if breadth < 1:
            raise ValueError("breadth must be >= 1")
        if depth < 1:
            raise ValueError("depth must be >= 1")
        now = datetime.now(tz=UTC)
        return cls(
            id=(id or str(uuid.uuid4())).strip(),
            niche_id=niche_id.strip(),
            title=title.strip(),
            pain_summary=pain_summary.strip(),
            unmet_need_type=unmet_need_type,
            affected_buyer=affected_buyer.strip(),
            suggested_wedge=suggested_wedge.strip(),
            signal_strength=signal_strength,
            breadth=breadth,
            depth=depth,
            evidence_finding_ids=evidence_finding_ids or [],
            created_at=created_at or now,
            updated_at=updated_at or now,
        )


@dataclass(frozen=True)
class UserNiche:
    """A user's personal adoption of a niche template.

    Fields are copied from the template at adoption time and are then
    user-editable — changes do not affect the shared template or other users.
    template_niche_id preserves the origin for future reset/propagation features.
    """

    id: str
    user_id: str
    job: str
    buyer: str
    category: str
    status: NicheStatus = "defined"
    template_niche_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str | None = None,
        user_id: str,
        job: str,
        buyer: str,
        category: str,
        status: NicheStatus = "defined",
        template_niche_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> "UserNiche":
        if not user_id.strip():
            raise ValueError("user_id is required")
        if not job.strip():
            raise ValueError("job is required")
        if not buyer.strip():
            raise ValueError("buyer is required")
        if not category.strip():
            raise ValueError("category is required")
        now = datetime.now(tz=UTC)
        return cls(
            id=(id or str(uuid.uuid4())).strip(),
            user_id=user_id.strip(),
            job=job.strip(),
            buyer=buyer.strip(),
            category=category.strip(),
            status=status,
            template_niche_id=template_niche_id,
            created_at=created_at or now,
            updated_at=updated_at or now,
        )
