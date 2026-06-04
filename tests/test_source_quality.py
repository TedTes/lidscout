import unittest

from application.source_quality import source_observed_quality_score
from domain.niche import NicheSourceRunStats


class SourceQualityScoringTests(unittest.TestCase):
    def test_scores_unknown_sources_neutrally(self):
        stats = NicheSourceRunStats.create(niche_source_id="source-1")

        self.assertEqual(source_observed_quality_score(stats), 0.5)

    def test_scores_reliable_relevant_sources_higher_than_noisy_sources(self):
        high_quality = NicheSourceRunStats.create(
            niche_source_id="source-1",
            total_runs=4,
            success_count=4,
            posts_fetched_count=40,
            relevant_posts_count=12,
            rule_filtered_count=8,
            llm_filtered_count=0,
            extracted_signals_count=6,
            gap_count=2,
        )
        noisy = NicheSourceRunStats.create(
            niche_source_id="source-2",
            total_runs=4,
            success_count=4,
            posts_fetched_count=40,
            relevant_posts_count=2,
            rule_filtered_count=30,
            llm_filtered_count=8,
        )

        self.assertGreater(
            source_observed_quality_score(high_quality),
            source_observed_quality_score(noisy),
        )

    def test_penalizes_consecutive_fetch_failures(self):
        healthy = NicheSourceRunStats.create(
            niche_source_id="source-1",
            total_runs=4,
            success_count=4,
            posts_fetched_count=8,
            relevant_posts_count=4,
            rule_filtered_count=4,
        )
        failing = NicheSourceRunStats.create(
            niche_source_id="source-2",
            total_runs=4,
            success_count=1,
            failure_count=3,
            consecutive_failures=3,
            relevant_posts_count=4,
            rule_filtered_count=4,
        )

        self.assertLess(
            source_observed_quality_score(failing),
            source_observed_quality_score(healthy),
        )

    def test_sparse_success_does_not_overrate_source(self):
        sparse = NicheSourceRunStats.create(
            niche_source_id="source-1",
            total_runs=1,
            success_count=1,
            posts_fetched_count=1,
            relevant_posts_count=1,
            extracted_signals_count=1,
            gap_count=1,
        )
        established = NicheSourceRunStats.create(
            niche_source_id="source-2",
            total_runs=4,
            success_count=4,
            posts_fetched_count=40,
            relevant_posts_count=12,
            rule_filtered_count=8,
            extracted_signals_count=6,
            gap_count=2,
        )

        self.assertLess(
            source_observed_quality_score(sparse),
            source_observed_quality_score(established),
        )

    def test_repeated_no_yield_source_scores_low(self):
        no_yield = NicheSourceRunStats.create(
            niche_source_id="source-1",
            total_runs=3,
            success_count=3,
            posts_fetched_count=45,
            rule_filtered_count=30,
            llm_filtered_count=15,
        )

        self.assertLess(source_observed_quality_score(no_yield), 0.25)

    def test_repeated_failures_score_very_low(self):
        failing = NicheSourceRunStats.create(
            niche_source_id="source-1",
            total_runs=4,
            success_count=1,
            failure_count=3,
            consecutive_failures=3,
            posts_fetched_count=5,
            relevant_posts_count=1,
            rule_filtered_count=4,
        )

        self.assertLess(source_observed_quality_score(failing), 0.15)


if __name__ == "__main__":
    unittest.main()
