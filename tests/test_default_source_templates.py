import unittest

from application.source_suggestions import (
    get_default_source_templates,
    render_source_candidates,
)
from application.source_suggestions.default_templates import (
    SUPPORTED_TEMPLATE_CATEGORIES,
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
        self.assertIn("github-company-issues-search", template_ids)
        self.assertNotIn("company-website", template_ids)
        self.assertIn("reddit-market-search", template_ids)

    def test_market_templates_are_explicitly_scoped(self):
        templates = {
            template.id: template
            for template in get_default_source_templates()
        }

        self.assertEqual(templates["reddit-company-search"].scope, "company")
        self.assertEqual(templates["reddit-market-search"].scope, "market")
        self.assertEqual(templates["hackernews-market-search"].scope, "market")

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
            if template.id in {"reddit-company-search", "company-changelog"}
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
                "https://www.notion.so/changelog",
            },
        )
        self.assertEqual(
            [candidate.locator for candidate in market_candidates],
            ["https://www.reddit.com/search.json?q=Workspace+Tools&sort=new"],
        )

    def test_review_templates_use_consistent_categories(self):
        templates = {
            template.id: template
            for template in get_default_source_templates()
        }

        self.assertEqual(
            templates["g2-company-search"].applicable_categories,
            templates["capterra-company-search"].applicable_categories,
        )

    def test_hackernews_market_template_includes_productivity(self):
        templates = {
            template.id: template
            for template in get_default_source_templates()
        }

        self.assertIn(
            "productivity",
            templates["hackernews-market-search"].applicable_categories,
        )

    def test_github_template_renders_for_devtools_competitors(self):
        templates = get_default_source_templates()
        competitor = Competitor.create(
            id="acme-devtool",
            name="Acme Devtool",
            category="devtools",
        )
        github_templates = [
            template
            for template in templates
            if template.id == "github-company-issues-search"
        ]

        candidates = render_source_candidates(
            github_templates,
            competitor=competitor,
        )

        self.assertEqual(
            [candidate.locator for candidate in candidates],
            [
                "https://api.github.com/search/issues"
                "?q=Acme+Devtool+is%3Aissue&sort=updated&order=desc"
            ],
        )
        self.assertEqual(candidates[0].options["adapter"], "json")

    def test_documents_supported_categories_without_consumer_app(self):
        self.assertIn("devtools", SUPPORTED_TEMPLATE_CATEGORIES)
        self.assertIn("vertical_saas", SUPPORTED_TEMPLATE_CATEGORIES)
        self.assertNotIn("consumer_app", SUPPORTED_TEMPLATE_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
