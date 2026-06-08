from application.opportunity import OpportunitySynthesisContext
from application.theme_memory import ThemeOpportunitySynthesisService
from domain.finding import Finding
from domain.theme import Theme


def _theme(status: str = "qualified") -> Theme:
    return Theme.create(
        id="c9158d97-9449-4bf2-9ef5-17bb825d522f",
        user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
        title="Schema change reliability",
        summary="Analytics engineers need safer schema changes.",
        status=status,  # type: ignore[arg-type]
        finding_count=2,
        source_count=2,
        average_confidence=0.8,
    )


def _finding(post_id: str, source_id: str) -> Finding:
    return Finding.create(
        id=f"349d4322-1614-48c1-a7d3-b50b3821a27{post_id[-1]}",
        user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
        post_id=post_id,
        pain="Incremental models break on schema changes",
        evidence_text="Incremental models break on schema changes",
        structured_embedding_text="Incremental models break on schema changes",
        urgency="high",
        severity="medium",
        confidence=0.8,
        source_id=source_id,
        affected_user="analytics engineers",
        current_workaround="manual rebuilds",
        category="data reliability",
    )


def test_synthesizes_opportunity_from_qualified_theme():
    result = ThemeOpportunitySynthesisService().synthesize(
        _theme(),
        [_finding("post-1", "source-1"), _finding("post-2", "source-2")],
        OpportunitySynthesisContext(objective="Find data warehouse workflow gaps"),
    )

    assert result.opportunity is not None
    assert result.opportunity.cluster_id is None
    assert result.opportunity.source_theme_id == "c9158d97-9449-4bf2-9ef5-17bb825d522f"
    assert result.opportunity.evidence_count == 2
    assert result.opportunity.target_user == "analytics engineers"
    assert result.opportunity.unmet_need_type == "time"
    assert "research objective" in result.opportunity.why_it_matters


def test_skips_unqualified_theme():
    result = ThemeOpportunitySynthesisService().synthesize(
        _theme(status="emerging"),
        [_finding("post-1", "source-1"), _finding("post-2", "source-2")],
    )

    assert result.opportunity is None
    assert result.reason == "theme_not_qualified"
