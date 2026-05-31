from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from domain.agent import AgentActivity, AgentFeedback, AgentPreferences
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.market import Market
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import SourceLocator
from infrastructure.db import (
    SQLiteAgentActivityRepository,
    SQLiteAgentFeedbackRepository,
    SQLiteAgentPreferencesRepository,
    SQLiteClusterRepository,
    SQLiteOpportunityRepository,
    SQLitePipelineRunMetricsRepository,
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
            self.assertTrue(repository.delete_signal("signal-1"))
            self.assertIsNone(repository.get_signal("signal-1"))
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
            self.assertTrue(repository.delete_score("signal-1"))
            self.assertIsNone(repository.get_score("signal-1"))
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

    def test_sqlite_opportunity_repository_saves_and_loads_opportunities(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteOpportunityRepository(database_path)
            opportunity = Opportunity.create(
                id="opportunity-1",
                cluster_id="cluster-1",
                title="Reduce reporting setup friction",
                target_user="finance teams",
                pain_summary="Finance teams cannot get useful reports quickly.",
                why_it_matters="The cluster has repeated evidence of reporting pain.",
                suggested_wedge="Ship a focused reporting setup assistant.",
                evidence_count=2,
                confidence=0.82,
                evidence_signal_ids=["signal-1", "signal-2"],
            )

            saved_count = repository.save_opportunities([opportunity, opportunity])
            repository.close()

            repository = SQLiteOpportunityRepository(database_path)
            self.assertEqual(saved_count, 1)
            self.assertEqual(repository.get_opportunity("opportunity-1"), opportunity)
            self.assertEqual(repository.list_opportunities(), [opportunity])
            repository.close()

    @unittest.skip("SQLiteMarketRepository removed — use SQLiteUserNicheRepository")
    def test_sqlite_market_repository_saves_and_loads_markets(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteMarketRepository(database_path)
            market = Market.create(
                id="workspace-tools",
                name="Workspace tools",
                description="Tools for async teams.",
                target_user="product teams",
                idea_prompt="Find workflow gaps in collaboration tools.",
                created_at=datetime(2026, 5, 23, 11, 0, tzinfo=UTC),
            )

            saved_count = repository.save_markets([market, market])
            repository.close()

            repository = SQLiteMarketRepository(database_path)
            self.assertEqual(saved_count, 1)
            self.assertEqual(repository.get_market("workspace-tools"), market)
            self.assertEqual(repository.list_markets(), [market])

            updated = Market.create(
                id="workspace-tools",
                name="Workspace intelligence",
                description=None,
                target_user="founders",
                idea_prompt="Find repeated product gaps.",
                created_at=market.created_at,
            )
            self.assertTrue(repository.update_market(updated))
            self.assertEqual(repository.get_market("workspace-tools"), updated)
            self.assertFalse(
                repository.update_market(
                    Market.create(id="missing", name="Missing")
                )
            )
            self.assertTrue(repository.delete_market("workspace-tools"))
            self.assertIsNone(repository.get_market("workspace-tools"))
            self.assertFalse(repository.delete_market("workspace-tools"))
            repository.close()

    def test_sqlite_agent_preferences_repository_saves_and_loads_preferences(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteAgentPreferencesRepository(database_path)
            preferences = AgentPreferences.create(
                user_niche_id="workspace-tools",
                preferred_source_families=["reviews", "social"],
                ignored_themes=["pricing"],
                created_at=datetime(2026, 5, 25, 16, 0, tzinfo=UTC),
            )

            self.assertTrue(repository.save_agent_preferences(preferences))
            repository.close()

            repository = SQLiteAgentPreferencesRepository(database_path)
            self.assertEqual(
                repository.get_agent_preferences("workspace-tools"),
                preferences,
            )
            updated = AgentPreferences.create(
                user_niche_id="workspace-tools",
                muted_source_ids=["source-1"],
                created_at=preferences.created_at,
            )
            self.assertTrue(repository.save_agent_preferences(updated))
            self.assertEqual(
                repository.get_agent_preferences("workspace-tools"),
                updated,
            )
            self.assertTrue(repository.delete_agent_preferences("workspace-tools"))
            self.assertIsNone(repository.get_agent_preferences("workspace-tools"))
            repository.close()

    def test_sqlite_agent_feedback_repository_saves_and_loads_feedback(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteAgentFeedbackRepository(database_path)
            feedback = AgentFeedback.create(
                id="feedback-1",
                user_niche_id="workspace-tools",
                opportunity_id="opportunity-1",
                action="save",
                created_at=datetime(2026, 5, 25, 16, 10, tzinfo=UTC),
            )

            self.assertTrue(repository.save_agent_feedback(feedback))
            self.assertFalse(repository.save_agent_feedback(feedback))
            repository.close()

            repository = SQLiteAgentFeedbackRepository(database_path)
            self.assertEqual(
                repository.list_agent_feedback(user_niche_id="workspace-tools"),
                [feedback],
            )
            self.assertEqual(
                repository.list_agent_feedback(action="dismiss"),
                [],
            )
            repository.close()

    def test_sqlite_agent_activity_repository_saves_and_loads_activity(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteAgentActivityRepository(database_path)
            activity = AgentActivity.create(
                id="activity-1",
                user_niche_id="workspace-tools",
                event_type="run_completed",
                title="Scan completed",
                metadata={"fetched_count": 12},
                created_at=datetime(2026, 5, 25, 16, 20, tzinfo=UTC),
            )

            self.assertTrue(repository.save_agent_activity(activity))
            self.assertFalse(repository.save_agent_activity(activity))
            repository.close()

            repository = SQLiteAgentActivityRepository(database_path)
            self.assertEqual(
                repository.list_agent_activity(user_niche_id="workspace-tools"),
                [activity],
            )
            self.assertEqual(
                repository.list_agent_activity(event_type="source_failed"),
                [],
            )
            repository.close()

    def test_sqlite_pipeline_run_metrics_repository_saves_and_loads_metrics(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLitePipelineRunMetricsRepository(database_path)
            metrics = self._pipeline_run_metrics()

            self.assertTrue(repository.save_pipeline_run_metrics(metrics))
            self.assertFalse(repository.save_pipeline_run_metrics(metrics))
            repository.close()

            repository = SQLitePipelineRunMetricsRepository(database_path)
            self.assertEqual(repository.list_pipeline_run_metrics(), [metrics])
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

    @unittest.skip("SQLiteNicheCompanyRepository removed — use PostgresNicheCompanyRepository")
    def test_sqlite_competitor_repository_saves_and_loads_competitors(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteNicheCompanyRepository(database_path)
            competitor = Competitor.create(
                id="competitor-1",
                name="Acme CRM",
                website="https://acme.example",
                category="crm",
                market_id="market-1",
            )

            saved_count = repository.save_competitors([competitor, competitor])
            repository.close()

            repository = SQLiteNicheCompanyRepository(database_path)
            self.assertEqual(saved_count, 1)
            self.assertEqual(repository.get_competitor("competitor-1"), competitor)
            self.assertEqual(repository.list_competitors(), [competitor])
            repository.close()

    @unittest.skip("SQLiteNicheSourceRepository removed — MonitoredSource replaced by NicheSource")
    def test_sqlite_monitored_source_repository_saves_and_loads_sources(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteNicheSourceRepository(database_path)
            source = MonitoredSource.create(
                id="source-1",
                competitor_id="competitor-1",
                market_id="market-1",
                locator="https://acme.example/reviews",
                source_type="reviews",
                limit=10,
            )
            disabled_source = MonitoredSource.create(
                id="source-2",
                competitor_id="competitor-2",
                market_id="market-2",
                locator="https://other.example/reviews",
                enabled=False,
            )

            saved_count = repository.save_monitored_sources(
                [source, source, disabled_source]
            )
            repository.close()

            repository = SQLiteNicheSourceRepository(database_path)
            self.assertEqual(saved_count, 2)
            self.assertEqual(repository.get_monitored_source("source-1"), source)
            self.assertEqual(
                repository.list_monitored_sources(competitor_id="competitor-1"),
                [source],
            )
            self.assertEqual(
                repository.list_monitored_sources(market_id="market-1"),
                [source],
            )
            self.assertEqual(
                repository.list_monitored_sources(enabled=False),
                [disabled_source],
            )
            updated_source = MonitoredSource.create(
                id="source-1",
                competitor_id="competitor-1",
                market_id="market-1",
                locator="https://acme.example/reviews",
                source_type="forum",
                enabled=False,
                limit=25,
                options={"section": "support"},
            )
            self.assertTrue(repository.update_monitored_source(updated_source))
            self.assertEqual(
                repository.get_monitored_source("source-1"),
                updated_source,
            )
            repository.close()

    @unittest.skip("SQLiteSourceHealthRepository removed — health tracked on NicheSource")
    def test_sqlite_source_health_repository_saves_and_loads_health(self):
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "lidscout.sqlite"
            repository = SQLiteSourceHealthRepository(database_path)
            scanned_at = datetime(2026, 5, 25, 16, 20, tzinfo=UTC)
            health = SourceHealth.create(
                monitored_source_id="source-1",
                total_runs=1,
                success_count=1,
                posts_fetched_count=5,
                relevant_posts_count=2,
                extracted_signals_count=1,
                opportunity_count=1,
                last_status="healthy",
                last_fetched_count=5,
                last_relevant_count=2,
                last_extracted_count=1,
                last_opportunity_count=1,
                last_scanned_at=scanned_at,
                updated_at=scanned_at,
            )

            self.assertTrue(repository.save_source_health(health))
            repository.close()

            repository = SQLiteSourceHealthRepository(database_path)
            self.assertEqual(repository.get_source_health("source-1"), health)
            self.assertEqual(
                repository.list_source_health(status="healthy"),
                [health],
            )
            updated = health.record_run(
                fetched_count=0,
                relevant_count=0,
                extracted_count=0,
                opportunity_count=0,
                error="Blocked",
                scanned_at=scanned_at,
            )
            self.assertTrue(repository.save_source_health(updated))
            self.assertEqual(repository.get_source_health("source-1"), updated)
            self.assertEqual(
                repository.list_source_health(status="failing"),
                [updated],
            )
            repository.close()

    def _pipeline_run_metrics(self) -> PipelineRunMetrics:
        return PipelineRunMetrics.create(
            id="run-1",
            ran_at=datetime(2026, 5, 22, 13, 0, tzinfo=UTC),
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


if __name__ == "__main__":
    unittest.main()
