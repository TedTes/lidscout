"""Signal scoring service."""
from dataclasses import dataclass, replace

from application.ports import ScoreRepository
from domain.score import OpportunityScore, calculate_opportunity_score
from domain.signal import Signal
from shared.logger import get_logger, log_event


logger = get_logger(__name__)


@dataclass(frozen=True)
class ScoringResult:
    """Counts and aggregate score for a scoring run."""

    scored_count: int
    failed_count: int
    average_score: float


OpportunityScoreRepository = ScoreRepository


class ScoringService:
    """Scores signals and persists opportunity scores."""

    def __init__(self, repository: ScoreRepository):
        self.repository = repository

    def score(self, signals: list[Signal]) -> ScoringResult:
        failed_count = 0
        scores: list[OpportunityScore] = []

        for signal in signals:
            try:
                base_score = OpportunityScore.from_signal(signal)
                scores.append(
                    replace(
                        base_score,
                        total_score=calculate_opportunity_score(signal),
                    )
                )
            except (KeyError, ValueError):
                failed_count += 1

        saved_count = self.repository.save_scores(scores)
        failed_count += len(scores) - saved_count
        average_score = (
            round(sum(score.total_score for score in scores[:saved_count]) / saved_count, 2)
            if saved_count
            else 0.0
        )

        result = ScoringResult(
            scored_count=saved_count,
            failed_count=failed_count,
            average_score=average_score,
        )
        log_event(
            logger,
            "scoring_completed",
            scored_count=result.scored_count,
            failed_count=result.failed_count,
            average_score=result.average_score,
        )
        return result
