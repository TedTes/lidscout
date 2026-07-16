from application.agent.ranking import rank_opportunities_with_feedback
from domain.agent import AgentFeedback
from domain.opportunity import Opportunity


def test_feedback_ranking_applies_first_save_immediately() -> None:
    opportunities = [
        _opportunity("saved-low", confidence=0.6),
        _opportunity("control-high", confidence=0.8),
    ]
    feedback = [
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="saved-low",
            action="save",
        )
    ]

    ranked = rank_opportunities_with_feedback(opportunities, feedback)

    assert [item.id for item in ranked] == ["saved-low", "control-high"]


def test_feedback_ranking_applies_after_threshold() -> None:
    opportunities = [
        _opportunity("saved-low", confidence=0.6),
        _opportunity("control-high", confidence=0.8),
    ]
    feedback = [
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="saved-low",
            action="save",
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="historical-save-1",
            action="save",
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="historical-save-2",
            action="save",
        ),
    ]

    ranked = rank_opportunities_with_feedback(opportunities, feedback)

    assert [item.id for item in ranked] == ["saved-low", "control-high"]


def test_feedback_ranking_keeps_unfeedbacked_exploration_slot() -> None:
    opportunities = [
        _opportunity("saved-a", confidence=0.75),
        _opportunity("saved-b", confidence=0.74),
        _opportunity("unseen", confidence=0.73),
    ]
    feedback = [
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="saved-a",
            action="save",
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="saved-b",
            action="save",
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="historical-save",
            action="save",
        ),
    ]

    ranked = rank_opportunities_with_feedback(opportunities, feedback)

    assert [item.id for item in ranked] == ["saved-a", "unseen", "saved-b"]


def _opportunity(opportunity_id: str, *, confidence: float) -> Opportunity:
    return Opportunity.create(
        id=opportunity_id,
        cluster_id=f"cluster-{opportunity_id}",
        title=opportunity_id,
        target_user="operators",
        pain_summary="Pain summary",
        why_it_matters="Why it matters",
        suggested_wedge="Suggested wedge",
        evidence_count=1,
        confidence=confidence,
        evidence_signal_ids=[f"signal-{opportunity_id}"],
    )
