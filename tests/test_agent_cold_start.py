import unittest

from application.agent import AgentColdStartService
from domain.niche import NicheCompany, NicheSource, UserNiche


class AgentColdStartServiceTests(unittest.TestCase):
    def test_returns_setup_guidance_for_empty_niche(self):
        user_niche = UserNiche.create(
            id="market-1",
            user_id="user-1",
            template_niche_id="niche-1",
            job="Build internal tools",
            buyer="operations teams",
            category="devtools",
        )

        plan = AgentColdStartService().build_plan(
            user_niche=user_niche,
            companies=[],
            sources=[],
            source_suggestions=[],
        )

        self.assertEqual(plan.status, "setup_needed")
        self.assertEqual(plan.brief.market_id, "market-1")
        self.assertEqual(plan.brief.niche_name, "Build internal tools")
        self.assertIn("add_companies", plan.next_actions)
        self.assertIn("add_sources", plan.next_actions)
        self.assertEqual(
            plan.source_explanations,
            ["No active sources are configured yet."],
        )
        self.assertIn("Add at least one active source", plan.expected_result_window)
        self.assertIn("Add or enable sources", plan.no_result_guidance[0])

    def test_marks_configured_niche_ready_for_first_scan(self):
        user_niche = UserNiche.create(
            id="market-1",
            user_id="user-1",
            template_niche_id="niche-1",
            job="Build internal tools",
            buyer="operations teams",
            category="devtools",
        )
        company = NicheCompany.create(
            id="company-1",
            niche_id="niche-1",
            name="Retool",
        )
        sources = [
            NicheSource.create(
                id="source-1",
                niche_id="niche-1",
                locator="https://github.com/appsmithorg/appsmith/issues",
                source_type="github_issues",
                source_family="technical_forum",
                is_gate_free=True,
                buyer_voice_verified=True,
            ),
            NicheSource.create(
                id="source-2",
                niche_id="niche-1",
                locator="https://www.g2.com/products/retool/reviews",
                source_type="review_search",
                source_family="reviews",
                is_gate_free=False,
                requires_proxy=True,
            ),
        ]

        plan = AgentColdStartService().build_plan(
            user_niche=user_niche,
            companies=[company],
            sources=sources,
            source_suggestions=[],
        )

        self.assertEqual(plan.status, "ready_for_scan")
        self.assertEqual(plan.next_actions, ["run_first_scan"])
        self.assertEqual(plan.active_source_count, 2)
        self.assertTrue(
            any("Technical forums" in item for item in plan.source_explanations)
        )
        self.assertTrue(
            any("Review sources" in item for item in plan.source_explanations)
        )
        self.assertIn("8-15 minutes", plan.expected_result_window)
        self.assertIn("Check source health", plan.no_result_guidance[0])


if __name__ == "__main__":
    unittest.main()
