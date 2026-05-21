from datetime import UTC, datetime
import logging
import unittest

from application.clustering import ClusteringService
from application.ingestion import IngestionService
from application.reporting import MarketSignalReport
from application.scoring import ScoringService
from domain.cluster import SignalCluster
from domain.opportunity import Opportunity
from domain.post import RawPost
from domain.signal import Signal
from infrastructure.db import InMemoryPostRepository, InMemoryScoreRepository
from infrastructure.email import EmailClient, EmailNotifier
from infrastructure.llm import MockLLMClient
from application.extraction import ExtractionService
from shared.errors import ExtractionError
from shared.logger import get_logger, log_event


class FakeEmailNotifier(EmailNotifier):
    def send_report(self, subject: str, body: str, recipients: list[str]) -> None:
        return None


class LoggingTests(unittest.TestCase):
    def test_log_event_writes_structured_json(self):
        logger = get_logger("tests.structured")

        with self.assertLogs(logger, level="INFO") as captured:
            log_event(logger, "custom_event", count=2)

        self.assertIn('"event": "custom_event"', captured.output[0])
        self.assertIn('"count": 2', captured.output[0])

    def test_requested_application_events_are_logged(self):
        post = RawPost.create(source="reddit", source_id="abc", title="Reporting pain")
        signal = Signal.create(
            id="signal-1",
            post_id=post.id,
            pain="Manual reporting is slow",
            urgency="high",
            severity="medium",
            willingness_to_pay=True,
            category="reporting",
            confidence=0.8,
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="reporting",
            summary="Teams need faster reports.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=8.6,
        )
        report = MarketSignalReport(
            title="Daily report",
            generated_at=datetime(2026, 5, 20, tzinfo=UTC),
            top_clusters=[cluster],
            emerging_pains=[cluster.summary],
            recommended_opportunities=[
                Opportunity.create(
                    id="opportunity-1",
                    cluster_id="cluster-1",
                    title="Improve recurring reports",
                    target_user="finance teams",
                    pain_summary=cluster.summary,
                    why_it_matters="Repeated evidence with strong scores.",
                    suggested_wedge="Build a reporting setup assistant.",
                    evidence_count=1,
                    confidence=0.84,
                    evidence_signal_ids=["signal-1"],
                )
            ],
        )

        with self.assertLogs(level="INFO") as captured:
            IngestionService(InMemoryPostRepository()).ingest([post])

            with self.assertRaises(ExtractionError):
                ExtractionService(MockLLMClient("not json")).extract(post)

            ScoringService(InMemoryScoreRepository()).score([signal])
            ClusteringService().cluster([signal], {"signal-1": [1.0, 0.0]})
            EmailClient(FakeEmailNotifier()).send_report(report, "founder@example.com")

        output = "\n".join(captured.output)
        self.assertIn('"event": "ingestion_started"', output)
        self.assertIn('"event": "ingestion_completed"', output)
        self.assertIn('"event": "extraction_failed"', output)
        self.assertIn('"event": "scoring_completed"', output)
        self.assertIn('"event": "clustering_completed"', output)
        self.assertIn('"event": "report_sent"', output)


if __name__ == "__main__":
    unittest.main()
