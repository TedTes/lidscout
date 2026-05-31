import unittest
from unittest.mock import Mock, patch

from adapters.web import (
    ApiAdapter,
    BrowserSessionAdapter,
    DocumentAdapter,
    FeedAdapter,
    JsonUrlAdapter,
    RenderedUrlAdapter,
    StaticUrlAdapter,
)
from domain.source import SourceInput


class SourceAdapterTests(unittest.TestCase):
    def test_json_url_normalizes_text_records(self):
        response = Mock()
        response.headers = {"content-type": "application/json"}
        response.raise_for_status.return_value = None
        response.json.return_value = [
            {
                "data": {
                    "children": [
                        {
                            "kind": "t3",
                            "data": {
                                "id": "abc123",
                                "title": "Tooling pain",
                                "selftext": "Dashboards are slow.",
                                "permalink": "/r/startups/comments/abc123/tooling_pain/",
                                "created_utc": 1_700_000_000,
                            },
                        }
                    ]
                }
            },
            {
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "c1",
                                "body": "Exports take too much manual work.",
                                "author": "founder",
                                "permalink": "/r/startups/comments/abc123/comment/c1/",
                                "created_utc": 1_700_000_100,
                                "score": 5,
                                "parent_id": "t3_abc123",
                                "subreddit": "startups",
                            },
                        }
                    ]
                }
            },
        ]

        with patch("adapters.web.client.requests.get", return_value=response):
            adapter = JsonUrlAdapter()
            posts = adapter.fetch_source(
                SourceInput.create(
                    locator="https://example.com/thread.json",
                    limit=10,
                    options={
                        "competitor_id": "notion",
                        "competitor_name": "Notion",
                        "competitor_domain": "notion.so",
                        "market_id": "workspace-tools",
                        "market_name": "Workspace tools",
                        "source_family": "social",
                    },
                )
            )

        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0].id, "web_json:abc123")
        self.assertEqual(posts[1].id, "web_json:c1")
        self.assertEqual(posts[0].title, "Tooling pain")
        self.assertEqual(posts[1].body, "Exports take too much manual work.")
        self.assertEqual(posts[1].metadata["domain"], "example.com")
        self.assertEqual(posts[1].metadata["competitor_id"], "notion")
        self.assertEqual(posts[1].metadata["competitor_name"], "Notion")
        self.assertEqual(posts[1].metadata["competitor_domain"], "notion.so")
        self.assertEqual(posts[1].metadata["market_id"], "workspace-tools")
        self.assertEqual(posts[1].metadata["market_name"], "Workspace tools")
        self.assertEqual(posts[1].metadata["source_family"], "social")

    def test_json_url_extracts_items_at_configured_path(self):
        response = Mock()
        response.headers = {"content-type": "application/json"}
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "hits": [
                {"objectID": "1", "title": "HN story one", "story_text": "Pain with SaaS pricing", "author": "user1", "points": 42, "num_comments": 5, "created_at": "2024-01-01T00:00:00Z"},
                {"objectID": "2", "title": "HN story two", "url": "https://example.com/post", "author": "user2", "points": 10, "num_comments": 1, "created_at": "2024-01-02T00:00:00Z"},
            ],
            "nbHits": 2,
            "page": 0,
        }

        with patch("adapters.web.client.requests.get", return_value=response):
            adapter = JsonUrlAdapter()
            posts = adapter.fetch_source(
                SourceInput.create(
                    locator="https://hn.algolia.com/api/v1/search_by_date?query=example&tags=story",
                    options={"adapter": "json", "items_path": "hits", "market_id": "mkt-1"},
                )
            )

        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0].id, "web_json:1")
        self.assertEqual(posts[0].title, "HN story one")
        self.assertIn("Pain with SaaS pricing", posts[0].body)
        self.assertEqual(posts[1].id, "web_json:2")
        self.assertEqual(posts[1].metadata["market_id"], "mkt-1")

    def test_json_adapter_can_handle_explicit_json_api_source(self):
        adapter = JsonUrlAdapter()
        source = SourceInput.create(
            locator="https://api.github.com/search/issues?q=Linear+is%3Aissue",
            options={"adapter": "json"},
        )

        self.assertTrue(adapter.can_handle(source))

    def test_web_page_url_normalizes_static_page_text(self):
        response = Mock()
        response.headers = {"content-type": "text/html"}
        response.raise_for_status.return_value = None
        response.text = """
        <html>
          <head><title>G2 Reviews</title></head>
          <body>
            <h1>Accounting Tool Reviews</h1>
            <p>Users complain exports are slow.</p>
          </body>
        </html>
        """

        with patch("adapters.web.client.requests.get", return_value=response):
            adapter = StaticUrlAdapter()
            posts = adapter.fetch_source(
                SourceInput.create(
                    locator="https://www.g2.com/products/example/reviews",
                )
            )

        self.assertEqual(posts[0].source, "web")
        self.assertEqual(posts[0].title, "G2 Reviews")
        self.assertIn("Users complain exports are slow.", posts[0].body)
        self.assertEqual(posts[0].metadata["domain"], "www.g2.com")

    def test_placeholder_adapters_are_not_enabled_by_default(self):
        source = SourceInput.create(locator="https://example.com/reviews")

        self.assertFalse(FeedAdapter().can_handle(source))
        self.assertFalse(DocumentAdapter().can_handle(source))
        self.assertFalse(ApiAdapter().can_handle(source))
        self.assertFalse(BrowserSessionAdapter().can_handle(source))

    def test_rendered_adapter_is_option_gated_placeholder(self):
        adapter = RenderedUrlAdapter()
        source = SourceInput.create(
            locator="https://example.com/reviews",
            options={"render": True},
        )

        self.assertTrue(adapter.can_handle(source))
        with self.assertRaises(NotImplementedError):
            adapter.fetch_source(source)


if __name__ == "__main__":
    unittest.main()
