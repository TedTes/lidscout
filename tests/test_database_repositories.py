from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from domain.cluster import SignalCluster
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import SourceLocator
from infrastructure.db import (
    SQLiteClusterRepository,
    SQLitePostRepository,
    SQLiteScoreRepository,
    SQLiteSignalRepository,
    SQLiteSourceLocatorRepository,
)


class DatabaseRepositoryTests(unittest.TestCase):
    def test_sqlite_post_repository_saves_and_loads_posts(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLitePostRepository(database_path)
            post = RawPost.create(
                source="reddit",
                source_id="abc",
                title="Reporting pain",
                body="Manual reporting is slow.",
                author="founder",
                url="https://reddit.example/post",
                created_at=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
                upvotes=10,
                comments_count=3,
                metadata={"subreddit": "startups"},
            )

            saved_count = repository.save_posts([post, post])
            repository.close()

            repository = SQLitePostRepository(database_path)
            self.assertEqual(saved_count, 1)
            self.assertEqual(repository.get_post("reddit:abc"), post)
            self.assertEqual(repository.list_posts(), [post])
            repository.close()

    def test_sqlite_signal_repository_saves_and_loads_signals(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteSignalRepository(database_path)
            signal = Signal.create(
                id="signal-1",
                post_id="reddit:abc",
                pain="Manual reporting is slow",
                user_type="founder",
                job_to_be_done="understand revenue",
                current_workaround="spreadsheets",
                urgency="high",
                severity="medium",
                willingness_to_pay=True,
                category="reporting",
                confidence=0.8,
            )

            saved_count = repository.save_signals([signal, signal])
            repository.close()

            repository = SQLiteSignalRepository(database_path)
            self.assertEqual(saved_count, 1)
            self.assertEqual(repository.get_signal("signal-1"), signal)
            self.assertEqual(repository.list_signals(), [signal])
            repository.close()

    def test_sqlite_score_repository_saves_and_loads_scores(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteScoreRepository(database_path)
            score = OpportunityScore(
                signal_id="signal-1",
                total_score=8.4,
                urgency_score=5.0,
                severity_score=3.0,
                willingness_score=5.0,
                confidence_score=4.0,
                reasoning="high reporting pain",
            )

            saved_count = repository.save_scores([score, score])
            repository.close()

            repository = SQLiteScoreRepository(database_path)
            self.assertEqual(saved_count, 1)
            self.assertEqual(repository.get_score("signal-1"), score)
            self.assertEqual(repository.list_scores(), [score])
            repository.close()

    def test_sqlite_cluster_repository_saves_and_loads_clusters(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteClusterRepository(database_path)
            cluster = SignalCluster.create(
                id="cluster-1",
                theme="reporting",
                summary="Teams need faster reports.",
                signal_ids=["signal-1", "signal-2"],
                frequency=2,
                average_score=8.4,
                top_examples=["Manual reporting is slow."],
            )

            saved_count = repository.save_clusters([cluster, cluster])
            repository.close()

            repository = SQLiteClusterRepository(database_path)
            self.assertEqual(saved_count, 1)
            self.assertEqual(repository.get_cluster("cluster-1"), cluster)
            self.assertEqual(repository.list_clusters(), [cluster])
            repository.close()

    def test_sqlite_source_locator_repository_saves_and_loads_locators(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteSourceLocatorRepository(database_path)
            locator = SourceLocator.create(
                id="locator-1",
                locator="https://example.com/reviews",
                limit=10,
                options={"section": "reviews"},
            )
            disabled_locator = SourceLocator.create(
                id="locator-2",
                locator="https://example.com/old",
                enabled=False,
            )

            saved_count = repository.save_source_locators(
                [locator, locator, disabled_locator]
            )
            repository.close()

            repository = SQLiteSourceLocatorRepository(database_path)
            self.assertEqual(saved_count, 2)
            self.assertEqual(repository.get_source_locator("locator-1"), locator)
            self.assertEqual(repository.list_source_locators(enabled=True), [locator])
            self.assertEqual(
                repository.list_source_locators(enabled=False),
                [disabled_locator],
            )
            repository.close()


if __name__ == "__main__":
    unittest.main()
