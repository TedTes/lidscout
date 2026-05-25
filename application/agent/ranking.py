"""Feedback-aware opportunity ranking for the research agent."""
from domain.agent import AgentFeedback
from domain.opportunity import Opportunity


def rank_opportunities_with_feedback(
    opportunities: list[Opportunity],
    feedback: list[AgentFeedback],
) -> list[Opportunity]:
    """Rank opportunities with lightweight feedback boosts and penalties."""
    feedback_by_opportunity: dict[str, list[AgentFeedback]] = {}
    for item in feedback:
        feedback_by_opportunity.setdefault(item.opportunity_id, []).append(item)

    return sorted(
        opportunities,
        key=lambda opportunity: (
            _feedback_adjusted_score(
                opportunity,
                feedback_by_opportunity.get(opportunity.id, []),
            ),
            opportunity.evidence_count,
            opportunity.confidence,
        ),
        reverse=True,
    )


def _feedback_adjusted_score(
    opportunity: Opportunity,
    feedback: list[AgentFeedback],
) -> float:
    score = opportunity.confidence + min(opportunity.evidence_count, 10) / 100
    for item in feedback:
        if item.action == "save":
            score += 0.25
        elif item.action == "more_like_this":
            score += 0.15
        elif item.action == "less_like_this":
            score -= 0.25
        elif item.action == "dismiss":
            score -= 0.4
    return score
