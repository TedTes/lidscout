import asyncio

from api.routes.signals import (
    NicheSourceRequest,
    NicheSourceUpdateRequest,
    SignalApiDependencies,
    create_market_source,
    delete_source,
    exclude_market_source,
    get_pipeline_diagnostics,
    list_market_sources,
    restore_market_source,
    update_source,
)
from domain.niche import (
    TemplateSourceBinding,
    UserNiche,
    UserSource,
    UserSourcePreference,
    UserSourceRunStats,
)
from domain.source import Source
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


def test_market_sources_include_replacement_suggestions_for_blocked_sources() -> None:
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
                locator="https://www.reddit.com/search.json?q=retool&sort=new",
                source_type="reddit_search",
                source_family="social",
                is_gate_free=False,
                access_mode="api_auth",
                requires_auth=True,
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
                default_enabled=False,
            )
        ]
    )
    dependencies = SignalApiDependencies(
        user_niche_repository=user_niche_repository,
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
    )

    response = asyncio.run(
        list_market_sources("market-1", dependencies, current_user=user)
    )

    suggestions = response["sources"][0]["replacement_suggestions"]
    assert response["sources"][0]["quality_status"] == "blocked"
    assert response["sources"][0]["scan_eligible"] is False
    assert response["sources"][0]["scan_ineligible_reason"] == "Source is disabled."
    assert response["sources"][0]["management"]["recommended_action"] == "enable_or_remove"
    assert suggestions[0]["trigger"] == "blocked_source"
    assert suggestions[0]["replaces_source_id"] == "source-1"
    assert suggestions[0]["candidate"]["source_type"] == "hackernews_search"
    assert suggestions[0]["candidate"]["market_name"] == "Build internal tools"


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
