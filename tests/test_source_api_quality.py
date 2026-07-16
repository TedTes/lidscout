import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from api.routes.signals import (
    NicheSourceRequest,
    NicheSourceUpdateRequest,
    SignalApiDependencies,
    create_market_source,
    delete_source,
    exclude_market_source,
    get_pipeline_diagnostics,
    list_markets,
    list_market_sources,
    list_sources,
    restore_market_source,
    update_source,
)
from domain.finding import Finding
from domain.niche import (
    TemplateSourceBinding,
    UserNiche,
    UserSource,
    UserSourcePreference,
    UserSourceRunStats,
)
from domain.opportunity import Opportunity
from domain.post import RawPost
from domain.signal import Signal
from domain.source import Source
from domain.theme import Theme
from domain.user import User
from infrastructure.db import (
    InMemorySourceRepository,
    InMemoryTemplateSourceBindingRepository,
    InMemoryUserNicheRepository,
    InMemoryUserSourceRepository,
    InMemoryUserSourcePreferenceRepository,
    InMemoryUserSourceRunStatsRepository,
)


def test_market_sources_include_quality_status_and_health_stats() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://hn.algolia.com/api/v1/search_by_date?query=devtools",
                source_type="hackernews_search",
                source_family="technical_forum",
                is_gate_free=True,
                access_mode="api",
            )
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
                default_buyer_voice_verified=True,
            )
        ]
    )
    user_source_run_stats_repository = InMemoryUserSourceRunStatsRepository()
    user_source_run_stats_repository.upsert_user_source_run_stats(
        UserSourceRunStats.create(
            user_niche_id="market-1",
            source_id="source-1",
            template_source_binding_id="binding-1",
            total_runs=4,
            success_count=4,
            posts_fetched_count=40,
            relevant_posts_count=8,
            rule_filtered_count=12,
            extracted_signals_count=3,
            gap_count=1,
            last_status="healthy",
            last_fetched_count=10,
            last_relevant_count=2,
            last_extracted_count=1,
            last_gap_count=1,
        )
    )
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_run_stats_repository=user_source_run_stats_repository,
    )

    response = asyncio.run(
        list_market_sources("market-1", dependencies, current_user=user)
    )

    item = response["sources"][0]
    assert item["quality_status"] == "productive"
    assert item["quality_reason"] == "Source has produced relevant buyer evidence."
    assert item["scan_eligible"] is True
    assert item["scan_ineligible_reason"] is None
    assert item["health"]["total_runs"] == 4
    assert item["health"]["fetch_success_rate"] == 1.0
    assert item["health"]["relevance_yield_rate"] == 0.2
    assert item["health"]["signal_yield_rate"] == 0.375
    assert item["management"]["recommended_action"] == "keep_monitoring"
    assert item["management"]["can_disable"] is True


def test_global_sources_endpoint_is_deprecated() -> None:
    with pytest.raises(HTTPException) as exc:
        asyncio.run(list_sources())

    assert exc.value.status_code == 410
    assert "markets/{market_id}/sources" in exc.value.detail


