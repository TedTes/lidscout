import unittest

from domain.cluster import SignalCluster


class SignalClusterModelTests(unittest.TestCase):
    def test_creates_valid_signal_cluster(self):
        cluster = SignalCluster.create(
            id=" cluster-1 ",
            theme=" Reporting pain ",
            summary=" Users struggle to build recurring reports. ",
            signal_ids=[" signal-1 ", "signal-2"],
            frequency=2,
            average_score=7.456,
            top_examples=[" Manual reporting is slow. ", " Dashboards are limited. "],
        )

        self.assertEqual(cluster.id, "cluster-1")
        self.assertEqual(cluster.theme, "Reporting pain")
        self.assertEqual(cluster.summary, "Users struggle to build recurring reports.")
        self.assertEqual(cluster.signal_ids, ["signal-1", "signal-2"])
        self.assertEqual(cluster.frequency, 2)
        self.assertEqual(cluster.average_score, 7.46)
        self.assertEqual(
            cluster.top_examples,
            ["Manual reporting is slow.", "Dashboards are limited."],
        )

    def test_rejects_missing_theme(self):
        with self.assertRaises(ValueError):
            SignalCluster.create(
                id="cluster-1",
                theme="",
                summary="Users struggle to build reports.",
                signal_ids=["signal-1"],
                frequency=1,
                average_score=5.0,
            )

    def test_rejects_missing_signal_ids(self):
        with self.assertRaises(ValueError):
            SignalCluster.create(
                id="cluster-1",
                theme="Reporting pain",
                summary="Users struggle to build reports.",
                signal_ids=[],
                frequency=1,
                average_score=5.0,
            )

    def test_rejects_out_of_range_average_score(self):
        with self.assertRaises(ValueError):
            SignalCluster.create(
                id="cluster-1",
                theme="Reporting pain",
                summary="Users struggle to build reports.",
                signal_ids=["signal-1"],
                frequency=1,
                average_score=11.0,
            )


if __name__ == "__main__":
    unittest.main()
