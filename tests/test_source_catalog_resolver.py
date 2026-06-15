from application.source_catalog import SourceCatalogResolver
from domain.niche import TemplateSourceBinding, UserSource, UserSourcePreference
from domain.source import Source
from infrastructure.db import (
    InMemorySourceRepository,
    InMemoryTemplateSourceBindingRepository,
    InMemoryUserSourceRepository,
    InMemoryUserSourcePreferenceRepository,
)


def _resolver(
    *,
    sources: list[Source],
    bindings: list[TemplateSourceBinding],
    user_sources: list[UserSource] | None = None,
    preferences: list[UserSourcePreference] | None = None,
) -> SourceCatalogResolver:
    source_repository = InMemorySourceRepository()
    source_repository.save_sources(sources)
    binding_repository = InMemoryTemplateSourceBindingRepository()
    binding_repository.save_template_source_bindings(bindings)
    preference_repository = InMemoryUserSourcePreferenceRepository()
    for preference in preferences or []:
        preference_repository.save_user_source_preference(preference)
    user_source_repository = InMemoryUserSourceRepository()
    user_source_repository.save_user_sources(user_sources or [])
    return SourceCatalogResolver(
        source_repository=source_repository,
        template_source_binding_repository=binding_repository,
        user_source_preference_repository=preference_repository,
        user_source_repository=user_source_repository,
    )


def test_resolver_inherits_template_source_defaults() -> None:
    source = Source.create(
        id="source-1",
        locator="https://api.github.com/search/issues?q=repo:owner/repo",
        source_type="github_issues_search",
        source_family="technical_forum",
        access_mode="api",
        is_gate_free=True,
    )
    binding = TemplateSourceBinding.create(
        id="binding-1",
        template_niche_id="template-1",
        source_id="source-1",
        default_limit=25,
        default_scan_frequency="daily",
        default_buyer_voice_verified=True,
        default_options={"items_path": "items"},
        tier=1,
        signal_quality_score=0.95,
    )

    resolved = _resolver(sources=[source], bindings=[binding]).list_effective_sources(
        template_niche_id="template-1",
    )

    assert len(resolved) == 1
    assert resolved[0].source_id == "source-1"
    assert resolved[0].enabled is True
    assert resolved[0].limit == 25
    assert resolved[0].scan_frequency == "daily"
    assert resolved[0].buyer_voice_verified is True
    assert resolved[0].options == {"items_path": "items"}
    assert resolved[0].to_source_input().options["source_type"] == "github_issues_search"


def test_resolver_applies_user_preference_overrides() -> None:
    source = Source.create(
        id="source-1",
        locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
        source_type="hackernews",
        source_family="technical_forum",
    )
    binding = TemplateSourceBinding.create(
        id="binding-1",
        template_niche_id="template-1",
        source_id="source-1",
        default_limit=25,
        default_scan_frequency="daily",
        default_options={"query": "vercel", "tags": "comment"},
        tier=2,
    )
    preference = UserSourcePreference.create(
        id="preference-1",
        user_niche_id="user-niche-1",
        source_id="source-1",
        enabled=False,
        cadence_override="weekly",
        priority_override=1,
        limit_override=10,
        options_override={"query": "vercel railway"},
    )

    resolved = _resolver(
        sources=[source],
        bindings=[binding],
        preferences=[preference],
    ).list_effective_sources(
        template_niche_id="template-1",
        user_niche_id="user-niche-1",
        enabled=False,
    )

    assert len(resolved) == 1
    assert resolved[0].enabled is False
    assert resolved[0].scan_frequency == "weekly"
    assert resolved[0].priority == 1
    assert resolved[0].limit == 10
    assert resolved[0].options == {"query": "vercel railway", "tags": "comment"}


