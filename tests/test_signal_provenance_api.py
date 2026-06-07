import asyncio
from datetime import UTC, datetime

from api.routes.signals import SignalApiDependencies, list_clusters, list_opportunities
from domain.cluster import SignalCluster
from domain.niche import NicheCompany, UserNiche
from domain.opportunity import Opportunity
from domain.signal import Signal


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
