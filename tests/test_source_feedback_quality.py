from application.source_quality import (
    feedback_adjusted_source_confidence,
    source_feedback_stats,
)
from domain.agent import AgentFeedback


def test_source_feedback_stats_attributes_feedback_to_sources() -> None:
    feedback = [
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="opportunity-1",
            action="save",
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="opportunity-2",
            action="dismiss",
            reason="Evidence too thin",
        ),
    ]

    stats = source_feedback_stats(
        feedback=feedback,
        opportunity_source_ids={
            "opportunity-1": {"source-a", "source-b"},
            "opportunity-2": {"source-b"},
        },
    )

    by_source = {item.source_id: item for item in stats}
    assert by_source["source-a"].saved_count == 1
    assert by_source["source-a"].dismissed_count == 0
    assert by_source["source-b"].saved_count == 1
    assert by_source["source-b"].dismissed_count == 1
    assert by_source["source-b"].dismiss_reasons == {"Evidence too thin": 1}


def test_feedback_adjusted_source_confidence_is_bounded() -> None:
    stats = source_feedback_stats(
        feedback=[
            AgentFeedback.create(
                user_niche_id="market-1",
                opportunity_id="opportunity-1",
                action="dismiss",
            )
        ],
        opportunity_source_ids={"opportunity-1": {"source-a"}},
    )[0]

    assert feedback_adjusted_source_confidence(
        base_confidence=0.2,
        stats=stats,
    ) == 0.3

    positive_stats = source_feedback_stats(
        feedback=[
            AgentFeedback.create(
                user_niche_id="market-1",
                opportunity_id=f"opportunity-{idx}",
                action="save",
            )
            for idx in range(3)
        ],
        opportunity_source_ids={
            "opportunity-0": {"source-a"},
            "opportunity-1": {"source-a"},
            "opportunity-2": {"source-a"},
        },
    )[0]
    assert feedback_adjusted_source_confidence(
        base_confidence=0.9,
        stats=positive_stats,
    ) == 1.4
