from datetime import UTC, datetime
import unittest

from domain.post import RawPost


class RawPostTests(unittest.TestCase):
    def test_creates_stable_internal_id_and_normalizes_timestamp(self):
        post = RawPost.create(
            source=" Web ",
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

        self.assertEqual(post.id, "web:abc123")
        self.assertEqual(post.source, "web")
        self.assertEqual(post.source_id, "abc123")
        self.assertEqual(post.title, "Pricing thread")
        self.assertEqual(post.body, "Too expensive for small teams.")
        self.assertEqual(post.author, "jane")
        self.assertEqual(post.created_at, datetime.fromtimestamp(1_700_000_000, tz=UTC))
        self.assertEqual(post.upvotes, 42)
        self.assertEqual(post.comments_count, 7)


if __name__ == "__main__":
    unittest.main()
