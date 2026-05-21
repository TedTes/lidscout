import unittest

from application.opportunity import OpportunitySynthesisService
from domain.cluster import SignalCluster
from domain.signal import Signal
from infrastructure.db import InMemoryOpportunityRepository


class OpportunitySynthesisServiceTests(unittest.TestCase):
    def test_synthesizes_and_persists_opportunities_from_high_score_clusters(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
        )
        signal = Signal.create(
            id="signal-1",
            post_id="post-1",
            pain="Reporting setup takes too long.",
            user_type="finance teams",
            job_to_be_done="close month-end reporting",
            current_workaround="exporting spreadsheets",
            urgency="high",
            severity="high",
            willingness_to_pay=True,
            category="Reporting",
            confidence=0.9,
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Teams struggle to configure useful reports.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=8.4,
            top_examples=["Reporting setup takes too long."],
        )

        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 1)
        self.assertEqual(result.inserted_count, 1)
        self.assertEqual(result.failed_count, 0)
        opportunity = result.opportunities[0]
        self.assertEqual(opportunity.id, "opportunity-cluster-1")
        self.assertEqual(opportunity.cluster_id, "cluster-1")
        self.assertEqual(
            opportunity.title,
            "Reduce reporting friction for finance teams",
        )
        self.assertEqual(opportunity.target_user, "finance teams")
        self.assertIn("average opportunity score of 8.4", opportunity.why_it_matters)
        self.assertIn("exporting spreadsheets", opportunity.suggested_wedge)
        self.assertEqual(opportunity.evidence_count, 1)
        self.assertEqual(opportunity.evidence_signal_ids, ["signal-1"])
        self.assertEqual(repository.get_opportunity("opportunity-cluster-1"), opportunity)

    def test_skips_clusters_below_score_threshold(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=7.0,
        )
        signal = Signal.create(
            id="signal-1",
            post_id="post-1",
            pain="Minor reporting annoyance.",
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Minor reporting annoyance.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=4.0,
        )

        result = service.synthesize([cluster], [signal])

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.inserted_count, 0)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(repository.list_opportunities(), [])

    def test_counts_cluster_without_matching_signal_as_failed(self):
        repository = InMemoryOpportunityRepository()
        service = OpportunitySynthesisService(
            repository,
            minimum_average_score=0.0,
        )
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="Reporting",
            summary="Teams struggle to configure useful reports.",
            signal_ids=["missing-signal"],
            frequency=1,
            average_score=8.4,
        )

        result = service.synthesize([cluster], [])

        self.assertEqual(result.synthesized_count, 0)
        self.assertEqual(result.inserted_count, 0)
        self.assertEqual(result.failed_count, 1)


if __name__ == "__main__":
    unittest.main()
