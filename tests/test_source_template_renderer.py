import unittest

from application.source_suggestions import (
    render_source_candidate,
    render_source_candidates,
)
from domain.competitor import Competitor
from domain.market import Market
from domain.source import SourceTemplate


class SourceTemplateRendererTests(unittest.TestCase):
    def test_renders_competitor_source_candidate(self):
        template = SourceTemplate.create(
            id="reddit-search",
            label="{company_name} Reddit",
            source_type="reddit_search",
            url_template="https://www.reddit.com/search.json?q={company_query}",
            source_family="social",
            rationale="Find posts about {company_name}.",
            default_limit=25,
            rank_score=0.8,
            options={"query": "{company_query}", "page_size": 25},
        )
        competitor = Competitor.create(
            id="notion-ai",
            name="Notion AI",
            website="https://www.notion.so/",
            category="productivity",
        )

        candidate = render_source_candidate(template, competitor=competitor)

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(
            candidate.locator,
            "https://www.reddit.com/search.json?q=Notion+AI",
        )
        self.assertEqual(candidate.label, "Notion AI Reddit")
        self.assertEqual(candidate.rationale, "Find posts about Notion AI.")
        self.assertEqual(candidate.options, {"query": "Notion+AI", "page_size": 25})
        self.assertEqual(candidate.template_id, "reddit-search")
        self.assertEqual(candidate.rank_score, 0.8)

    def test_renders_domain_and_slug_variables(self):
        template = SourceTemplate.create(
            id="website-changelog",
            label="{domain} changelog",
            source_type="changelog",
            url_template="{website}/changelog/{company_slug}",
            source_family="owned_site",
            rationale="Track product updates from {domain}.",
        )
        competitor = Competitor.create(
            id="linear",
            name="Linear App",
            website="https://www.linear.app",
        )

        candidate = render_source_candidate(template, competitor=competitor)

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(
            candidate.locator,
            "https://www.linear.app/changelog/linear-app",
        )
        self.assertEqual(candidate.label, "linear.app changelog")
        self.assertEqual(candidate.rationale, "Track product updates from linear.app.")

    def test_renders_market_source_candidate(self):
        template = SourceTemplate.create(
            id="market-hn-search",
            label="{market_name} Hacker News",
            source_type="hackernews_search",
            url_template="https://hn.algolia.com/api/v1/search?query={market_query}",
            source_family="technical_forum",
            rationale="Find discussions in {market_name}.",
            options={"market_slug": "{market_slug}"},
        )
        market = Market.create(id="ai-devtools", name="AI Devtools")

        candidate = render_source_candidate(template, market=market)

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(
            candidate.locator,
            "https://hn.algolia.com/api/v1/search?query=AI+Devtools",
        )
        self.assertEqual(candidate.options, {"market_slug": "ai-devtools"})

    def test_skips_template_when_required_variable_is_missing(self):
        template = SourceTemplate.create(
            id="website",
            label="{domain} website",
            source_type="website",
            url_template="{website}",
            source_family="owned_site",
            rationale="Monitor {domain}.",
        )
        competitor = Competitor.create(id="notion", name="Notion")

        candidate = render_source_candidate(template, competitor=competitor)

        self.assertIsNone(candidate)

    def test_renders_candidates_with_existing_marker_and_deduping(self):
        first = SourceTemplate.create(
            id="reddit-search",
            label="Reddit",
            source_type="reddit_search",
            url_template="https://www.reddit.com/search.json?q={company_query}",
            source_family="social",
            rationale="Find discussions.",
            rank_score=0.8,
        )
        duplicate = SourceTemplate.create(
            id="reddit-search-duplicate",
            label="Reddit duplicate",
            source_type="reddit_search",
            url_template="https://www.reddit.com/search.json?q={company_query}",
            source_family="social",
            rationale="Find discussions again.",
            rank_score=0.9,
        )
        competitor = Competitor.create(id="notion", name="Notion")

        candidates = render_source_candidates(
            [first, duplicate],
            competitor=competitor,
            existing_locators={"https://www.reddit.com/search.json?q=Notion/"},
        )

        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0].already_monitored)
        self.assertEqual(candidates[0].template_id, "reddit-search")


if __name__ == "__main__":
    unittest.main()
