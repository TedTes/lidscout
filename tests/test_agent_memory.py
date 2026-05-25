import unittest
from datetime import UTC, datetime

from application.agent import build_agent_memory_summary
from domain.agent import AgentFeedback, AgentPreferences
from domain.market import Market
from domain.source import MonitoredSource, SourceHealth


class AgentMemorySummaryTests(unittest.TestCase):
    def test_summarizes_preferences_feedback_and_source_health(self):
        source = MonitoredSource.create(
            id="source-1",
            market_id="devtools",
            locator="https://example.com/issues",
            source_type="github_issues",
            options={"source_family": "technical_forum"},
        )
        health = SourceHealth.create(monitored_source_id="source-1").record_run(
            fetched_count=12,
            relevant_count=3,
            extracted_count=1,
            opportunity_count=1,
            error=None,
            scanned_at=datetime(2026, 5, 25, tzinfo=UTC),
        )

        summary = build_agent_memory_summary(
            market=Market.create(id="devtools", name="Developer tools"),
            preferences=AgentPreferences.create(
                market_id="devtools",
                preferred_source_families=["technical_forum"],
                ignored_themes=["pricing"],
                extra_instructions="Prioritize developer workflow pain.",
            ),
            feedback=[
                AgentFeedback.create(
                    market_id="devtools",
                    opportunity_id="opportunity-1",
                    action="save",
                ),
                AgentFeedback.create(
                    market_id="devtools",
                    opportunity_id="opportunity-2",
                    action="dismiss",
                ),
            ],
            sources=[source],
            source_health=[health],
        )

        self.assertEqual(summary.market_id, "devtools")
        self.assertIn("Developer tools", summary.headline)
        self.assertIn("Prioritize technical_forum sources.", summary.learned_preferences)
        self.assertIn("Avoid themes: pricing.", summary.learned_preferences)
        self.assertIn("1 monitored source(s), 1 recently healthy.", summary.source_notes)
        self.assertIn("1 saved gap(s), 1 dismissed gap(s).", summary.feedback_notes)


if __name__ == "__main__":
    unittest.main()
