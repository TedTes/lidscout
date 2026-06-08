import asyncio
from datetime import UTC, datetime

from api.routes.signals import (
    SignalApiDependencies,
    list_clusters,
    list_opportunities,
    list_themes,
)
from domain.cluster import SignalCluster
from domain.finding import Finding
from domain.niche import NicheCompany, UserNiche
from domain.opportunity import Opportunity
from domain.signal import Signal
from domain.theme import Theme


class FakeThemeRepository:
    def __init__(self) -> None:
        self.themes: list[Theme] = []
        self.findings_by_theme_id: dict[str, list[Finding]] = {}

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

    def list_changed_themes(self, *, user_niche_id: str, since: object) -> list[Theme]:
        return [theme for theme in self.themes if theme.user_niche_id == user_niche_id]

    def list_findings_for_theme(self, theme_id: str) -> list[Finding]:
        return self.findings_by_theme_id.get(theme_id, [])

    def refresh_theme_rollups(self, theme_ids: list[str]) -> int:
        return len(theme_ids)


def test_opportunities_include_evidence_items_with_source_attribution() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_scope(dependencies)
    dependencies.signal_repository.save_signals(
        [
            Signal.create(
                id="signal-1",
                post_id="github:item-1",
                pain="Migrations fail on schema drift",
                user_type="analytics engineers",
                urgency="high",
                severity="high",
                willingness_to_pay=True,
                category="data reliability",
                confidence=0.91,
                niche_company_id="company-1",
                niche_id="niche-1",
                evidence_url="https://github.com/example/tool/issues/123",
                evidence_text="The incremental model breaks whenever the schema changes.",
                detected_at=datetime(2026, 6, 7, 1, 0, tzinfo=UTC),
            )
        ]
    )
    dependencies.opportunity_repository.save_opportunities(
        [
            Opportunity.create(
                id="opportunity-1",
                cluster_id="cluster-1",
                title="Reliable schema-change handling",
                target_user="analytics engineers",
                pain_summary="Schema drift breaks dbt workflows.",
                why_it_matters="Teams lose trust in warehouse transforms.",
                suggested_wedge="Detect and repair schema drift before deployment.",
                evidence_count=1,
                confidence=0.72,
                evidence_signal_ids=["signal-1"],
                unmet_need_type="capability",
            )
        ]
    )

    response = asyncio.run(list_opportunities(dependencies, market_id="market-1"))

    opportunity = response["opportunities"][0]
    assert opportunity["source_family_breakdown"] == [
        {"source_family": "technical_forum", "count": 1}
    ]
    assert opportunity["evidence_items"] == [
        {
            "id": "signal-1",
            "signal_id": "signal-1",
            "post_id": "github:item-1",
            "quote": "The incremental model breaks whenever the schema changes.",
            "pain": "Migrations fail on schema drift",
            "url": "https://github.com/example/tool/issues/123",
            "source_label": "GitHub",
            "source_family": "technical_forum",
            "source_type": "github_issues",
            "company_id": "company-1",
            "company_name": "Example Tool",
            "category": "data reliability",
            "urgency": "high",
            "severity": "high",
            "confidence": 0.91,
            "detected_at": "2026-06-07T01:00:00+00:00",
        }
    ]


def test_theme_backed_opportunities_include_durable_finding_evidence() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_scope(dependencies)
    theme_repository = FakeThemeRepository()
    theme = Theme.create(
        id="c9158d97-9449-4bf2-9ef5-17bb825d522f",
        user_niche_id="market-1",
        title="Schema change reliability",
        summary="Analytics engineers need safer schema changes.",
        status="qualified",
        finding_count=2,
        source_count=2,
        average_confidence=0.83,
    )
    finding = Finding.create(
        id="349d4322-1614-48c1-a7d3-b50b3821a27c",
        user_niche_id="market-1",
        niche_id="niche-1",
        source_id="source-1",
        company_id="company-1",
        post_id="github:item-1",
        pain="Incremental models break on schema changes",
        evidence_text="The incremental model breaks whenever the schema changes.",
        structured_embedding_text="Incremental models break on schema changes",
        urgency="high",
        severity="high",
        confidence=0.91,
        evidence_url="https://github.com/example/tool/issues/123",
        affected_user="analytics engineers",
        category="data reliability",
        detected_at=datetime(2026, 6, 7, 1, 0, tzinfo=UTC),
        metadata={
            "source_family": "technical_forum",
            "source_type": "github_issues",
        },
    )
    theme_repository.save_themes([theme])
    theme_repository.findings_by_theme_id[theme.id] = [finding]
    dependencies.theme_repository = theme_repository
    dependencies.opportunity_repository.save_opportunities(
        [
            Opportunity.create(
                id="opportunity-theme-c9158d97-9449-4bf2-9ef5-17bb825d522f",
                cluster_id=None,
                source_theme_id=theme.id,
                title="Reliable schema-change handling",
                target_user="analytics engineers",
                pain_summary="Schema drift breaks warehouse workflows.",
                why_it_matters="Teams lose trust in transforms.",
                suggested_wedge="Detect and repair schema drift before deployment.",
                evidence_count=2,
                confidence=0.76,
                evidence_signal_ids=[finding.id],
                unmet_need_type="capability",
            )
        ]
    )

    response = asyncio.run(list_opportunities(dependencies, market_id="market-1"))

    opportunity = response["opportunities"][0]
    assert opportunity["cluster_id"] is None
    assert opportunity["source_theme_id"] == theme.id
    assert opportunity["evidence_source_count"] == 1
    assert opportunity["source_family_breakdown"] == [
        {"source_family": "technical_forum", "count": 1}
    ]
    assert opportunity["evidence_items"] == [
        {
            "id": "349d4322-1614-48c1-a7d3-b50b3821a27c",
            "signal_id": None,
            "post_id": "github:item-1",
            "quote": "The incremental model breaks whenever the schema changes.",
            "pain": "Incremental models break on schema changes",
            "url": "https://github.com/example/tool/issues/123",
            "source_label": "GitHub",
            "source_family": "technical_forum",
            "source_type": "github_issues",
            "company_id": "company-1",
            "company_name": "Example Tool",
            "category": "data reliability",
            "urgency": "high",
            "severity": "high",
            "confidence": 0.91,
            "detected_at": "2026-06-07T01:00:00+00:00",
        }
    ]


