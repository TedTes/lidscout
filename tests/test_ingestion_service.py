import unittest

from application.ingestion import IngestionService
from domain.post import RawPost


class FakeRawPostRepository:
    def __init__(self, existing_ids: set[str] | None = None):
        self.existing_ids = existing_ids or set()
        self.saved_posts: list[RawPost] = []

    def save_posts(self, posts: list[RawPost]) -> int:
        inserted = 0
        for post in posts:
            if post.id in self.existing_ids:
                continue
            self.existing_ids.add(post.id)
            self.saved_posts.append(post)
            inserted += 1
        return inserted


class IngestionServiceTests(unittest.TestCase):
    def test_ingests_unique_posts_and_counts_duplicates(self):
        repository = FakeRawPostRepository(existing_ids={"reddit:existing"})
        service = IngestionService(repository)
        posts = [
            RawPost.create(source="reddit", source_id="one", title=" First "),
            RawPost.create(source="reddit", source_id="one", title="Duplicate"),
            RawPost.create(source="reddit", source_id="existing", title="Already stored"),
        ]

        result = service.ingest(posts)

        self.assertEqual(result.received_count, 3)
        self.assertEqual(result.inserted_count, 1)
        self.assertEqual(result.duplicate_count, 2)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(repository.saved_posts[0].title, "First")


if __name__ == "__main__":
    unittest.main()
