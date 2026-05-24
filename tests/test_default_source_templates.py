import unittest

from application.source_suggestions import (
    get_default_source_templates,
    render_source_candidates,
)
from domain.competitor import Competitor
from domain.market import Market


class DefaultSourceTemplateTests(unittest.TestCase):
    def test_default_templates_have_unique_ids(self):
        templates = get_default_source_templates()
        ids = [template.id for template in templates]

        self.assertEqual(len(ids), len(set(ids)))

    def test_default_templates_include_company_and_market_sources(self):
        templates = get_default_source_templates()
        template_ids = {template.id for template in templates}

        self.assertIn("reddit-company-search", template_ids)
        self.assertIn("g2-company-search", template_ids)
        self.assertIn("company-website", template_ids)
        self.assertIn("reddit-market-search", template_ids)

    def test_default_templates_can_render_for_company_or_market(self):
        templates = get_default_source_templates()
        competitor = Competitor.create(
            id="notion",
            name="Notion",
            website="https://www.notion.so",
            category="productivity",
        )
        market = Market.create(id="workspace-tools", name="Workspace Tools")

        company_templates = [
            template
            for template in templates
            if template.id in {"reddit-company-search", "company-website"}
        ]
        market_templates = [
            template
            for template in templates
            if template.id == "reddit-market-search"
        ]
        company_candidates = render_source_candidates(
            company_templates,
            competitor=competitor,
        )
        market_candidates = render_source_candidates(market_templates, market=market)

        self.assertTrue(
            all(
                template.applies_to_any_category([competitor.category or ""])
                for template in company_templates
            )
        )
        self.assertEqual(
            {candidate.locator for candidate in company_candidates},
            {
                "https://www.reddit.com/search.json?q=Notion&sort=new",
                "https://www.notion.so",
            },
        )
        self.assertEqual(
            [candidate.locator for candidate in market_candidates],
            ["https://www.reddit.com/search.json?q=Workspace+Tools&sort=new"],
        )


if __name__ == "__main__":
    unittest.main()
