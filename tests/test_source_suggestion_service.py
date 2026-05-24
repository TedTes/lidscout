import unittest

from application.source_suggestions import SourceSuggestionService
from domain.competitor import Competitor
from domain.market import Market
from domain.source import MonitoredSource


class SourceSuggestionServiceTests(unittest.TestCase):
    def test_suggests_default_sources_for_competitor(self):
        competitor = Competitor.create(
            id="notion",
            name="Notion",
            website="https://www.notion.so",
            category="productivity",
        )

        suggestions = SourceSuggestionService().suggest(competitor)

        self.assertEqual(suggestions[0].source_family, "reviews")
        locators = [suggestion.locator for suggestion in suggestions]
        self.assertIn(
            "https://www.reddit.com/search.json?q=Notion&sort=new",
            locators,
        )
        self.assertIn(
            "https://hn.algolia.com/api/v1/search_by_date?query=Notion&tags=story",
            locators,
        )
        self.assertIn("https://www.g2.com/search?query=Notion", locators)
        self.assertIn("https://www.capterra.com/search/?query=Notion", locators)
        self.assertIn("https://www.notion.so/changelog", locators)
        self.assertIn("https://www.notion.so/blog", locators)
        self.assertTrue(all(suggestion.template_id for suggestion in suggestions))
        self.assertTrue(all(suggestion.source_family for suggestion in suggestions))
        self.assertTrue(
            all(suggestion.validation_status == "valid" for suggestion in suggestions)
        )

    def test_filters_category_specific_templates_when_category_is_known(self):
        competitor = Competitor.create(
            id="notion",
            name="Notion",
            category="consumer_app",
        )

        suggestions = SourceSuggestionService().suggest(competitor)
        locators = [suggestion.locator for suggestion in suggestions]

        self.assertIn(
            "https://www.reddit.com/search.json?q=Notion&sort=new",
            locators,
        )
        self.assertNotIn("https://www.g2.com/search?query=Notion", locators)

    def test_suggests_market_level_sources(self):
        market = Market.create(id="ai-devtools", name="AI Devtools")

        suggestions = SourceSuggestionService().suggest_for_market(market)
        locators = [suggestion.locator for suggestion in suggestions]

        self.assertIn(
            "https://www.reddit.com/search.json?q=AI+Devtools&sort=new",
            locators,
        )
        self.assertIn(
            "https://hn.algolia.com/api/v1/search_by_date?query=AI+Devtools&tags=story",
            locators,
        )

    def test_marks_existing_market_sources(self):
        market = Market.create(id="ai-devtools", name="AI Devtools")
        existing_source = MonitoredSource.create(
            market_id="ai-devtools",
            locator="https://www.reddit.com/search.json?q=AI+Devtools&sort=new",
            source_type="reddit_search",
        )

        suggestions = SourceSuggestionService().suggest_for_market(
            market,
            [existing_source],
        )

        existing = next(
            suggestion
            for suggestion in suggestions
            if suggestion.locator == existing_source.locator
        )
        self.assertTrue(existing.already_monitored)

    def test_marks_existing_sources(self):
        competitor = Competitor.create(id="notion", name="Notion")
        existing_source = MonitoredSource.create(
            competitor_id="notion",
            locator="https://www.reddit.com/search.json?q=Notion&sort=new",
            source_type="reddit_search",
        )

        suggestions = SourceSuggestionService().suggest(
            competitor,
            [existing_source],
        )

        existing = next(
            suggestion
            for suggestion in suggestions
            if suggestion.locator == existing_source.locator
        )
        new = next(
            suggestion
            for suggestion in suggestions
            if suggestion.locator == "https://www.g2.com/search?query=Notion"
        )

        self.assertTrue(existing.already_monitored)
        self.assertFalse(new.already_monitored)


if __name__ == "__main__":
    unittest.main()