def test_clusters_include_source_family_breakdown() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_scope(dependencies)
    dependencies.signal_repository.save_signals(
        [
            Signal.create(
                id="signal-1",
                post_id="github:item-1",
                pain="GitHub issue pain",
                urgency="medium",
                severity="medium",
                category="developer workflow",
                confidence=0.8,
                niche_company_id="company-1",
                niche_id="niche-1",
                evidence_url="https://github.com/example/tool/issues/123",
                evidence_text="This issue blocks our rollout.",
            ),
            Signal.create(
                id="signal-2",
                post_id="reddit:item-2",
                pain="Reddit complaint",
                urgency="medium",
                severity="medium",
                category="developer workflow",
                confidence=0.7,
                niche_company_id="company-1",
                niche_id="niche-1",
                evidence_url="https://www.reddit.com/r/devtools/comments/abc/example",
                evidence_text="This workflow is painful.",
            ),
        ]
    )
    dependencies.cluster_repository.save_clusters(
        [
            SignalCluster.create(
                id="cluster-1",
                theme="workflow reliability",
                summary="Users report repeated workflow reliability issues.",
                signal_ids=["signal-1", "signal-2"],
                frequency=2,
                average_score=7.2,
                top_examples=["This issue blocks our rollout."],
            )
        ]
    )

    response = asyncio.run(list_clusters(dependencies, market_id="market-1"))

    assert response["clusters"][0]["source_family_breakdown"] == [
        {"source_family": "social", "count": 1},
        {"source_family": "technical_forum", "count": 1},
    ]


def test_themes_include_durable_evidence_and_source_breakdown() -> None:
    dependencies = SignalApiDependencies()
    _seed_market_scope(dependencies)
    theme_repository = FakeThemeRepository()
    theme = Theme.create(
        id="c9158d97-9449-4bf2-9ef5-17bb825d522f",
        user_niche_id="market-1",
        title="Schema change reliability",
        summary="Analytics engineers need safer schema changes.",
        status="qualified",
        finding_count=1,
        source_count=1,
        company_count=1,
        average_confidence=0.83,
    )
    finding = Finding.create(
        id="349d4322-1614-48c1-a7d3-b50b3821a27c",
        user_niche_id="market-1",
        niche_id="niche-1",
        source_id="source-1",
        company_id="company-1",
        post_id="github:item-1",
        pain="Incremental models break on schema changes",
        evidence_text="The incremental model breaks whenever the schema changes.",
        structured_embedding_text="Incremental models break on schema changes",
        urgency="high",
        severity="high",
        confidence=0.91,
        evidence_url="https://github.com/example/tool/issues/123",
        affected_user="analytics engineers",
        category="data reliability",
        detected_at=datetime(2026, 6, 7, 1, 0, tzinfo=UTC),
        metadata={
            "source_family": "technical_forum",
            "source_type": "github_issues",
        },
    )
    theme_repository.save_themes([theme])
    theme_repository.findings_by_theme_id[theme.id] = [finding]
    dependencies.theme_repository = theme_repository

    response = asyncio.run(list_themes(dependencies, market_id="market-1"))

    serialized = response["themes"][0]
    assert serialized["id"] == theme.id
    assert serialized["theme"] == "Schema change reliability"
    assert serialized["status"] == "qualified"
    assert serialized["qualification_status"] == "qualified"
    assert serialized["finding_ids"] == [finding.id]
    assert serialized["frequency"] == 1
    assert serialized["average_score"] == 8.3
    assert serialized["company_names"] == ["Example Tool"]
    assert serialized["source_family_breakdown"] == [
        {"source_family": "technical_forum", "count": 1}
    ]
    assert serialized["evidence_items"][0]["source_label"] == "GitHub"


def _seed_market_scope(dependencies: SignalApiDependencies) -> None:
    dependencies.user_niche_repository.save_user_niche(
        UserNiche.create(
            id="market-1",
            user_id="user-1",
            job="Transform data in the warehouse",
            buyer="Analytics engineers",
            category="data",
            template_niche_id="niche-1",
        )
    )
    dependencies.niche_company_repository.save_niche_companies(
        [
            NicheCompany.create(
                id="company-1",
                niche_id="niche-1",
                name="Example Tool",
            )
        ]
    )
