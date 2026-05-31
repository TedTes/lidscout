import unittest

from application.agent import build_agent_memory_summary
from domain.agent import AgentFeedback, AgentPreferences
from domain.niche import NicheSource, UserNiche


class AgentMemorySummaryTests(unittest.TestCase):
    def test_summarizes_preferences_feedback_and_source_health(self):
        user_niche = UserNiche.create(
            id="devtools",
            user_id="user-1",
            job="Developer tools",
            buyer="developers",
            category="tools",
        )
        source = NicheSource.create(
            id="source-1",
            niche_id="devtools",
            locator="https://example.com/issues",
            source_type="github_issues",
            source_family="technical_forum",
            is_gate_free=True,
            health_status="active",
        )

        summary = build_agent_memory_summary(
            user_niche=user_niche,
            preferences=AgentPreferences.create(
                user_niche_id="devtools",
                preferred_source_families=["technical_forum"],
                ignored_themes=["pricing"],
                extra_instructions="Prioritize developer workflow pain.",
            ),
            feedback=[
                AgentFeedback.create(
                    user_niche_id="devtools",
                    opportunity_id="opportunity-1",
                    action="save",
                ),
                AgentFeedback.create(
                    user_niche_id="devtools",
                    opportunity_id="opportunity-2",
                    action="dismiss",
                ),
            ],
            sources=[source],
        )

        self.assertEqual(summary.market_id, "devtools")
        self.assertIn("Developer tools", summary.headline)
        self.assertIn("Prioritize technical_forum sources.", summary.learned_preferences)
        self.assertIn("Avoid themes: pricing.", summary.learned_preferences)
        self.assertIn("1 monitored source(s), 1 recently healthy.", summary.source_notes)
        self.assertIn("1 saved gap(s), 1 dismissed gap(s).", summary.feedback_notes)


if __name__ == "__main__":
    unittest.main()