def test_market_sources_include_contribution_rollups() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://example.com/source-1",
                source_type="web",
                source_family="forum",
                is_gate_free=True,
            ),
            Source.create(
                id="source-2",
                locator="https://example.com/source-2",
                source_type="web",
                source_family="forum",
                is_gate_free=True,
            ),
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
            ),
            TemplateSourceBinding.create(
                id="binding-2",
                template_niche_id="template-1",
                source_id="source-2",
            ),
        ]
    )
    findings = [
        Finding.create(
            id="finding-1",
            user_niche_id="market-1",
            post_id="web:source-1-a",
            pain="Exports are slow.",
            evidence_text="Exports are slow.",
            structured_embedding_text="Exports are slow.",
            urgency="medium",
            severity="medium",
            confidence=0.8,
            niche_id="template-1",
            source_id="source-1",
        ),
        Finding.create(
            id="finding-2",
            user_niche_id="market-1",
            post_id="web:source-1-b",
            pain="Exports need retries.",
            evidence_text="Exports need retries.",
            structured_embedding_text="Exports need retries.",
            urgency="medium",
            severity="medium",
            confidence=0.8,
            niche_id="template-1",
            source_id="source-1",
        ),
        Finding.create(
            id="finding-3",
            user_niche_id="market-1",
            post_id="web:source-2-a",
            pain="Imports lack previews.",
            evidence_text="Imports lack previews.",
            structured_embedding_text="Imports lack previews.",
            urgency="medium",
            severity="medium",
            confidence=0.8,
            niche_id="template-1",
            source_id="source-2",
        ),
    ]
    themes = [
        Theme.create(
            id="theme-1",
            user_niche_id="market-1",
            title="Export reliability",
            summary="Exports need better reliability.",
        ),
        Theme.create(
            id="theme-2",
            user_niche_id="market-1",
            title="Import previews",
            summary="Imports need preview workflows.",
        ),
    ]
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        finding_repository=FakeFindingRepository(findings),
        theme_repository=FakeThemeRepository(
            themes,
            {"theme-1": findings[:2], "theme-2": findings[2:]},
        ),
    )
    dependencies.post_repository.save_posts(
        [
            RawPost.create(
                source="web",
                source_id="source-1-a",
                metadata={"source_id": "source-1"},
            )
        ]
    )
    dependencies.signal_repository.save_signals(
        [
            Signal.create(
                id="signal-1",
                post_id="web:source-1-a",
                niche_id="template-1",
                pain="Exports are slow.",
            )
        ]
    )
    dependencies.opportunity_repository.save_opportunities(
        [
            Opportunity.create(
                id="opportunity-signal",
                cluster_id="cluster-1",
                title="Reliable exports",
                target_user="engineering teams",
                pain_summary="Exports are slow.",
                why_it_matters="Teams wait on exports.",
                suggested_wedge="Retry failed exports automatically.",
                evidence_count=1,
                confidence=0.7,
                evidence_signal_ids=["signal-1"],
                unmet_need_type="time",
            ),
            Opportunity.create(
                id="opportunity-theme",
                cluster_id=None,
                source_theme_id="theme-2",
                title="Import preview workflow",
                target_user="engineering teams",
                pain_summary="Imports lack previews.",
                why_it_matters="Teams catch errors late.",
                suggested_wedge="Preview imports before commit.",
                evidence_count=1,
                confidence=0.7,
                evidence_signal_ids=["finding-3"],
                unmet_need_type="time",
            ),
        ]
    )

    response = asyncio.run(
        list_market_sources("market-1", dependencies, current_user=user)
    )

    sources = {source["id"]: source for source in response["sources"]}
    assert sources["source-1"]["contribution"] == {
        "findings_count": 2,
        "themes_count": 1,
        "opportunities_count": 1,
    }
    assert sources["source-1"]["findings_count"] == 2
    assert sources["source-2"]["contribution"] == {
        "findings_count": 1,
        "themes_count": 1,
        "opportunities_count": 1,
    }


def test_markets_include_source_health_summary() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://example.com/source-1",
                source_type="web",
                source_family="forum",
                is_gate_free=True,
            ),
            Source.create(
                id="source-2",
                locator="https://example.com/source-2",
                source_type="web",
                source_family="forum",
                is_gate_free=True,
            ),
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
            ),
            TemplateSourceBinding.create(
                id="binding-2",
                template_niche_id="template-1",
                source_id="source-2",
            ),
        ]
    )
    user_source_repository = InMemoryUserSourceRepository()
    user_source_repository.save_user_sources(
        [
            UserSource.create(
                user_niche_id="market-1",
                source_id="source-2",
                muted=True,
            )
        ]
    )
    user_source_run_stats_repository = InMemoryUserSourceRunStatsRepository()
    user_source_run_stats_repository.upsert_user_source_run_stats(
        UserSourceRunStats.create(
            user_niche_id="market-1",
            source_id="source-1",
            total_runs=2,
            failure_count=2,
            consecutive_failures=2,
            last_status="failing",
            last_error="Timed out",
        )
    )
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_repository=user_source_repository,
        user_source_run_stats_repository=user_source_run_stats_repository,
    )

    response = asyncio.run(
        list_markets(dependencies, current_user=user, include_source_summary=True)
    )

    summary = response["markets"][0]["source_summary"]
    assert summary["source_count"] == 2
    assert summary["active_count"] == 1
    assert summary["excluded_count"] == 1
    assert summary["failing_count"] == 1
    assert summary["coverage_status"] == "degraded"


