"""Postgres repository implementations for niche domain entities."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from application.ports import (
    GapRepository,
    NicheCompanyRepository,
    NicheRepository,
    NicheSourceRepository,
    UserNicheRepository,
)
from domain.niche import Gap, Niche, NicheCompany, NicheSource, UserNiche
from infrastructure.db.repository import _PostgresRepository, _rowcount


class PostgresNicheRepository(_PostgresRepository, NicheRepository):
    """Postgres-backed niche repository."""

    def save_niches(self, niches: list[Niche]) -> int:
        inserted = 0
        for niche in niches:
            cursor = self.connection.execute(
                """
                INSERT INTO niches (
                    id, job, buyer, category, description, status,
                    monitorability_score, opportunity_score, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    niche.id, niche.job, niche.buyer, niche.category,
                    niche.description, niche.status,
                    niche.monitorability_score, niche.opportunity_score,
                    niche.created_at, niche.updated_at,
                ),
            )
            inserted += _rowcount(cursor)
        self.connection.commit()
        return inserted

    def get_niche(self, niche_id: str) -> Niche | None:
        row = self.connection.execute(
            "SELECT * FROM niches WHERE id = %s", (niche_id,)
        ).fetchone()
        return _niche_from_row(row) if row else None

    def list_niches(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
    ) -> list[Niche]:
        clauses, params = [], []
        if category:
            clauses.append("category = %s")
            params.append(category)
        if status:
            clauses.append("status = %s")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self.connection.execute(
            f"SELECT * FROM niches {where} ORDER BY created_at DESC", params
        ).fetchall()
        return [_niche_from_row(r) for r in rows]

    def update_niche(self, niche: Niche) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE niches
               SET job = %s, buyer = %s, category = %s, description = %s,
                   status = %s, monitorability_score = %s, opportunity_score = %s,
                   updated_at = %s
             WHERE id = %s
            """,
            (
                niche.job, niche.buyer, niche.category, niche.description,
                niche.status, niche.monitorability_score, niche.opportunity_score,
                niche.updated_at, niche.id,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def delete_niche(self, niche_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM niches WHERE id = %s", (niche_id,)
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresNicheCompanyRepository(_PostgresRepository, NicheCompanyRepository):
    """Postgres-backed niche company repository."""

    def save_niche_companies(self, companies: list[NicheCompany]) -> int:
        inserted = 0
        for company in companies:
            cursor = self.connection.execute(
                """
                INSERT INTO niche_companies (id, niche_id, name, website, is_primary, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    company.id, company.niche_id, company.name,
                    company.website, company.is_primary, company.created_at,
                ),
            )
            inserted += _rowcount(cursor)
        self.connection.commit()
        return inserted

    def list_niche_companies(self, niche_id: str) -> list[NicheCompany]:
        rows = self.connection.execute(
            "SELECT * FROM niche_companies WHERE niche_id = %s ORDER BY name",
            (niche_id,),
        ).fetchall()
        return [_niche_company_from_row(r) for r in rows]

    def delete_niche_company(self, company_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM niche_companies WHERE id = %s", (company_id,)
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresNicheSourceRepository(_PostgresRepository, NicheSourceRepository):
    """Postgres-backed niche source repository."""

    def save_niche_sources(self, sources: list[NicheSource]) -> int:
        inserted = 0
        for source in sources:
            cursor = self.connection.execute(
                """
                INSERT INTO niche_sources (
                    id, niche_id, company_id, locator, source_type, source_family,
                    is_gate_free, enabled, limit_value, scan_frequency,
                    buyer_voice_verified, health_status, last_scanned_at,
                    last_error, options, tier, signal_quality_score, access_mode,
                    requires_proxy, requires_auth, recommended_cadence,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s::jsonb, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (niche_id, locator) DO NOTHING
                """,
                (
                    source.id, source.niche_id, source.company_id,
                    source.locator, source.source_type, source.source_family,
                    source.is_gate_free, source.enabled, source.limit,
                    source.scan_frequency, source.buyer_voice_verified,
                    source.health_status, source.last_scanned_at,
                    source.last_error, json.dumps(source.options), source.tier,
                    source.signal_quality_score, source.access_mode,
                    source.requires_proxy, source.requires_auth,
                    source.recommended_cadence, source.created_at,
                    source.updated_at,
                ),
            )
            inserted += _rowcount(cursor)
        self.connection.commit()
        return inserted

    def list_niche_sources(
        self,
        niche_id: str,
        *,
        enabled: bool | None = None,
        is_gate_free: bool | None = None,
        buyer_voice_verified: bool | None = None,
    ) -> list[NicheSource]:
        clauses, params = ["niche_id = %s"], [niche_id]
        if enabled is not None:
            clauses.append("enabled = %s")
            params.append(enabled)
        if is_gate_free is not None:
            clauses.append("is_gate_free = %s")
            params.append(is_gate_free)
        if buyer_voice_verified is not None:
            clauses.append("buyer_voice_verified = %s")
            params.append(buyer_voice_verified)
        rows = self.connection.execute(
            f"SELECT * FROM niche_sources WHERE {' AND '.join(clauses)} ORDER BY created_at",
            params,
        ).fetchall()
        return [_niche_source_from_row(r) for r in rows]

    def update_niche_source_health(
        self,
        source_id: str,
        health_status: str,
        last_scanned_at: Any = None,
        last_error: str | None = None,
    ) -> bool:
        from datetime import UTC
        cursor = self.connection.execute(
            """
            UPDATE niche_sources
               SET health_status = %s, last_scanned_at = %s,
                   last_error = %s, updated_at = %s
             WHERE id = %s
            """,
            (health_status, last_scanned_at, last_error, datetime.now(UTC), source_id),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def delete_niche_source(self, source_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM niche_sources WHERE id = %s", (source_id,)
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresGapRepository(_PostgresRepository, GapRepository):
    """Postgres-backed gap repository."""

    def save_gaps(self, gaps: list[Gap]) -> int:
        inserted = 0
        for gap in gaps:
            cursor = self.connection.execute(
                """
                INSERT INTO gaps (
                    id, niche_id, title, pain_summary, unmet_need_type,
                    affected_buyer, suggested_wedge, breadth, depth,
                    signal_strength, evidence_finding_ids, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    gap.id, gap.niche_id, gap.title, gap.pain_summary,
                    gap.unmet_need_type, gap.affected_buyer, gap.suggested_wedge,
                    gap.breadth, gap.depth, gap.signal_strength,
                    json.dumps(gap.evidence_finding_ids),
                    gap.created_at, gap.updated_at,
                ),
            )
            inserted += _rowcount(cursor)
        self.connection.commit()
        return inserted

    def get_gap(self, gap_id: str) -> Gap | None:
        row = self.connection.execute(
            "SELECT * FROM gaps WHERE id = %s", (gap_id,)
        ).fetchone()
        return _gap_from_row(row) if row else None

    def list_gaps(
        self,
        niche_id: str,
        *,
        unmet_need_type: str | None = None,
        signal_strength: str | None = None,
    ) -> list[Gap]:
        clauses, params = ["niche_id = %s"], [niche_id]
        if unmet_need_type:
            clauses.append("unmet_need_type = %s")
            params.append(unmet_need_type)
        if signal_strength:
            clauses.append("signal_strength = %s")
            params.append(signal_strength)
        rows = self.connection.execute(
            f"SELECT * FROM gaps WHERE {' AND '.join(clauses)} ORDER BY created_at DESC",
            params,
        ).fetchall()
        return [_gap_from_row(r) for r in rows]

    def delete_gap(self, gap_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM gaps WHERE id = %s", (gap_id,)
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresUserNicheRepository(_PostgresRepository, UserNicheRepository):
    """Postgres-backed user niche repository."""

    def save_user_niche(self, user_niche: UserNiche) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO user_niches (
                id, user_id, template_niche_id, job, buyer, category,
                status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                user_niche.id, user_niche.user_id, user_niche.template_niche_id,
                user_niche.job, user_niche.buyer, user_niche.category,
                user_niche.status, user_niche.created_at, user_niche.updated_at,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def get_user_niche(self, user_niche_id: str) -> UserNiche | None:
        row = self.connection.execute(
            "SELECT * FROM user_niches WHERE id = %s", (user_niche_id,)
        ).fetchone()
        return _user_niche_from_row(row) if row else None

    def list_user_niches(self, user_id: str) -> list[UserNiche]:
        rows = self.connection.execute(
            "SELECT * FROM user_niches WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [_user_niche_from_row(r) for r in rows]

    def list_all_user_niches(self) -> list[UserNiche]:
        rows = self.connection.execute(
            "SELECT * FROM user_niches ORDER BY created_at DESC"
        ).fetchall()
        return [_user_niche_from_row(r) for r in rows]

    def update_user_niche(self, user_niche: UserNiche) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE user_niches
               SET job = %s, buyer = %s, category = %s, status = %s, updated_at = %s
             WHERE id = %s
            """,
            (
                user_niche.job, user_niche.buyer, user_niche.category,
                user_niche.status, user_niche.updated_at, user_niche.id,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def delete_user_niche(self, user_niche_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM user_niches WHERE id = %s", (user_niche_id,)
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


# ── Row deserializers ─────────────────────────────────────────────────────────

def _json_obj(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _niche_from_row(row: dict[str, Any]) -> Niche:
    return Niche(
        id=str(row["id"]),
        job=row["job"],
        buyer=row["buyer"],
        category=row["category"],
        description=row.get("description"),
        status=row["status"],
        monitorability_score=row.get("monitorability_score"),
        opportunity_score=row.get("opportunity_score"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _niche_company_from_row(row: dict[str, Any]) -> NicheCompany:
    return NicheCompany(
        id=str(row["id"]),
        niche_id=str(row["niche_id"]),
        name=row["name"],
        website=row.get("website"),
        is_primary=bool(row.get("is_primary", True)),
        created_at=row.get("created_at"),
    )


def _niche_source_from_row(row: dict[str, Any]) -> NicheSource:
    return NicheSource(
        id=str(row["id"]),
        niche_id=str(row["niche_id"]),
        company_id=str(row["company_id"]) if row.get("company_id") else None,
        locator=row["locator"],
        source_type=row["source_type"],
        source_family=row["source_family"],
        is_gate_free=bool(row["is_gate_free"]),
        enabled=bool(row.get("enabled", True)),
        limit=row.get("limit_value"),
        scan_frequency=row.get("scan_frequency"),
        buyer_voice_verified=bool(row.get("buyer_voice_verified", False)),
        health_status=row.get("health_status", "unknown"),
        last_scanned_at=row.get("last_scanned_at"),
        last_error=row.get("last_error"),
        options=_json_obj(row.get("options")),
        tier=row.get("tier"),
        signal_quality_score=row.get("signal_quality_score"),
        access_mode=row.get("access_mode", "unknown"),
        requires_proxy=bool(row.get("requires_proxy", False)),
        requires_auth=bool(row.get("requires_auth", False)),
        recommended_cadence=row.get("recommended_cadence"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _gap_from_row(row: dict[str, Any]) -> Gap:
    evidence = row.get("evidence_finding_ids") or []
    if isinstance(evidence, str):
        import json as _json
        evidence = _json.loads(evidence)
    return Gap(
        id=str(row["id"]),
        niche_id=str(row["niche_id"]),
        title=row["title"],
        pain_summary=row["pain_summary"],
        unmet_need_type=row["unmet_need_type"],
        affected_buyer=row["affected_buyer"],
        suggested_wedge=row["suggested_wedge"],
        breadth=int(row["breadth"]),
        depth=int(row["depth"]),
        signal_strength=row["signal_strength"],
        evidence_finding_ids=list(evidence),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _user_niche_from_row(row: dict[str, Any]) -> UserNiche:
    return UserNiche(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        template_niche_id=str(row["template_niche_id"]) if row.get("template_niche_id") else None,
        job=row["job"],
        buyer=row["buyer"],
        category=row["category"],
        status=row["status"],
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
