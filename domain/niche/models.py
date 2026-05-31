"""Niche domain entities."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

NicheStatus = Literal["defined", "sourced", "active"]
NicheSourceHealth = Literal["unknown", "active", "failing", "paused"]
NicheSourceAccessMode = Literal[
    "unknown",
    "api",
    "api_auth",
    "json",
    "rss",
    "html",
    "proxy_required",
    "manual",
]
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
    enabled: bool = True
    limit: int | None = None
    scan_frequency: str | None = None
    buyer_voice_verified: bool = False
    health_status: NicheSourceHealth = "unknown"
    last_scanned_at: datetime | None = None
    last_error: str | None = None
    options: dict[str, Any] = field(default_factory=dict)
    tier: int | None = None
    signal_quality_score: float | None = None
    access_mode: NicheSourceAccessMode = "unknown"
    requires_proxy: bool = False
    requires_auth: bool = False
    recommended_cadence: str | None = None
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
        enabled: bool = True,
        limit: int | None = None,
        scan_frequency: str | None = None,
        buyer_voice_verified: bool = False,
        health_status: NicheSourceHealth = "unknown",
        last_scanned_at: datetime | None = None,
        last_error: str | None = None,
        options: dict[str, Any] | None = None,
        tier: int | None = None,
        signal_quality_score: float | None = None,
        access_mode: str = "unknown",
        requires_proxy: bool = False,
        requires_auth: bool = False,
        recommended_cadence: str | None = None,
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
        if limit is not None and limit < 1:
            raise ValueError("limit must be at least 1")
        if tier is not None and not 1 <= tier <= 6:
            raise ValueError("tier must be between 1 and 6")
        if signal_quality_score is not None and not 0 <= signal_quality_score <= 1:
            raise ValueError("signal_quality_score must be between 0 and 1")
        normalized_source_type = source_type.strip()
        normalized_source_family = source_family.strip()
        defaults = _source_catalog_defaults(normalized_source_type, is_gate_free)
        normalized_access_mode = (
            access_mode.strip().lower()
            if access_mode != "unknown"
            else defaults["access_mode"]
        )
        if normalized_access_mode not in {
            "unknown",
            "api",
            "api_auth",
            "json",
            "rss",
            "html",
            "proxy_required",
            "manual",
        }:
            raise ValueError("unsupported access_mode")
        now = datetime.now(tz=UTC)
        normalized_requires_proxy = bool(requires_proxy or defaults["requires_proxy"])
        normalized_requires_auth = bool(requires_auth or defaults["requires_auth"])
        effective_enabled = enabled and not normalized_requires_proxy and not normalized_requires_auth
        return cls(
            id=(id or str(uuid.uuid4())).strip(),
            niche_id=niche_id.strip(),
            locator=locator.strip(),
            source_type=normalized_source_type,
            source_family=normalized_source_family,
            is_gate_free=is_gate_free,
            company_id=company_id,
            enabled=effective_enabled,
            limit=limit,
            scan_frequency=scan_frequency.strip() if scan_frequency else None,
            buyer_voice_verified=buyer_voice_verified,
            health_status=health_status,
            last_scanned_at=last_scanned_at,
            last_error=last_error.strip() if last_error else None,
            options=options or {},
            tier=tier if tier is not None else defaults["tier"],
            signal_quality_score=(
                signal_quality_score
                if signal_quality_score is not None
                else defaults["signal_quality_score"]
            ),
            access_mode=normalized_access_mode,  # type: ignore[arg-type]
            requires_proxy=normalized_requires_proxy,
            requires_auth=normalized_requires_auth,
            recommended_cadence=(
                recommended_cadence.strip()
                if recommended_cadence
                else defaults["recommended_cadence"]
            ),
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


def _source_catalog_defaults(source_type: str, is_gate_free: bool) -> dict[str, Any]:
    normalized_type = source_type.strip().lower()
    if normalized_type in {
        "github_issues",
        "github_discussions",
        "github_issues_search",
    }:
        return _source_defaults("api", 1, 0.95, "daily")
    if normalized_type in {"stackoverflow", "stackoverflow_search"}:
        return _source_defaults("api", 1, 0.95, "daily")
    if normalized_type in {"hackernews", "hackernews_search"}:
        return _source_defaults("api", 2, 0.78, "daily")
    if normalized_type in {"discourse", "discourse_forum"}:
        return _source_defaults("json", 2, 0.82, "daily")
    if normalized_type in {"reddit", "reddit_search", "reddit_subreddit"}:
        return _source_defaults(
            "api_auth",
            2,
            0.82,
            "daily",
            requires_auth=True,
        )
    if normalized_type in {
        "g2",
        "g2_reviews",
        "capterra",
        "capterra_reviews",
        "trust_radius",
        "trustpilot",
        "review_search",
    }:
        return _source_defaults(
            "proxy_required",
            1,
            0.9,
            None,
            requires_proxy=True,
        )
    if normalized_type in {"rss", "changelog"}:
        return _source_defaults("rss", 5, 0.55, "weekly")
    if normalized_type in {"public_roadmap", "canny", "productboard"}:
        return _source_defaults("html", 5, 0.55, "weekly")
    if not is_gate_free:
        return _source_defaults("unknown", None, None, None, requires_auth=True)
    return _source_defaults("unknown", None, None, None)


def _source_defaults(
    access_mode: str,
    tier: int | None,
    signal_quality_score: float | None,
    recommended_cadence: str | None,
    *,
    requires_proxy: bool = False,
    requires_auth: bool = False,
) -> dict[str, Any]:
    return {
        "access_mode": access_mode,
        "tier": tier,
        "signal_quality_score": signal_quality_score,
        "recommended_cadence": recommended_cadence,
        "requires_proxy": requires_proxy,
        "requires_auth": requires_auth,
    }