def test_market_sources_can_be_resolved_from_source_catalog() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
                source_type="hackernews",
                source_family="technical_forum",
                access_mode="api",
                is_gate_free=True,
            )
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
                default_limit=25,
                default_scan_frequency="daily",
                default_options={"query": "vercel"},
                tier=2,
                signal_quality_score=0.78,
            )
        ]
    )
    preference_repository = InMemoryUserSourcePreferenceRepository()
    preference_repository.save_user_source_preference(
        UserSourcePreference.create(
            id="preference-1",
            user_niche_id="market-1",
            source_id="source-1",
            limit_override=10,
            options_override={"query": "vercel railway"},
        )
    )
    user_source_run_stats_repository = InMemoryUserSourceRunStatsRepository()
    user_source_run_stats_repository.upsert_user_source_run_stats(
        UserSourceRunStats.create(
            user_niche_id="market-1",
            source_id="source-1",
            template_source_binding_id="binding-1",
            total_runs=1,
            success_count=1,
            posts_fetched_count=10,
            relevant_posts_count=2,
            extracted_signals_count=1,
            gap_count=1,
            last_status="healthy",
        )
    )
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_preference_repository=preference_repository,
        user_source_run_stats_repository=user_source_run_stats_repository,
    )

    response = asyncio.run(
        list_market_sources("market-1", dependencies, current_user=user)
    )

    item = response["sources"][0]
    assert item["id"] == "source-1"
    assert item["market_id"] == "template-1"
    assert item["enabled"] is True
    assert item["limit"] == 10
    assert item["scan_frequency"] == "daily"
    assert item["options"]["query"] == "vercel railway"
    assert item["options"]["template_source_binding_id"] == "binding-1"
    assert item["options"]["user_source_preference_id"] == "preference-1"
    assert item["health"]["total_runs"] == 1
    assert response["summary"]["source_count"] == 1


def test_catalog_source_update_and_delete_write_user_sources() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
                source_type="hackernews",
                source_family="technical_forum",
                access_mode="api",
                is_gate_free=True,
            )
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
                default_limit=25,
                default_scan_frequency="daily",
                default_options={"query": "vercel"},
            )
        ]
    )
    preference_repository = InMemoryUserSourcePreferenceRepository()
    user_source_repository = InMemoryUserSourceRepository()
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_preference_repository=preference_repository,
        user_source_repository=user_source_repository,
    )

    updated = asyncio.run(
        update_source(
            "source-1",
            NicheSourceUpdateRequest(
                enabled=False,
                limit=5,
                scan_frequency="weekly",
                options={"query": "vercel railway"},
            ),
            dependencies,
            current_user=user,
        )
    )

    user_source = user_source_repository.get_user_source(
        "market-1",
        "source-1",
    )
    assert updated["enabled"] is False
    assert updated["limit"] == 5
    assert user_source is not None
    assert user_source.enabled is False
    assert user_source.limit == 5
    assert user_source.cadence == "weekly"
    assert user_source.template_source_binding_id == "binding-1"
    assert user_source.options == {"query": "vercel railway"}

    deleted = asyncio.run(delete_source("source-1", dependencies, current_user=user))
    user_source = user_source_repository.get_user_source(
        "market-1",
        "source-1",
    )

    assert deleted == {"id": "source-1", "deleted": True}
    assert user_source is not None
    assert user_source.muted is True
    assert user_source.enabled is False


