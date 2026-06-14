"""Postgres repository implementations for niche domain entities."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from application.ports import (
    NicheCompanyRepository,
    NicheRepository,
    NicheSourceRepository,
    TemplateSourceBindingRepository,
    UserNicheRepository,
    UserSourceRepository,
    UserSourcePreferenceRepository,
    UserSourceRunStatsRepository,
)
from domain.niche import (
    Niche,
    NicheCompany,
    NicheSource,
    NicheSourceRunStats,
    TemplateSourceBinding,
    UserNiche,
    UserSource,
    UserSourcePreference,
    UserSourceRunStats,
)
from infrastructure.db.repository import _PostgresRepository, _rowcount


class PostgresNicheRepository(_PostgresRepository, NicheRepository):
    """Postgres-backed niche repository."""

    def save_niches(self, niches: list[Niche]) -> int:
        inserted = 0
        for niche in niches:
            cursor = self.connection.execute(
                """
                INSERT INTO niches (
                    id, job, buyer, category, description, is_custom, status,
                    monitorability_score, opportunity_score, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    niche.id, niche.job, niche.buyer, niche.category,
                    niche.description, niche.is_custom, niche.status,
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
        is_custom: bool | None = None,
    ) -> list[Niche]:
        clauses, params = [], []
        if category:
            clauses.append("category = %s")
            params.append(category)
        if status:
            clauses.append("status = %s")
            params.append(status)
        if is_custom is not None:
            clauses.append("is_custom = %s")
            params.append(is_custom)
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

    def update_niche_source_quality(
        self,
        source_id: str,
        signal_quality_score: float,
        *,
        buyer_voice_verified: bool | None = None,
    ) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE niche_sources
               SET signal_quality_score = %s,
                   buyer_voice_verified = COALESCE(%s, buyer_voice_verified),
                   updated_at = now()
             WHERE id = %s
            """,
            (signal_quality_score, buyer_voice_verified, source_id),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def update_niche_source(self, source: NicheSource) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE niche_sources
               SET company_id = %s,
                   locator = %s,
                   source_type = %s,
                   source_family = %s,
                   is_gate_free = %s,
                   enabled = %s,
                   limit_value = %s,
                   scan_frequency = %s,
                   buyer_voice_verified = %s,
                   health_status = %s,
                   last_scanned_at = %s,
                   last_error = %s,
                   options = %s::jsonb,
                   tier = %s,
                   signal_quality_score = %s,
                   access_mode = %s,
                   requires_proxy = %s,
                   requires_auth = %s,
                   recommended_cadence = %s,
                   updated_at = %s
             WHERE id = %s
            """,
            (
                source.company_id,
                source.locator,
                source.source_type,
                source.source_family,
                source.is_gate_free,
                source.enabled,
                source.limit,
                source.scan_frequency,
                source.buyer_voice_verified,
                source.health_status,
                source.last_scanned_at,
                source.last_error,
                json.dumps(source.options),
                source.tier,
                source.signal_quality_score,
                source.access_mode,
                source.requires_proxy,
                source.requires_auth,
                source.recommended_cadence,
                source.updated_at,
                source.id,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def upsert_niche_source_run_stats(self, stats: NicheSourceRunStats) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO niche_source_health_stats (
                niche_source_id, total_runs, success_count, failure_count,
                consecutive_failures, posts_fetched_count, relevant_posts_count,
                rule_filtered_count, llm_filtered_count, relevance_failed_count,
                extracted_signals_count, gap_count, last_status, last_error,
                last_fetched_count, last_relevant_count, last_rule_filtered_count,
                last_llm_filtered_count, last_relevance_failed_count,
                last_extracted_count, last_gap_count, rejection_breakdown,
                last_rejection_breakdown, last_scanned_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s
            )
            ON CONFLICT (niche_source_id) DO UPDATE SET
                total_runs = EXCLUDED.total_runs,
                success_count = EXCLUDED.success_count,
                failure_count = EXCLUDED.failure_count,
                consecutive_failures = EXCLUDED.consecutive_failures,
                posts_fetched_count = EXCLUDED.posts_fetched_count,
                relevant_posts_count = EXCLUDED.relevant_posts_count,
                rule_filtered_count = EXCLUDED.rule_filtered_count,
                llm_filtered_count = EXCLUDED.llm_filtered_count,
                relevance_failed_count = EXCLUDED.relevance_failed_count,
                extracted_signals_count = EXCLUDED.extracted_signals_count,
                gap_count = EXCLUDED.gap_count,
                last_status = EXCLUDED.last_status,
                last_error = EXCLUDED.last_error,
                last_fetched_count = EXCLUDED.last_fetched_count,
                last_relevant_count = EXCLUDED.last_relevant_count,
                last_rule_filtered_count = EXCLUDED.last_rule_filtered_count,
                last_llm_filtered_count = EXCLUDED.last_llm_filtered_count,
                last_relevance_failed_count = EXCLUDED.last_relevance_failed_count,
                last_extracted_count = EXCLUDED.last_extracted_count,
                last_gap_count = EXCLUDED.last_gap_count,
                rejection_breakdown = EXCLUDED.rejection_breakdown,
                last_rejection_breakdown = EXCLUDED.last_rejection_breakdown,
                last_scanned_at = EXCLUDED.last_scanned_at,
                updated_at = EXCLUDED.updated_at
            """,
            (
                stats.niche_source_id,
                stats.total_runs,
                stats.success_count,
                stats.failure_count,
                stats.consecutive_failures,
                stats.posts_fetched_count,
                stats.relevant_posts_count,
                stats.rule_filtered_count,
                stats.llm_filtered_count,
                stats.relevance_failed_count,
                stats.extracted_signals_count,
                stats.gap_count,
                stats.last_status,
                stats.last_error,
                stats.last_fetched_count,
                stats.last_relevant_count,
                stats.last_rule_filtered_count,
                stats.last_llm_filtered_count,
                stats.last_relevance_failed_count,
                stats.last_extracted_count,
                stats.last_gap_count,
                json.dumps(stats.rejection_breakdown),
                json.dumps(stats.last_rejection_breakdown),
                stats.last_scanned_at,
                stats.updated_at,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def get_niche_source_run_stats(
        self,
        source_id: str,
    ) -> NicheSourceRunStats | None:
        row = self.connection.execute(
            """
            SELECT *
              FROM niche_source_health_stats
             WHERE niche_source_id = %s
            """,
            (source_id,),
        ).fetchone()
        return _niche_source_run_stats_from_row(row) if row else None

    def list_niche_source_run_stats(
        self,
        source_ids: list[str] | None = None,
    ) -> list[NicheSourceRunStats]:
        if source_ids == []:
            return []
        if source_ids is None:
            rows = self.connection.execute(
                "SELECT * FROM niche_source_health_stats ORDER BY updated_at DESC",
            ).fetchall()
        else:
            placeholders = ", ".join(["%s"] * len(source_ids))
            rows = self.connection.execute(
                f"""
                SELECT *
                  FROM niche_source_health_stats
                 WHERE niche_source_id IN ({placeholders})
                 ORDER BY updated_at DESC
                """,
                tuple(source_ids),
            ).fetchall()
        return [_niche_source_run_stats_from_row(row) for row in rows]

    def delete_niche_source(self, source_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM niche_sources WHERE id = %s", (source_id,)
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresTemplateSourceBindingRepository(
    _PostgresRepository,
    TemplateSourceBindingRepository,
):
    """Postgres-backed template source binding repository."""

    def save_template_source_bindings(
        self,
        bindings: list[TemplateSourceBinding],
    ) -> int:
        inserted = 0
        for binding in bindings:
            cursor = self.connection.execute(
                """
                INSERT INTO template_sources (
                    id, template_niche_id, source_id, company_id, default_enabled,
                    default_limit_value, default_scan_frequency,
                    default_buyer_voice_verified, default_options, tier,
                    signal_quality_score, recommended_cadence, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s
                )
                ON CONFLICT (template_niche_id, source_id) DO NOTHING
                """,
                (
                    binding.id,
                    binding.template_niche_id,
                    binding.source_id,
                    binding.company_id,
                    binding.default_enabled,
                    binding.default_limit,
                    binding.default_scan_frequency,
                    binding.default_buyer_voice_verified,
                    json.dumps(binding.default_options),
                    binding.tier,
                    binding.signal_quality_score,
                    binding.recommended_cadence,
                    binding.created_at,
                    binding.updated_at,
                ),
            )
            inserted += _rowcount(cursor)
        self.connection.commit()
        return inserted

    def list_template_source_bindings(
        self,
        template_niche_id: str,
        *,
        default_enabled: bool | None = None,
    ) -> list[TemplateSourceBinding]:
        clauses: list[str] = ["template_niche_id = %s"]
        params: list[Any] = [template_niche_id]
        if default_enabled is not None:
            clauses.append("default_enabled = %s")
            params.append(default_enabled)
        rows = self.connection.execute(
            f"""
            SELECT * FROM template_sources
             WHERE {' AND '.join(clauses)}
             ORDER BY tier NULLS LAST, created_at, id
            """,
            tuple(params),
        ).fetchall()
        return [_template_source_binding_from_row(row) for row in rows]

    def delete_template_source_binding(self, binding_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM template_sources WHERE id = %s",
            (binding_id,),
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


class PostgresUserSourceRepository(_PostgresRepository, UserSourceRepository):
    """Postgres-backed concrete user source binding repository."""

    def save_user_sources(self, sources: list[UserSource]) -> int:
        inserted = 0
        for source in sources:
            cursor = self.connection.execute(
                """
                INSERT INTO user_sources (
                    id, user_niche_id, source_id, template_source_binding_id,
                    enabled, muted, cadence, priority, limit_value, options,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s
                )
                ON CONFLICT (user_niche_id, source_id) DO UPDATE SET
                    template_source_binding_id = EXCLUDED.template_source_binding_id,
                    enabled = EXCLUDED.enabled,
                    muted = EXCLUDED.muted,
                    cadence = EXCLUDED.cadence,
                    priority = EXCLUDED.priority,
                    limit_value = EXCLUDED.limit_value,
                    options = EXCLUDED.options,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    source.id,
                    source.user_niche_id,
                    source.source_id,
                    source.template_source_binding_id,
                    source.enabled,
                    source.muted,
                    source.cadence,
                    source.priority,
                    source.limit,
                    json.dumps(source.options),
                    source.created_at,
                    source.updated_at,
                ),
            )
            inserted += _rowcount(cursor)
        self.connection.commit()
        return inserted

    def get_user_source(
        self,
        user_niche_id: str,
        source_id: str,
    ) -> UserSource | None:
        row = self.connection.execute(
            """
            SELECT * FROM user_sources
             WHERE user_niche_id = %s AND source_id = %s
            """,
            (user_niche_id, source_id),
        ).fetchone()
        return _user_source_from_row(row) if row else None

    def list_user_sources(
        self,
        user_niche_id: str,
        *,
        enabled: bool | None = None,
        include_muted: bool = True,
    ) -> list[UserSource]:
        clauses: list[str] = ["user_niche_id = %s"]
        params: list[Any] = [user_niche_id]
        if enabled is not None:
            clauses.append("enabled = %s")
            params.append(enabled)
        if not include_muted:
            clauses.append("muted = false")
        rows = self.connection.execute(
            f"""
            SELECT * FROM user_sources
             WHERE {' AND '.join(clauses)}
             ORDER BY priority NULLS LAST, created_at, id
            """,
            tuple(params),
        ).fetchall()
        return [_user_source_from_row(row) for row in rows]

    def delete_user_source(self, user_source_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM user_sources WHERE id = %s",
            (user_source_id,),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresUserSourcePreferenceRepository(
    _PostgresRepository,
    UserSourcePreferenceRepository,
):
    """Postgres-backed user source preference repository."""

    def save_user_source_preference(
        self,
        preference: UserSourcePreference,
    ) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO user_source_preferences (
                id, user_niche_id, source_id, enabled, muted, cadence_override,
                priority_override, limit_override, options_override,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (user_niche_id, source_id) DO UPDATE SET
                enabled = EXCLUDED.enabled,
                muted = EXCLUDED.muted,
                cadence_override = EXCLUDED.cadence_override,
                priority_override = EXCLUDED.priority_override,
                limit_override = EXCLUDED.limit_override,
                options_override = EXCLUDED.options_override,
                updated_at = EXCLUDED.updated_at
            """,
            (
                preference.id,
                preference.user_niche_id,
                preference.source_id,
                preference.enabled,
                preference.muted,
                preference.cadence_override,
                preference.priority_override,
                preference.limit_override,
                json.dumps(preference.options_override),
                preference.created_at,
                preference.updated_at,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def get_user_source_preference(
        self,
        user_niche_id: str,
        source_id: str,
    ) -> UserSourcePreference | None:
        row = self.connection.execute(
            """
            SELECT * FROM user_source_preferences
             WHERE user_niche_id = %s AND source_id = %s
            """,
            (user_niche_id, source_id),
        ).fetchone()
        return _user_source_preference_from_row(row) if row else None

    def list_user_source_preferences(
        self,
        user_niche_id: str,
    ) -> list[UserSourcePreference]:
        rows = self.connection.execute(
            """
            SELECT * FROM user_source_preferences
             WHERE user_niche_id = %s
             ORDER BY priority_override NULLS LAST, created_at, id
            """,
            (user_niche_id,),
        ).fetchall()
        return [_user_source_preference_from_row(row) for row in rows]

    def delete_user_source_preference(self, preference_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM user_source_preferences WHERE id = %s",
            (preference_id,),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresUserSourceRunStatsRepository(
    _PostgresRepository,
    UserSourceRunStatsRepository,
):
    """Postgres-backed user source runtime stats repository."""

    def upsert_user_source_run_stats(
        self,
        stats: UserSourceRunStats,
    ) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO user_source_run_stats (
                user_niche_id, source_id, template_source_binding_id, total_runs,
                success_count, failure_count, consecutive_failures,
                posts_fetched_count, relevant_posts_count, rule_filtered_count,
                llm_filtered_count, relevance_failed_count,
                extracted_signals_count, gap_count, last_status, last_error,
                last_fetched_count, last_relevant_count, last_rule_filtered_count,
                last_llm_filtered_count, last_relevance_failed_count,
                last_extracted_count, last_gap_count, rejection_breakdown,
                last_rejection_breakdown, last_scanned_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s
            )
            ON CONFLICT (user_niche_id, source_id) DO UPDATE SET
                template_source_binding_id = EXCLUDED.template_source_binding_id,
                total_runs = EXCLUDED.total_runs,
                success_count = EXCLUDED.success_count,
                failure_count = EXCLUDED.failure_count,
                consecutive_failures = EXCLUDED.consecutive_failures,
                posts_fetched_count = EXCLUDED.posts_fetched_count,
                relevant_posts_count = EXCLUDED.relevant_posts_count,
                rule_filtered_count = EXCLUDED.rule_filtered_count,
                llm_filtered_count = EXCLUDED.llm_filtered_count,
                relevance_failed_count = EXCLUDED.relevance_failed_count,
                extracted_signals_count = EXCLUDED.extracted_signals_count,
                gap_count = EXCLUDED.gap_count,
                last_status = EXCLUDED.last_status,
                last_error = EXCLUDED.last_error,
                last_fetched_count = EXCLUDED.last_fetched_count,
                last_relevant_count = EXCLUDED.last_relevant_count,
                last_rule_filtered_count = EXCLUDED.last_rule_filtered_count,
                last_llm_filtered_count = EXCLUDED.last_llm_filtered_count,
                last_relevance_failed_count = EXCLUDED.last_relevance_failed_count,
                last_extracted_count = EXCLUDED.last_extracted_count,
                last_gap_count = EXCLUDED.last_gap_count,
                rejection_breakdown = EXCLUDED.rejection_breakdown,
                last_rejection_breakdown = EXCLUDED.last_rejection_breakdown,
                last_scanned_at = EXCLUDED.last_scanned_at,
                updated_at = EXCLUDED.updated_at
            """,
            (
                stats.user_niche_id,
                stats.source_id,
                stats.template_source_binding_id,
                stats.total_runs,
                stats.success_count,
                stats.failure_count,
                stats.consecutive_failures,
                stats.posts_fetched_count,
                stats.relevant_posts_count,
                stats.rule_filtered_count,
                stats.llm_filtered_count,
                stats.relevance_failed_count,
                stats.extracted_signals_count,
                stats.gap_count,
                stats.last_status,
                stats.last_error,
                stats.last_fetched_count,
                stats.last_relevant_count,
                stats.last_rule_filtered_count,
                stats.last_llm_filtered_count,
                stats.last_relevance_failed_count,
                stats.last_extracted_count,
                stats.last_gap_count,
                json.dumps(stats.rejection_breakdown),
                json.dumps(stats.last_rejection_breakdown),
                stats.last_scanned_at,
                stats.updated_at,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def get_user_source_run_stats(
        self,
        user_niche_id: str,
        source_id: str,
    ) -> UserSourceRunStats | None:
        row = self.connection.execute(
            """
            SELECT *
              FROM user_source_run_stats
             WHERE user_niche_id = %s AND source_id = %s
            """,
            (user_niche_id, source_id),
        ).fetchone()
        return _user_source_run_stats_from_row(row) if row else None

    def list_user_source_run_stats(
        self,
        user_niche_id: str,
        source_ids: list[str] | None = None,
    ) -> list[UserSourceRunStats]:
        if source_ids == []:
            return []
        if source_ids is None:
            rows = self.connection.execute(
                """
                SELECT *
                  FROM user_source_run_stats
                 WHERE user_niche_id = %s
                 ORDER BY updated_at DESC
                """,
                (user_niche_id,),
            ).fetchall()
        else:
            placeholders = ", ".join(["%s"] * len(source_ids))
            rows = self.connection.execute(
                f"""
                SELECT *
                  FROM user_source_run_stats
                 WHERE user_niche_id = %s
                   AND source_id IN ({placeholders})
                 ORDER BY updated_at DESC
                """,
                (user_niche_id, *source_ids),
            ).fetchall()
        return [_user_source_run_stats_from_row(row) for row in rows]


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
        is_custom=bool(row.get("is_custom", False)),
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


def _template_source_binding_from_row(row: dict[str, Any]) -> TemplateSourceBinding:
    return TemplateSourceBinding(
        id=str(row["id"]),
        template_niche_id=str(row["template_niche_id"]),
        source_id=str(row["source_id"]),
        company_id=str(row["company_id"]) if row.get("company_id") else None,
        default_enabled=bool(row.get("default_enabled", True)),
        default_limit=row.get("default_limit_value"),
        default_scan_frequency=row.get("default_scan_frequency"),
        default_buyer_voice_verified=bool(
            row.get("default_buyer_voice_verified", False),
        ),
        default_options=_json_obj(row.get("default_options")),
        tier=row.get("tier"),
        signal_quality_score=row.get("signal_quality_score"),
        recommended_cadence=row.get("recommended_cadence"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _niche_source_run_stats_from_row(row: dict[str, Any]) -> NicheSourceRunStats:
    return NicheSourceRunStats.create(
        niche_source_id=str(row["niche_source_id"]),
        total_runs=int(row.get("total_runs", 0)),
        success_count=int(row.get("success_count", 0)),
        failure_count=int(row.get("failure_count", 0)),
        consecutive_failures=int(row.get("consecutive_failures", 0)),
        posts_fetched_count=int(row.get("posts_fetched_count", 0)),
        relevant_posts_count=int(row.get("relevant_posts_count", 0)),
        rule_filtered_count=int(row.get("rule_filtered_count", 0)),
        llm_filtered_count=int(row.get("llm_filtered_count", 0)),
        relevance_failed_count=int(row.get("relevance_failed_count", 0)),
        extracted_signals_count=int(row.get("extracted_signals_count", 0)),
        gap_count=int(row.get("gap_count", 0)),
        last_status=row.get("last_status", "unknown"),
        last_error=row.get("last_error"),
        last_fetched_count=int(row.get("last_fetched_count", 0)),
        last_relevant_count=int(row.get("last_relevant_count", 0)),
        last_rule_filtered_count=int(row.get("last_rule_filtered_count", 0)),
        last_llm_filtered_count=int(row.get("last_llm_filtered_count", 0)),
        last_relevance_failed_count=int(row.get("last_relevance_failed_count", 0)),
        last_extracted_count=int(row.get("last_extracted_count", 0)),
        last_gap_count=int(row.get("last_gap_count", 0)),
        rejection_breakdown={
            key: int(value)
            for key, value in _json_obj(row.get("rejection_breakdown")).items()
        },
        last_rejection_breakdown={
            key: int(value)
            for key, value in _json_obj(row.get("last_rejection_breakdown")).items()
        },
        last_scanned_at=row.get("last_scanned_at"),
        updated_at=row.get("updated_at"),
    )


def _user_source_from_row(row: dict[str, Any]) -> UserSource:
    return UserSource.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        source_id=str(row["source_id"]),
        template_source_binding_id=(
            str(row["template_source_binding_id"])
            if row.get("template_source_binding_id")
            else None
        ),
        enabled=bool(row.get("enabled", True)),
        muted=bool(row.get("muted", False)),
        cadence=row.get("cadence"),
        priority=row.get("priority"),
        limit=row.get("limit_value"),
        options=_json_obj(row.get("options")),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _user_source_run_stats_from_row(row: dict[str, Any]) -> UserSourceRunStats:
    return UserSourceRunStats.create(
        user_niche_id=str(row["user_niche_id"]),
        source_id=str(row["source_id"]),
        template_source_binding_id=(
            str(row["template_source_binding_id"])
            if row.get("template_source_binding_id")
            else None
        ),
        total_runs=int(row.get("total_runs", 0)),
        success_count=int(row.get("success_count", 0)),
        failure_count=int(row.get("failure_count", 0)),
        consecutive_failures=int(row.get("consecutive_failures", 0)),
        posts_fetched_count=int(row.get("posts_fetched_count", 0)),
        relevant_posts_count=int(row.get("relevant_posts_count", 0)),
        rule_filtered_count=int(row.get("rule_filtered_count", 0)),
        llm_filtered_count=int(row.get("llm_filtered_count", 0)),
        relevance_failed_count=int(row.get("relevance_failed_count", 0)),
        extracted_signals_count=int(row.get("extracted_signals_count", 0)),
        gap_count=int(row.get("gap_count", 0)),
        last_status=row.get("last_status", "unknown"),
        last_error=row.get("last_error"),
        last_fetched_count=int(row.get("last_fetched_count", 0)),
        last_relevant_count=int(row.get("last_relevant_count", 0)),
        last_rule_filtered_count=int(row.get("last_rule_filtered_count", 0)),
        last_llm_filtered_count=int(row.get("last_llm_filtered_count", 0)),
        last_relevance_failed_count=int(row.get("last_relevance_failed_count", 0)),
        last_extracted_count=int(row.get("last_extracted_count", 0)),
        last_gap_count=int(row.get("last_gap_count", 0)),
        rejection_breakdown={
            key: int(value)
            for key, value in _json_obj(row.get("rejection_breakdown")).items()
        },
        last_rejection_breakdown={
            key: int(value)
            for key, value in _json_obj(row.get("last_rejection_breakdown")).items()
        },
        last_scanned_at=row.get("last_scanned_at"),
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


def _user_source_preference_from_row(row: dict[str, Any]) -> UserSourcePreference:
    return UserSourcePreference(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        source_id=str(row["source_id"]),
        enabled=row.get("enabled") if row.get("enabled") is not None else None,
        muted=bool(row.get("muted", False)),
        cadence_override=row.get("cadence_override"),
        priority_override=row.get("priority_override"),
        limit_override=row.get("limit_override"),
        options_override=_json_obj(row.get("options_override")),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
