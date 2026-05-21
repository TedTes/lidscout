from datetime import UTC, datetime
import unittest

from application.reporting import MarketSignalReport, ReportingService
from domain.cluster import SignalCluster
from domain.opportunity import Opportunity


class ReportingServiceTests(unittest.TestCase):
    def test_ranks_clusters_and_generates_report(self):
        clusters = [
            self._cluster(
                id="cluster-1",
                theme="billing",
                summary="Users are confused by billing limits.",
                frequency=5,
                average_score=6.5,
            ),
            self._cluster(
                id="cluster-2",
                theme="reporting",
                summary="Teams need faster recurring reports.",
                frequency=3,
                average_score=8.4,
            ),
            self._cluster(
                id="cluster-3",
                theme="setup",
                summary="Setup takes too long for small teams.",
                frequency=6,
                average_score=8.4,
            ),
        ]
        service = ReportingService(top_cluster_limit=2, opportunity_threshold=8.0)

        opportunities = [
            self._opportunity(
                id="opportunity-1",
                cluster_id="cluster-2",
                title="Improve recurring reports",
                evidence_count=3,
                confidence=0.84,
            ),
            self._opportunity(
                id="opportunity-2",
                cluster_id="cluster-3",
                title="Simplify setup",
                evidence_count=6,
                confidence=0.88,
            ),
        ]

        report = service.generate(clusters, opportunities)

        self.assertIsInstance(report, MarketSignalReport)
        self.assertEqual(report.title, "LidScout Market Signal Report")
        self.assertIsInstance(report.generated_at, datetime)
        self.assertEqual(report.generated_at.tzinfo, UTC)
        self.assertEqual([cluster.id for cluster in report.top_clusters], ["cluster-3", "cluster-2"])
        self.assertEqual(
            report.emerging_pains,
            [
                "Setup takes too long for small teams.",
                "Teams need faster recurring reports.",
            ],
        )
        self.assertEqual(
            [opportunity.id for opportunity in report.recommended_opportunities],
            ["opportunity-2", "opportunity-1"],
        )

    def test_generates_empty_report_for_no_clusters(self):
        report = ReportingService().generate([])

        self.assertEqual(report.top_clusters, [])
        self.assertEqual(report.emerging_pains, [])
        self.assertEqual(report.recommended_opportunities, [])

    def test_rejects_invalid_limits(self):
        with self.assertRaises(ValueError):
            ReportingService(top_cluster_limit=0)

        with self.assertRaises(ValueError):
            ReportingService(opportunity_threshold=11.0)

    @staticmethod
    def _cluster(
        *,
        id: str,
        theme: str,
        summary: str,
        frequency: int,
        average_score: float,
    ) -> SignalCluster:
        return SignalCluster.create(
            id=id,
            theme=theme,
            summary=summary,
            signal_ids=[f"{id}-signal"],
            frequency=frequency,
            average_score=average_score,
            top_examples=[summary],
        )

    @staticmethod
    def _opportunity(
        *,
        id: str,
        cluster_id: str,
        title: str,
        evidence_count: int,
        confidence: float,
    ) -> Opportunity:
        return Opportunity.create(
            id=id,
            cluster_id=cluster_id,
            title=title,
            target_user="product teams",
            pain_summary="Users need better workflows.",
            why_it_matters="Repeated evidence with strong scores.",
            suggested_wedge="Build a focused workflow.",
            evidence_count=evidence_count,
            confidence=confidence,
            evidence_signal_ids=[f"{cluster_id}-signal"],
        )


if __name__ == "__main__":
    unittest.main()