def test_resolver_prefers_user_source_over_legacy_preference() -> None:
    source = Source.create(
        id="source-1",
        locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
        source_type="hackernews",
        source_family="technical_forum",
    )
    binding = TemplateSourceBinding.create(
        id="binding-1",
        template_niche_id="template-1",
        source_id="source-1",
        default_limit=25,
        default_scan_frequency="daily",
        default_options={"query": "vercel", "tags": "comment"},
        tier=2,
    )
    user_source = UserSource.create(
        id="user-source-1",
        user_niche_id="user-niche-1",
        source_id="source-1",
        template_source_binding_id="binding-1",
        enabled=False,
        cadence="weekly",
        priority=1,
        limit=10,
        options={"query": "vercel railway"},
    )
    preference = UserSourcePreference.create(
        id="preference-1",
        user_niche_id="user-niche-1",
        source_id="source-1",
        enabled=True,
        cadence_override="monthly",
        priority_override=9,
        limit_override=100,
        options_override={"query": "legacy preference"},
    )

    resolved = _resolver(
        sources=[source],
        bindings=[binding],
        user_sources=[user_source],
        preferences=[preference],
    ).list_effective_sources(
        template_niche_id="template-1",
        user_niche_id="user-niche-1",
        enabled=False,
    )

    assert len(resolved) == 1
    assert resolved[0].user_source_id == "user-source-1"
    assert resolved[0].user_source_preference_id is None
    assert resolved[0].enabled is False
    assert resolved[0].scan_frequency == "weekly"
    assert resolved[0].priority == 1
    assert resolved[0].limit == 10
    assert resolved[0].options == {"query": "vercel railway", "tags": "comment"}


def test_resolver_includes_user_only_source_bindings() -> None:
    source = Source.create(
        id="source-2",
        locator="https://www.reddit.com/r/SaaS",
        source_type="reddit",
        source_family="social",
    )
    user_source = UserSource.create(
        id="user-source-2",
        user_niche_id="user-niche-1",
        source_id="source-2",
        cadence="daily",
        limit=15,
        options={"subreddit": "SaaS"},
    )

    resolved = _resolver(
        sources=[source],
        bindings=[],
        user_sources=[user_source],
    ).list_effective_sources(
        template_niche_id="template-1",
        user_niche_id="user-niche-1",
    )

    assert len(resolved) == 1
    assert resolved[0].source_id == "source-2"
    assert resolved[0].template_source_binding_id is None
    assert resolved[0].user_source_id == "user-source-2"
    assert resolved[0].enabled is True
    assert resolved[0].limit == 15
    assert resolved[0].scan_frequency == "daily"
    assert resolved[0].options == {"subreddit": "SaaS"}


def test_resolver_filters_muted_sources_unless_requested() -> None:
    source = Source.create(
        id="source-1",
        locator="https://www.reddit.com/r/SaaS",
        source_type="reddit",
        source_family="social",
    )
    binding = TemplateSourceBinding.create(
        id="binding-1",
        template_niche_id="template-1",
        source_id="source-1",
    )
    preference = UserSourcePreference.create(
        id="preference-1",
        user_niche_id="user-niche-1",
        source_id="source-1",
        muted=True,
    )
    resolver = _resolver(
        sources=[source],
        bindings=[binding],
        preferences=[preference],
    )

    assert resolver.list_effective_sources(
        template_niche_id="template-1",
        user_niche_id="user-niche-1",
    ) == []
    resolved = resolver.list_effective_sources(
        template_niche_id="template-1",
        user_niche_id="user-niche-1",
        include_muted=True,
    )
    assert len(resolved) == 1
    assert resolved[0].muted is True
    # enabled reflects the binding's default, not the muted override — callers
    # use the muted flag to determine net-active state
    assert resolved[0].enabled is True


def test_resolver_filters_muted_user_sources_while_preserving_enabled_state() -> None:
    source = Source.create(
        id="source-1",
        locator="https://hn.algolia.com/api/v1/search_by_date?query=vercel",
        source_type="hackernews",
        source_family="technical_forum",
    )
    binding = TemplateSourceBinding.create(
        id="binding-1",
        template_niche_id="template-1",
        source_id="source-1",
    )
    user_source = UserSource.create(
        id="user-source-1",
        user_niche_id="user-niche-1",
        source_id="source-1",
        template_source_binding_id="binding-1",
        enabled=True,
        muted=True,
    )
    resolver = _resolver(
        sources=[source],
        bindings=[binding],
        user_sources=[user_source],
    )

    assert resolver.list_effective_sources(
        template_niche_id="template-1",
        user_niche_id="user-niche-1",
        enabled=True,
    ) == []
    resolved = resolver.list_effective_sources(
        template_niche_id="template-1",
        user_niche_id="user-niche-1",
        enabled=True,
        include_muted=True,
    )

    assert len(resolved) == 1
    assert resolved[0].enabled is True
    assert resolved[0].muted is True


def test_resolver_skips_bindings_without_canonical_source() -> None:
    binding = TemplateSourceBinding.create(
        id="binding-1",
        template_niche_id="template-1",
        source_id="missing-source",
    )

    resolved = _resolver(sources=[], bindings=[binding]).list_effective_sources(
        template_niche_id="template-1",
    )

    assert resolved == []