def test_market_source_exclude_and_restore_are_user_scoped() -> None:
    user = User(id="user-1", email="user@example.com")
    other_user = User(id="user-2", email="other@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-2",
            user_id=other_user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
                source_type="hackernews",
                source_family="technical_forum",
                access_mode="api",
                is_gate_free=True,
            )
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
                default_enabled=True,
            )
        ]
    )
    user_source_repository = InMemoryUserSourceRepository()
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_repository=user_source_repository,
    )

    excluded = asyncio.run(
        exclude_market_source(
            "market-1",
            "source-1",
            dependencies,
            current_user=user,
        )
    )
    market_1_sources = asyncio.run(
        list_market_sources("market-1", dependencies, current_user=user)
    )
    market_2_sources = asyncio.run(
        list_market_sources("market-2", dependencies, current_user=other_user)
    )

    assert excluded["enabled"] is True
    assert excluded["muted"] is True
    assert excluded["excluded"] is True
    assert market_1_sources["sources"][0]["excluded"] is True
    assert market_1_sources["summary"]["excluded_count"] == 1
    assert market_1_sources["summary"]["active_count"] == 0
    assert market_1_sources["summary"]["coverage_status"] == "no_active_sources"
    assert market_2_sources["sources"][0]["excluded"] is False
    assert market_2_sources["summary"]["active_count"] == 1
    user_source = user_source_repository.get_user_source("market-1", "source-1")
    assert user_source is not None
    assert user_source.muted is True
    assert user_source.enabled is True

    restored = asyncio.run(
        restore_market_source(
            "market-1",
            "source-1",
            dependencies,
            current_user=user,
        )
    )
    market_1_sources = asyncio.run(
        list_market_sources("market-1", dependencies, current_user=user)
    )

    assert restored["enabled"] is True
    assert restored["muted"] is False
    assert restored["excluded"] is False
    assert market_1_sources["summary"]["excluded_count"] == 0
    assert market_1_sources["summary"]["active_count"] == 1


def test_market_source_restore_reactivates_legacy_deleted_binding() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
                source_type="hackernews",
                source_family="technical_forum",
            )
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
            )
        ]
    )
    user_source_repository = InMemoryUserSourceRepository()
    user_source_repository.save_user_sources(
        [
            UserSource.create(
                id="user-source-1",
                user_niche_id="market-1",
                source_id="source-1",
                template_source_binding_id="binding-1",
                enabled=False,
                muted=True,
            )
        ]
    )
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_repository=user_source_repository,
    )

    restored = asyncio.run(
        restore_market_source(
            "market-1",
            "source-1",
            dependencies,
            current_user=user,
        )
    )

    user_source = user_source_repository.get_user_source("market-1", "source-1")
    assert restored["enabled"] is True
    assert restored["excluded"] is False
    assert user_source is not None
    assert user_source.enabled is True
    assert user_source.muted is False


def test_create_market_source_writes_canonical_and_user_source() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Track developer tooling",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    user_source_repository = InMemoryUserSourceRepository()
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        user_source_repository=user_source_repository,
    )

    created = asyncio.run(
        create_market_source(
            "market-1",
            NicheSourceRequest(
                locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
                source_type="hackernews",
                options={
                    "source_family": "technical_forum",
                    "limit": 10,
                    "scan_frequency": "daily",
                    "query": "vercel",
                },
            ),
            dependencies,
            current_user=user,
        )
    )

    canonical_source = source_repository.get_source_by_identity(
        "hackernews",
        "https://hn.algolia.com/api/v1/search_by_date?query=vercel",
    )
    assert canonical_source is not None
    user_source = user_source_repository.get_user_source(
        "market-1",
        canonical_source.id,
    )
    assert user_source is not None
    assert user_source.limit == 10
    assert user_source.cadence == "daily"
    assert user_source.options == {"query": "vercel"}
    assert created["id"] == canonical_source.id
    assert created["market_id"] == "template-1"
    assert created["options"]["user_source_id"] == user_source.id


def test_pipeline_diagnostics_returns_sanitized_runtime_warnings() -> None:
    user = User(id="user-1", email="user@example.com")
    dependencies = SignalApiDependencies(
        source_adapters=[],
        llm_client=None,
        embedding_client=None,
    )

    response = asyncio.run(
        get_pipeline_diagnostics(dependencies=dependencies, current_user=user)
    )

    assert response["ready"] is False
    assert response["has_llm_client"] is False
    assert response["has_embedding_client"] is False
    assert response["source_adapter_count"] == 0
    assert "pipeline_schedule" in response
    assert "next_run_at" in response
    messages = [item["message"] for item in response["diagnostics"]]
    assert any("LLM client is not configured" in message for message in messages)
    assert any("No source adapters are configured" in message for message in messages)


