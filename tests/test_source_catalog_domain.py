import pytest

from domain.niche import (
    TemplateSourceBinding,
    UserSourcePreference,
    UserSourceRunStats,
)
from domain.source import Source


def test_source_create_normalizes_identity_and_access_mode() -> None:
    source = Source.create(
        locator=" https://hn.algolia.com/api/v1/search_by_date?query=vercel ",
        source_type=" HackerNews ",
        source_family=" Technical_Forum ",
        access_mode=" API ",
        is_gate_free=True,
    )

    assert source.locator == "https://hn.algolia.com/api/v1/search_by_date?query=vercel"
    assert source.source_type == "hackernews"
    assert source.source_family == "technical_forum"
    assert source.access_mode == "api"
    assert source.is_gate_free is True


def test_source_create_rejects_invalid_access_mode() -> None:
    with pytest.raises(ValueError, match="unsupported access_mode"):
        Source.create(
            locator="https://example.com",
            source_type="web",
            source_family="reviews",
            access_mode="crawler",
        )


def test_template_source_binding_validates_quality_defaults() -> None:
    binding = TemplateSourceBinding.create(
        template_niche_id="template-1",
        source_id="source-1",
        default_limit=25,
        tier=2,
        signal_quality_score=0.78,
        recommended_cadence=" daily ",
    )

    assert binding.default_limit == 25
    assert binding.tier == 2
    assert binding.signal_quality_score == 0.78
    assert binding.recommended_cadence == "daily"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("default_limit", 0, "default_limit must be at least 1"),
        ("tier", 6, "tier must be between 1 and 5"),
        ("signal_quality_score", 1.01, "signal_quality_score must be between 0 and 1"),
    ],
)
def test_template_source_binding_rejects_invalid_defaults(
    field: str,
    value: int | float,
    message: str,
) -> None:
    values = {
        "template_niche_id": "template-1",
        "source_id": "source-1",
        field: value,
    }

    with pytest.raises(ValueError, match=message):
        TemplateSourceBinding.create(**values)


def test_user_source_preference_resolves_nullable_enabled() -> None:
    inherited = UserSourcePreference.create(
        user_niche_id="user-niche-1",
        source_id="source-1",
        enabled=None,
    )
    disabled = UserSourcePreference.create(
        user_niche_id="user-niche-1",
        source_id="source-2",
        enabled=False,
    )

    assert inherited.effective_enabled(default_enabled=True) is True
    assert inherited.effective_enabled(default_enabled=False) is False
    assert disabled.effective_enabled(default_enabled=True) is False


def test_user_source_preference_rejects_invalid_overrides() -> None:
    with pytest.raises(ValueError, match="limit_override must be at least 1"):
        UserSourcePreference.create(
            user_niche_id="user-niche-1",
            source_id="source-1",
            limit_override=0,
        )


def test_user_source_run_stats_validates_and_cleans_counts() -> None:
    stats = UserSourceRunStats.create(
        user_niche_id=" user-niche-1 ",
        source_id=" source-1 ",
        template_source_binding_id=" binding-1 ",
        total_runs=1,
        success_count=1,
        last_status="healthy",
        rejection_breakdown={" wrong_subject ": 2},
    )

    assert stats.user_niche_id == "user-niche-1"
    assert stats.source_id == "source-1"
    assert stats.template_source_binding_id == "binding-1"
    assert stats.rejection_breakdown == {"wrong_subject": 2}


def test_user_source_run_stats_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="total_runs must be non-negative"):
        UserSourceRunStats.create(
            user_niche_id="user-niche-1",
            source_id="source-1",
            total_runs=-1,
        )
