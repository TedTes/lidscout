from datetime import UTC, datetime
import json
import unittest

from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import MonitoredSource, SourceLocator
from infrastructure.db import (
    PostgresClusterRepository,
    PostgresCompetitorRepository,
    PostgresMonitoredSourceRepository,
    PostgresPostRepository,
    PostgresScoreRepository,
    PostgresSignalRepository,
    PostgresSourceLocatorRepository,
)


class FakeCursor:
    def __init__(self, *, rowcount: int = 0, row=None, rows=None):
        self.rowcount = rowcount
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursors: list[FakeCursor]):
        self.cursors = cursors
        self.calls: list[tuple[str, tuple]] = []
        self.commit_count = 0
        self.closed = False

    def execute(self, query: str, params: tuple = ()):
        self.calls.append((query, params))
        return self.cursors.pop(0)

    def commit(self):
        self.commit_count += 1

    def close(self):
        self.closed = True


class PostgresRepositoryTests(unittest.TestCase):
    def test_post_repository_saves_and_loads_posts(self):
        created_at = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
        post = RawPost.create(
            source="reddit",
            source_id="abc",
            title="Reporting pain",
            body="Manual reporting is slow.",
            author="founder",
            url="https://reddit.example/post",
            created_at=created_at,
            upvotes=10,
            comments_count=3,
            metadata={"subreddit": "startups"},
        )
        row = {
            "source": "reddit",
            "source_id": "abc",
            "title": "Reporting pain",
            "body": "Manual reporting is slow.",
            "author": "founder",
            "url": "https://reddit.example/post",
            "created_at": created_at,
            "upvotes": 10,
            "comments_count": 3,
            "metadata": {"subreddit": "startups"},
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresPostRepository(connection=connection)

        self.assertEqual(repository.save_posts([post]), 1)
        self.assertEqual(repository.get_post("reddit:abc"), post)
        self.assertEqual(repository.list_posts(), [post])
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "reddit:abc")
        self.assertEqual(json.loads(connection.calls[0][1][-1]), {"subreddit": "startups"})
        self.assertEqual(connection.commit_count, 1)

    def test_signal_repository_saves_and_loads_signals(self):
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
        row = {
            "id": "signal-1",
            "post_id": "reddit:abc",
            "pain": "Manual reporting is slow",
            "user_type": "founder",
            "job_to_be_done": "understand revenue",
            "current_workaround": "spreadsheets",
            "urgency": "high",
            "severity": "medium",
            "willingness_to_pay": True,
            "category": "reporting",
            "confidence": 0.8,
        }
        connection = FakeConnection([FakeCursor(rowcount=1), FakeCursor(row=row)])
        repository = PostgresSignalRepository(connection=connection)

        self.assertEqual(repository.save_signals([signal]), 1)
        self.assertEqual(repository.get_signal("signal-1"), signal)
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.commit_count, 1)

    def test_score_repository_saves_and_loads_scores(self):
        score = OpportunityScore(
            signal_id="signal-1",
            total_score=8.4,
            urgency_score=5.0,
            severity_score=3.0,
            willingness_score=5.0,
            confidence_score=4.0,
            reasoning="high reporting pain",
        )
        row = {
            "signal_id": "signal-1",
            "total_score": 8.4,
            "urgency_score": 5.0,
            "severity_score": 3.0,
            "willingness_score": 5.0,
            "confidence_score": 4.0,
            "reasoning": "high reporting pain",
        }
        connection = FakeConnection([FakeCursor(rowcount=1), FakeCursor(row=row)])
        repository = PostgresScoreRepository(connection=connection)

        self.assertEqual(repository.save_scores([score]), 1)
        self.assertEqual(repository.get_score("signal-1"), score)
        self.assertIn("ON CONFLICT (signal_id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.commit_count, 1)

    def test_cluster_repository_saves_and_loads_clusters(self):
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="reporting",
            summary="Teams need faster reports.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.4,
            top_examples=["Manual reporting is slow."],
        )
        row = {
            "id": "cluster-1",
            "theme": "reporting",
            "summary": "Teams need faster reports.",
            "signal_ids": ["signal-1", "signal-2"],
            "frequency": 2,
            "average_score": 8.4,
            "top_examples": ["Manual reporting is slow."],
        }
        connection = FakeConnection([FakeCursor(rowcount=1), FakeCursor(row=row)])
        repository = PostgresClusterRepository(connection=connection)

        self.assertEqual(repository.save_clusters([cluster]), 1)
        self.assertEqual(repository.get_cluster("cluster-1"), cluster)
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.commit_count, 1)

    def test_source_locator_repository_saves_and_loads_enabled_locators(self):
        locator = SourceLocator.create(
            id="locator-1",
            locator="https://example.com/reviews",
            limit=10,
            options={"section": "reviews"},
        )
        row = {
            "id": "locator-1",
            "locator": "https://example.com/reviews",
            "enabled": True,
            "limit_value": 10,
            "options": {"section": "reviews"},
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresSourceLocatorRepository(connection=connection)

        self.assertEqual(repository.save_source_locators([locator]), 1)
        self.assertEqual(repository.get_source_locator("locator-1"), locator)
        self.assertEqual(repository.list_source_locators(enabled=True), [locator])
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "locator-1")
        self.assertEqual(json.loads(connection.calls[0][1][-1]), {"section": "reviews"})
        self.assertEqual(connection.calls[2][1], (True,))
        self.assertEqual(connection.commit_count, 1)

    def test_competitor_repository_saves_and_loads_competitors(self):
        created_at = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
        competitor = Competitor.create(
            id="competitor-1",
            name="Acme CRM",
            website="https://acme.example",
            category="crm",
            created_at=created_at,
        )
        row = {
            "id": "competitor-1",
            "name": "Acme CRM",
            "website": "https://acme.example",
            "category": "crm",
            "description": None,
            "created_at": created_at,
        }
        connection = FakeConnection([FakeCursor(rowcount=1), FakeCursor(row=row)])
        repository = PostgresCompetitorRepository(connection=connection)

        self.assertEqual(repository.save_competitors([competitor]), 1)
        self.assertEqual(repository.get_competitor("competitor-1"), competitor)
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.commit_count, 1)

    def test_monitored_source_repository_saves_and_loads_enabled_sources(self):
        source = MonitoredSource.create(
            id="source-1",
            competitor_id="competitor-1",
            locator="https://acme.example/reviews",
            source_type="reviews",
            limit=10,
            options={"section": "reviews"},
        )
        row = {
            "id": "source-1",
            "competitor_id": "competitor-1",
            "locator": "https://acme.example/reviews",
            "source_type": "reviews",
            "enabled": True,
            "limit_value": 10,
            "scan_frequency": None,
            "last_scanned_at": None,
            "last_error": None,
            "options": {"section": "reviews"},
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresMonitoredSourceRepository(connection=connection)

        self.assertEqual(repository.save_monitored_sources([source]), 1)
        self.assertEqual(repository.get_monitored_source("source-1"), source)
        self.assertEqual(
            repository.list_monitored_sources(
                competitor_id="competitor-1",
                enabled=True,
            ),
            [source],
        )
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(json.loads(connection.calls[0][1][-1]), {"section": "reviews"})
        self.assertEqual(connection.calls[2][1], ("competitor-1", True))
        updated_source = MonitoredSource.create(
            id="source-1",
            competitor_id="competitor-1",
            locator="https://acme.example/reviews",
            source_type="forum",
            enabled=False,
            limit=25,
            options={"section": "support"},
        )
        self.assertTrue(repository.update_monitored_source(updated_source))
        self.assertIn("UPDATE monitored_sources", connection.calls[3][0])
        self.assertEqual(connection.calls[3][1][0], "forum")
        self.assertEqual(connection.calls[3][1][1], False)
        self.assertEqual(connection.calls[3][1][2], 25)
        self.assertEqual(json.loads(connection.calls[3][1][-2]), {"section": "support"})
        self.assertEqual(connection.calls[3][1][-1], "source-1")
        self.assertEqual(connection.commit_count, 2)


if __name__ == "__main__":
    unittest.main()
