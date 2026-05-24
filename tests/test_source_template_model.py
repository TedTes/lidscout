import unittest

from domain.source import SourceCandidate, SourceTemplate


class SourceTemplateModelTests(unittest.TestCase):
    def test_creates_source_template(self):
        template = SourceTemplate.create(
            id=" reddit-search ",
            label=" Reddit search ",
            source_type=" Reddit_Search ",
            url_template=" https://www.reddit.com/search.json?q={company_query} ",
            source_family=" Social ",
            rationale=" Finds recent public discussions. ",
            scope=" market ",
            default_limit=25,
            applicable_categories=[
                "B2B_SaaS",
                " devtools ",
                "b2b_saas",
                "",
            ],
            rank_score=0.8,
            options={"adapter": "json"},
        )

        self.assertEqual(template.id, "reddit-search")
        self.assertEqual(template.label, "Reddit search")
        self.assertEqual(template.source_type, "reddit_search")
        self.assertEqual(
            template.url_template,
            "https://www.reddit.com/search.json?q={company_query}",
        )
        self.assertEqual(template.source_family, "social")
        self.assertEqual(template.rationale, "Finds recent public discussions.")
        self.assertEqual(template.scope, "market")
        self.assertEqual(template.default_limit, 25)
        self.assertEqual(template.applicable_categories, ["b2b_saas", "devtools"])
        self.assertEqual(template.rank_score, 0.8)
        self.assertEqual(template.options, {"adapter": "json"})

    def test_template_without_categories_applies_globally(self):
        template = SourceTemplate.create(
            id="website",
            label="Website",
            source_type="website",
            url_template="{website}",
            source_family="owned_site",
            rationale="Monitor the company website.",
        )

        self.assertTrue(template.applies_to_any_category([]))
        self.assertTrue(template.applies_to_any_category(["consumer_app"]))

    def test_template_matches_any_applicable_category(self):
        template = SourceTemplate.create(
            id="hn-search",
            label="Hacker News search",
            source_type="hackernews_search",
            url_template="https://hn.algolia.com/api/v1/search_by_date?query={company_query}",
            source_family="technical_forum",
            rationale="Find technical discussions.",
            applicable_categories=["devtools", "ai_tools"],
        )

        self.assertTrue(template.applies_to_any_category(["b2b_saas", "devtools"]))
        self.assertFalse(template.applies_to_any_category(["consumer_app"]))

    def test_rejects_invalid_source_template(self):
        with self.assertRaises(ValueError):
            SourceTemplate.create(
                id="template-1",
                label="Reddit",
                source_type="reddit_search",
                url_template=" ",
                source_family="social",
                rationale="Find discussions.",
            )

        with self.assertRaises(ValueError):
            SourceTemplate.create(
                id="template-1",
                label="Reddit",
                source_type="reddit_search",
                url_template="https://example.com",
                source_family="social",
                rationale="Find discussions.",
                default_limit=0,
            )

        with self.assertRaises(ValueError):
            SourceTemplate.create(
                id="template-1",
                label="Reddit",
                source_type="reddit_search",
                url_template="https://example.com",
                source_family="social",
                rationale=" ",
            )

        with self.assertRaises(ValueError):
            SourceTemplate.create(
                id="template-1",
                label="Reddit",
                source_type="reddit_search",
                url_template="https://example.com",
                source_family="social",
                rationale="Find discussions.",
                scope="global",  # type: ignore[arg-type]
            )

    def test_creates_source_candidate(self):
        candidate = SourceCandidate.create(
            locator=" https://www.reddit.com/search.json?q=notion ",
            source_type=" Reddit_Search ",
            label=" Reddit search ",
            rationale=" Finds recent public discussions. ",
            source_family=" Social ",
            competitor_id=" notion ",
            competitor_name=" Notion ",
            market_id=" workspace-tools ",
            market_name=" Workspace tools ",
            limit=25,
            options={"adapter": "json"},
            template_id=" reddit-search ",
            already_monitored=True,
            rank_score=0.75,
            validation_status="valid",
        )

        self.assertEqual(
            candidate.locator,
            "https://www.reddit.com/search.json?q=notion",
        )
        self.assertEqual(candidate.source_type, "reddit_search")
        self.assertEqual(candidate.label, "Reddit search")
        self.assertEqual(candidate.rationale, "Finds recent public discussions.")
        self.assertEqual(candidate.source_family, "social")
        self.assertEqual(candidate.competitor_id, "notion")
        self.assertEqual(candidate.competitor_name, "Notion")
        self.assertEqual(candidate.market_id, "workspace-tools")
        self.assertEqual(candidate.market_name, "Workspace tools")
        self.assertEqual(candidate.limit, 25)
        self.assertEqual(candidate.options, {"adapter": "json"})
        self.assertEqual(candidate.template_id, "reddit-search")
        self.assertTrue(candidate.already_monitored)
        self.assertEqual(candidate.rank_score, 0.75)
        self.assertEqual(candidate.validation_status, "valid")

    def test_rejects_invalid_source_candidate(self):
        with self.assertRaises(ValueError):
            SourceCandidate.create(
                locator=" ",
                source_type="reddit_search",
                label="Reddit",
                rationale="Find discussions.",
                source_family="social",
            )

        with self.assertRaises(ValueError):
            SourceCandidate.create(
                locator="https://example.com",
                source_type="reddit_search",
                label="Reddit",
                rationale="Find discussions.",
                source_family="social",
                validation_status="maybe",
            )


if __name__ == "__main__":
    unittest.main()
