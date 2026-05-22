import unittest

from application.clustering import ClusteringService
from domain.signal import Signal


class ClusteringServiceTests(unittest.TestCase):
    def test_groups_semantically_similar_signals_by_cosine_threshold(self):
        service = ClusteringService(similarity_threshold=0.9)
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:1",
                pain="Manual reporting is slow",
                urgency="high",
                severity="medium",
                willingness_to_pay=True,
                category="reporting",
                confidence=0.8,
            ),
            Signal.create(
                id="signal-2",
                post_id="hackernews:2",
                pain="Exports take too long to build",
                urgency="medium",
                severity="medium",
                willingness_to_pay=True,
                category="reporting",
                confidence=0.6,
            ),
            Signal.create(
                id="signal-3",
                post_id="reddit:3",
                pain="Billing limits are confusing",
                category="billing",
            ),
        ]

        clusters = service.cluster(
            signals,
            {
                "signal-1": [1.0, 0.0],
                "signal-2": [0.95, 0.05],
                "signal-3": [0.0, 1.0],
            },
        )

        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0].id, "cluster-1")
        self.assertEqual(clusters[0].theme, "reporting")
        self.assertEqual(clusters[0].signal_ids, ["signal-1", "signal-2"])
        self.assertEqual(clusters[0].frequency, 2)
        self.assertEqual(clusters[0].average_score, 7.9)
        self.assertEqual(
            clusters[0].top_examples,
            ["Manual reporting is slow", "Exports take too long to build"],
        )
        self.assertEqual(clusters[1].signal_ids, ["signal-3"])

    def test_rejects_missing_embedding(self):
        service = ClusteringService()
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:1",
                pain="Manual reporting is slow",
            )
        ]

        with self.assertRaises(ValueError):
            service.cluster(signals, {})

    def test_does_not_cluster_signals_across_competitors(self):
        service = ClusteringService(similarity_threshold=0.9)
        signals = [
            Signal.create(
                id="signal-1",
                post_id="reddit:1",
                pain="Calendar sync is broken",
                category="calendar",
                competitor_id="notion",
            ),
            Signal.create(
                id="signal-2",
                post_id="reddit:2",
                pain="Calendar sync is broken",
                category="calendar",
                competitor_id="linear",
            ),
        ]

        clusters = service.cluster(
            signals,
            {
                "signal-1": [1.0, 0.0],
                "signal-2": [1.0, 0.0],
            },
        )

        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0].signal_ids, ["signal-1"])
        self.assertEqual(clusters[1].signal_ids, ["signal-2"])

    def test_rejects_mismatched_embedding_dimensions(self):
        service = ClusteringService()
        signals = [
            Signal.create(id="signal-1", post_id="reddit:1", pain="One"),
            Signal.create(id="signal-2", post_id="reddit:2", pain="Two"),
        ]

        with self.assertRaises(ValueError):
            service.cluster(
                signals,
                {
                    "signal-1": [1.0, 0.0],
                    "signal-2": [1.0, 0.0, 0.0],
                },
            )


if __name__ == "__main__":
    unittest.main()
