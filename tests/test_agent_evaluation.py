import unittest
from pathlib import Path

from application.agent import rank_opportunities_with_feedback
from application.agent.evaluation import (
    evaluate_agent_ranker,
    load_labeled_agent_ranking_examples,
)
from domain.agent import AgentFeedback
from domain.opportunity import Opportunity


class AgentEvaluationTests(unittest.TestCase):
    def test_feedback_aware_ranker_boosts_saved_opportunities(self):
        saved = self._opportunity("opportunity-saved", confidence=0.62)
        control = self._opportunity("opportunity-control", confidence=0.72)
        feedback = [
            AgentFeedback.create(
                id="feedback-1",
                user_niche_id="devtools",
                opportunity_id="opportunity-saved",
                action="save",
            )
        ]

        ranked = rank_opportunities_with_feedback([control, saved], feedback)

        self.assertEqual(ranked[0].id, "opportunity-saved")

    def test_evaluates_labeled_agent_behavior_fixture(self):
        examples = load_labeled_agent_ranking_examples(
            Path("tests/fixtures/agent_behavior_eval.json")
        )

        report = evaluate_agent_ranker(
            rank_opportunities_with_feedback,
            examples,
        )

        self.assertEqual(report.total, 2)
        self.assertEqual(report.top_match_count, 2)
        self.assertEqual(report.mistakes, [])

    def test_cli_fixture_loader_rejects_non_array_payload(self):
        with self.assertRaises(FileNotFoundError):
            load_labeled_agent_ranking_examples("missing-agent-eval.json")

    @staticmethod
    def _opportunity(opportunity_id: str, *, confidence: float) -> Opportunity:
        return Opportunity.create(
            id=opportunity_id,
            cluster_id=f"cluster-{opportunity_id}",
            title=f"{opportunity_id} title",
            target_user="product teams",
            pain_summary="A repeated pain exists.",
            why_it_matters="It blocks a workflow.",
            suggested_wedge="Build a focused workflow.",
            evidence_count=1,
            confidence=confidence,
            evidence_signal_ids=[f"signal-{opportunity_id}"],
        )


if __name__ == "__main__":
    unittest.main()
