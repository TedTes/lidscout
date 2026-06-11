from datetime import UTC, datetime

from application.agent import build_agent_feedback_summary
from domain.agent import AgentFeedback


def test_build_agent_feedback_summary_counts_actions_and_reasons() -> None:
    feedback = [
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="opportunity-saved",
            action="save",
            comment="Useful roadmap input.",
            created_at=datetime(2026, 6, 10, 12, 0, tzinfo=UTC),
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="opportunity-dismissed",
            action="dismiss",
            reason="Evidence too thin",
            comment="Needs another source.",
            created_at=datetime(2026, 6, 10, 12, 5, tzinfo=UTC),
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="opportunity-dismissed-2",
            action="dismiss",
            reason="Evidence too thin",
            created_at=datetime(2026, 6, 10, 12, 10, tzinfo=UTC),
        ),
        AgentFeedback.create(
            user_niche_id="market-1",
            opportunity_id="opportunity-training",
            action="more_like_this",
            created_at=datetime(2026, 6, 10, 12, 15, tzinfo=UTC),
        ),
    ]

    summary = build_agent_feedback_summary(
        market_id="market-1",
        feedback=feedback,
    )

    assert summary.feedback_count == 4
    assert summary.saved_count == 1
    assert summary.dismissed_count == 2
    assert summary.positive_training_count == 1
    assert summary.negative_training_count == 0
    assert summary.actioned_opportunity_count == 3
    assert summary.dismiss_rate == 0.6667
    assert summary.dismiss_reasons[0].reason == "Evidence too thin"
    assert summary.dismiss_reasons[0].count == 2
    assert summary.recent_comments[0].comment == "Needs another source."
