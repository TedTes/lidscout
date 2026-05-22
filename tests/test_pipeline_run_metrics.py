from datetime import UTC, datetime
import unittest

from domain.pipeline import PipelineRunMetrics


class PipelineRunMetricsTests(unittest.TestCase):
    def test_creates_valid_pipeline_run_metrics(self):
        ran_at = datetime(2026, 5, 22, 13, 0, tzinfo=UTC)

        metrics = PipelineRunMetrics.create(
            id="run-1",
            ran_at=ran_at,
            fetched_count=10,
            fetch_failed_count=1,
            rule_filtered_count=2,
            llm_filtered_count=3,
            relevance_failed_count=0,
            extraction_attempted_count=4,
            extracted_count=3,
            no_signal_count=1,
            extraction_failed_count=0,
            signal_inserted_count=3,
            scored_count=3,
            scoring_failed_count=0,
            average_score=7.5,
            embedding_failed_count=0,
            clustered_count=2,
            cluster_inserted_count=2,
            opportunity_synthesized_count=1,
            opportunity_inserted_count=1,
            opportunity_failed_count=0,
            email_sent=True,
        )

        self.assertEqual(metrics.id, "run-1")
        self.assertEqual(metrics.ran_at, ran_at)
        self.assertEqual(metrics.fetched_count, 10)
        self.assertTrue(metrics.email_sent)

    def test_rejects_negative_counts(self):
        with self.assertRaises(ValueError):
            PipelineRunMetrics.create(
                fetched_count=-1,
                fetch_failed_count=0,
                rule_filtered_count=0,
                llm_filtered_count=0,
                relevance_failed_count=0,
                extraction_attempted_count=0,
                extracted_count=0,
                no_signal_count=0,
                extraction_failed_count=0,
                signal_inserted_count=0,
                scored_count=0,
                scoring_failed_count=0,
                average_score=0.0,
                embedding_failed_count=0,
                clustered_count=0,
                cluster_inserted_count=0,
                opportunity_synthesized_count=0,
                opportunity_inserted_count=0,
                opportunity_failed_count=0,
                email_sent=False,
            )


if __name__ == "__main__":
    unittest.main()
