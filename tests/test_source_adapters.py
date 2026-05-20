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
                )
            )

        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0].id, "web_json:abc123")
        self.assertEqual(posts[1].id, "web_json:c1")
        self.assertEqual(posts[0].title, "Tooling pain")
        self.assertEqual(posts[1].body, "Exports take too much manual work.")
        self.assertEqual(posts[1].metadata["domain"], "example.com")

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