def test_updates_owned_source_enabled_state() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Build internal tools",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://github.com/appsmithorg/appsmith/issues",
                source_type="github_issues",
                source_family="technical_forum",
                is_gate_free=True,
            )
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
            )
        ]
    )
    user_source_repository = InMemoryUserSourceRepository()
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_repository=user_source_repository,
    )

    updated = asyncio.run(
        update_source(
            "source-1",
            NicheSourceUpdateRequest(enabled=False),
            dependencies,
            current_user=user,
        )
    )

    assert updated["enabled"] is False
    assert updated["management"]["can_enable"] is True
    user_source = user_source_repository.get_user_source("market-1", "source-1")
    assert user_source is not None
    assert user_source.enabled is False


def test_deletes_owned_source() -> None:
    user = User(id="user-1", email="user@example.com")
    user_niche_repository = InMemoryUserNicheRepository()
    user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id=user.id,
            job="Build internal tools",
            buyer="Engineering teams",
            category="devtools",
            template_niche_id="template-1",
        )
    )
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(
        [
            Source.create(
                id="source-1",
                locator="https://github.com/appsmithorg/appsmith/issues",
                source_type="github_issues",
                source_family="technical_forum",
                is_gate_free=True,
            )
        ]
    )
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(
        [
            TemplateSourceBinding.create(
                id="binding-1",
                template_niche_id="template-1",
                source_id="source-1",
            )
        ]
    )
    user_source_repository = InMemoryUserSourceRepository()
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_repository=user_source_repository,
    )

    response = asyncio.run(
        delete_source("source-1", dependencies, current_user=user)
    )

    assert response == {"id": "source-1", "deleted": True}
    user_source = user_source_repository.get_user_source("market-1", "source-1")
    assert user_source is not None
    assert user_source.muted is True


class FakeFindingRepository:
    def __init__(self, findings: list[Finding]) -> None:
        self.findings = findings

    def save_findings(self, findings: list[Finding]) -> int:
        self.findings.extend(findings)
        return len(findings)

    def get_seen_post_ids(
        self,
        user_niche_id: str,
        post_ids: list[str],
    ) -> set[str]:
        post_id_set = set(post_ids)
        return {
            finding.post_id
            for finding in self.findings
            if finding.user_niche_id == user_niche_id
            and finding.post_id in post_id_set
        }

    def list_findings(
        self,
        *,
        user_niche_id: str | None = None,
        unassigned_only: bool = False,
    ) -> list[Finding]:
        findings = self.findings
        if user_niche_id is not None:
            findings = [
                finding
                for finding in findings
                if finding.user_niche_id == user_niche_id
            ]
        return findings


def _finding(
    post_id: str,
    user_niche_id: str,
    category: str,
    detected_at: datetime,
    source_id: str,
) -> Finding:
    return Finding.create(
        user_niche_id=user_niche_id,
        post_id=post_id,
        pain=f"{category} complaint",
        evidence_text=f"{category} evidence",
        structured_embedding_text=f"{category} complaint",
        urgency="medium",
        severity="medium",
        confidence=0.8,
        category=category,
        detected_at=detected_at,
        source_id=source_id,
    )


class FakeThemeRepository:
    def __init__(
        self,
        themes: list[Theme],
        findings_by_theme: dict[str, list[Finding]],
    ) -> None:
        self.themes = themes
        self.findings_by_theme = findings_by_theme

    def save_themes(self, themes: list[Theme]) -> int:
        self.themes.extend(themes)
        return len(themes)

    def save_theme_findings(self, assignments: list[object]) -> int:
        return len(assignments)

    def list_themes(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
    ) -> list[Theme]:
        themes = self.themes
        if user_niche_id is not None:
            themes = [theme for theme in themes if theme.user_niche_id == user_niche_id]
        if status is not None:
            themes = [theme for theme in themes if theme.status == status]
        return themes

    def list_changed_themes(
        self,
        *,
        user_niche_id: str,
        since: object,
    ) -> list[Theme]:
        return [
            theme for theme in self.themes if theme.user_niche_id == user_niche_id
        ]

    def find_similar_themes(
        self,
        user_niche_id: str,
        embedding: list[float],
        *,
        top_k: int = 5,
        min_similarity: float = 0.70,
    ) -> list[Theme]:
        return [
            theme for theme in self.themes if theme.user_niche_id == user_niche_id
        ][:top_k]

    def list_findings_for_theme(self, theme_id: str) -> list[Finding]:
        return self.findings_by_theme.get(theme_id, [])

    def refresh_theme_rollups(self, theme_ids: list[str]) -> int:
        return len(theme_ids)
