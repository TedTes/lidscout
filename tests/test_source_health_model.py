import unittest
from datetime import UTC, datetime

from domain.source import SourceHealth


class SourceHealthModelTests(unittest.TestCase):
    def test_records_successful_run(self):
        scanned_at = datetime(2026, 5, 25, 16, 30, tzinfo=UTC)
        health = SourceHealth.create(monitored_source_id="source-1")

        updated = health.record_run(
            fetched_count=10,
            relevant_count=4,
            extracted_count=2,
            opportunity_count=1,
            error=None,
            scanned_at=scanned_at,
        )

        self.assertEqual(updated.total_runs, 1)
        self.assertEqual(updated.success_count, 1)
        self.assertEqual(updated.failure_count, 0)
        self.assertEqual(updated.last_status, "healthy")
        self.assertEqual(updated.fetch_success_rate, 1.0)
        self.assertEqual(updated.relevance_yield_rate, 0.4)
        self.assertEqual(updated.signal_yield_rate, 0.2)

    def test_records_failed_run(self):
        scanned_at = datetime(2026, 5, 25, 16, 30, tzinfo=UTC)
        health = SourceHealth.create(monitored_source_id="source-1")

        updated = health.record_run(
            fetched_count=0,
            relevant_count=0,
            extracted_count=0,
            opportunity_count=0,
            error="403 Forbidden",
            scanned_at=scanned_at,
        )

        self.assertEqual(updated.failure_count, 1)
        self.assertEqual(updated.consecutive_failures, 1)
        self.assertEqual(updated.last_status, "failing")
        self.assertEqual(updated.last_error, "403 Forbidden")

    def test_rejects_negative_counts(self):
        with self.assertRaises(ValueError):
            SourceHealth.create(monitored_source_id="source-1", total_runs=-1)


if __name__ == "__main__":
    unittest.main()
