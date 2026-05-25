import unittest

from application.agent import AgentColdStartService
from application.source_suggestions import SourceSuggestionService
from domain.competitor import Competitor
from domain.market import Market
from domain.source import MonitoredSource


class AgentColdStartServiceTests(unittest.TestCase):
    def test_returns_setup_actions_for_empty_niche(self):
        market = Market.create(id="devtools", name="Developer tools")
        suggestions = SourceSuggestionService().suggest_for_market(market)

        plan = AgentColdStartService().build_plan(
            market=market,
            competitors=[],
            monitored_sources=[],
            source_suggestions=suggestions,
        )

        self.assertEqual(plan.status, "setup_needed")
        self.assertEqual(plan.brief.market_id, "devtools")
        self.assertEqual(plan.brief.target_user, "product teams and founders evaluating this niche")
        self.assertIn("refine_research_brief", plan.next_actions)
        self.assertIn("add_companies", plan.next_actions)
        self.assertIn("add_sources", plan.next_actions)
        self.assertGreater(plan.suggested_source_count, 0)
        self.assertIn("social", plan.brief.source_family_priorities)

    def test_marks_configured_niche_ready_for_first_scan(self):
        market = Market.create(
            id="devtools",
            name="Developer tools",
            target_user="developer tool PMs",
            idea_prompt="Find unmet devtool workflow needs.",
        )
        competitor = Competitor.create(
            id="supabase",
            name="Supabase",
            market_id="devtools",
        )
        source = MonitoredSource.create(
            market_id="devtools",
            locator="https://hn.algolia.com/api/v1/search_by_date?query=Supabase",
            source_type="hackernews_search",
        )

        plan = AgentColdStartService().build_plan(
            market=market,
            competitors=[competitor],
            monitored_sources=[source],
            source_suggestions=[],
        )

        self.assertEqual(plan.status, "ready_for_scan")
        self.assertEqual(plan.next_actions, ["run_first_scan"])
        self.assertEqual(plan.active_source_count, 1)


if __name__ == "__main__":
    unittest.main()
