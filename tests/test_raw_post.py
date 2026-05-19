from datetime import UTC, datetime
import unittest

from adapters.hackernews.client import HackerNewsActivityAdapter
from adapters.reddit.client import RedditActivityAdapter
from domain.post import RawPost


class RawPostTests(unittest.TestCase):
    def test_creates_stable_internal_id_and_normalizes_timestamp(self):
        post = RawPost.create(
            source=" Reddit ",
            source_id=" abc123 ",
            title="  Pricing thread ",
            body="  Too expensive for small teams. ",
            author=" jane ",
            url=" https://reddit.com/r/test/comments/abc123 ",
            created_at=1_700_000_000,
            upvotes=42,
            comments_count=7,
            metadata={"subreddit": "test"},
        )

        self.assertEqual(post.id, "reddit:abc123")
        self.assertEqual(post.source, "reddit")
        self.assertEqual(post.source_id, "abc123")
        self.assertEqual(post.title, "Pricing thread")
        self.assertEqual(post.body, "Too expensive for small teams.")
        self.assertEqual(post.author, "jane")
        self.assertEqual(post.created_at, datetime.fromtimestamp(1_700_000_000, tz=UTC))
        self.assertEqual(post.upvotes, 42)
        self.assertEqual(post.comments_count, 7)

    def test_normalizes_reddit_source_data(self):
        post = RedditActivityAdapter()._normalize_post(
            {
                "id": "r1",
                "title": "CRM alternatives",
                "selftext": "The setup is confusing and support is slow.",
                "author": "founder42",
                "permalink": "/r/startups/comments/r1/crm_alternatives/",
                "created_utc": 1_700_000_100,
                "score": 12,
                "num_comments": 5,
                "subreddit": "startups",
                "post_hint": "self",
            }
        )

        self.assertEqual(post.id, "reddit:r1")
        self.assertEqual(post.source, "reddit")
        self.assertEqual(post.source_id, "r1")
        self.assertEqual(post.body, "The setup is confusing and support is slow.")
        self.assertEqual(post.url, "https://www.reddit.com/r/startups/comments/r1/crm_alternatives/")
        self.assertEqual(post.upvotes, 12)
        self.assertEqual(post.comments_count, 5)
        self.assertEqual(post.metadata["subreddit"], "startups")

    def test_normalizes_hackernews_source_data(self):
        post = HackerNewsActivityAdapter()._normalize_item(
            {
                "id": 123,
                "type": "story",
                "by": "pg",
                "time": 1_700_000_200,
                "title": "Ask HN: What reporting tools are painful?",
                "text": "Exports are limited and dashboards are slow.",
                "score": 31,
                "descendants": 14,
                "kids": [124, 125],
            }
        )

        self.assertEqual(post.id, "hackernews:123")
        self.assertEqual(post.source, "hackernews")
        self.assertEqual(post.source_id, "123")
        self.assertEqual(post.author, "pg")
        self.assertEqual(post.url, "https://news.ycombinator.com/item?id=123")
        self.assertEqual(post.upvotes, 31)
        self.assertEqual(post.comments_count, 14)
        self.assertEqual(post.metadata["kids"], [124, 125])


if __name__ == "__main__":
    unittest.main()
