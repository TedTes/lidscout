"""Feedback-aware opportunity ranking for the research agent."""
from domain.agent import AgentFeedback
from domain.opportunity import Opportunity


MIN_FEEDBACK_FOR_PERSONALIZATION = 1
SAVE_BOOST = 0.25
MORE_LIKE_THIS_BOOST = 0.15
LESS_LIKE_THIS_PENALTY = 0.25
DISMISS_PENALTY = 0.4
EXPLORATION_SLOT_INDEX = 1


def rank_opportunities_with_feedback(
    opportunities: list[Opportunity],
    feedback: list[AgentFeedback],
) -> list[Opportunity]:
    """Rank opportunities with lightweight feedback boosts and penalties."""
    if not opportunities:
        return []

    feedback_by_opportunity: dict[str, list[AgentFeedback]] = {}
    for item in feedback:
        feedback_by_opportunity.setdefault(item.opportunity_id, []).append(item)

    base_ranked = _sort_by_base_score(opportunities)
    if not _has_enough_feedback(feedback):
        return base_ranked

    ranked = sorted(
        opportunities,
        key=lambda opportunity: _ranking_key(
            opportunity,
            feedback_by_opportunity.get(opportunity.id, []),
        ),
        reverse=True,
    )
    return _with_exploration_slot(ranked, base_ranked, feedback_by_opportunity)


def _sort_by_base_score(opportunities: list[Opportunity]) -> list[Opportunity]:
    return sorted(
        opportunities,
        key=lambda opportunity: (
            _base_score(opportunity),
            opportunity.evidence_count,
            opportunity.confidence,
        ),
        reverse=True,
    )


def _has_enough_feedback(feedback: list[AgentFeedback]) -> bool:
    saved_count = sum(1 for item in feedback if item.action == "save")
    dismissed_count = sum(1 for item in feedback if item.action == "dismiss")
    return (
        saved_count >= MIN_FEEDBACK_FOR_PERSONALIZATION
        or dismissed_count >= MIN_FEEDBACK_FOR_PERSONALIZATION
    )


def _ranking_key(
    opportunity: Opportunity,
    feedback: list[AgentFeedback],
) -> tuple[float, int, float]:
    return (
        _feedback_adjusted_score(opportunity, feedback),
        opportunity.evidence_count,
        opportunity.confidence,
    )


def _feedback_adjusted_score(
    opportunity: Opportunity,
    feedback: list[AgentFeedback],
) -> float:
    score = _base_score(opportunity)
    for item in feedback:
        if item.action == "save":
            score += SAVE_BOOST
        elif item.action == "more_like_this":
            score += MORE_LIKE_THIS_BOOST
        elif item.action == "less_like_this":
            score -= LESS_LIKE_THIS_PENALTY
        elif item.action == "dismiss":
            score -= DISMISS_PENALTY
    return score


def _base_score(opportunity: Opportunity) -> float:
    return opportunity.confidence + min(opportunity.evidence_count, 10) / 100


def _with_exploration_slot(
    ranked: list[Opportunity],
    base_ranked: list[Opportunity],
    feedback_by_opportunity: dict[str, list[AgentFeedback]],
) -> list[Opportunity]:
    explorer = next(
        (
            opportunity
            for opportunity in base_ranked
            if opportunity.id not in feedback_by_opportunity
        ),
        None,
    )
    if explorer is None or explorer in ranked[: EXPLORATION_SLOT_INDEX + 1]:
        return ranked

    without_explorer = [opportunity for opportunity in ranked if opportunity != explorer]
    insert_at = min(EXPLORATION_SLOT_INDEX, len(without_explorer))
    return [
        *without_explorer[:insert_at],
        explorer,
        *without_explorer[insert_at:],
    ]
