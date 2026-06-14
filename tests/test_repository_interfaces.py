import unittest

from domain.agent import (
    AgentActivity,
    AgentFeedback,
    AgentFollowUp,
    AgentPreferences,
)
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.market import Market
from domain.niche import (
    TemplateSourceBinding,
    UserSource,
    UserSourcePreference,
    UserSourceRunStats,
)
from domain.opportunity import Opportunity
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import Source, SourceLocator
from infrastructure.db import (
    InMemoryAgentActivityRepository,
    InMemoryAgentFeedbackRepository,
    InMemoryAgentFollowUpRepository,
    InMemoryAgentPreferencesRepository,
    InMemoryClusterRepository,
    InMemoryNicheCompanyRepository,
    InMemoryOpportunityRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemorySourceRepository,
    InMemorySourceLocatorRepository,
    InMemoryTemplateSourceBindingRepository,
    InMemoryUserSourceRepository,
    InMemoryUserSourcePreferenceRepository,
    InMemoryUserSourceRunStatsRepository,
)


class RepositoryInterfaceTests(unittest.TestCase):
    def test_post_repository_persists_unique_posts(self):
        repository = InMemoryPostRepository()
        post = RawPost.create(source="reddit", source_id="abc", title="Reporting pain")

        saved_count = repository.save_posts([post, post])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.posts["reddit:abc"], post)
        self.assertEqual(repository.get_post("reddit:abc"), post)
        self.assertEqual(repository.list_posts(), [post])

    def test_signal_repository_persists_unique_signals(self):
        repository = InMemorySignalRepository()
        signal = Signal.create(
            id="signal-1",
            post_id="reddit:abc",
            pain="Manual reporting is slow",
        )

        saved_count = repository.save_signals([signal, signal])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.signals["signal-1"], signal)
        self.assertEqual(repository.get_signal("signal-1"), signal)
        self.assertEqual(repository.list_signals(), [signal])
        self.assertTrue(repository.delete_signal("signal-1"))
        self.assertIsNone(repository.get_signal("signal-1"))

    def test_score_repository_persists_unique_scores(self):
        repository = InMemoryScoreRepository()
        score = OpportunityScore(
            signal_id="signal-1",
            total_score=8.0,
            urgency_score=5.0,
            severity_score=3.0,
            willingness_score=5.0,
            confidence_score=4.0,
            reasoning="test",
        )

        saved_count = repository.save_scores([score, score])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.scores["signal-1"], score)
        self.assertEqual(repository.get_score("signal-1"), score)
        self.assertEqual(repository.list_scores(), [score])
        self.assertTrue(repository.delete_score("signal-1"))
        self.assertIsNone(repository.get_score("signal-1"))

    def test_cluster_repository_persists_unique_clusters(self):
        repository = InMemoryClusterRepository()
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="reporting",
            summary="Teams need faster reporting.",
            signal_ids=["signal-1"],
            frequency=1,
            average_score=8.0,
        )

        saved_count = repository.save_clusters([cluster, cluster])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.clusters["cluster-1"], cluster)
        self.assertEqual(repository.get_cluster("cluster-1"), cluster)
        self.assertEqual(repository.list_clusters(), [cluster])

    def test_opportunity_repository_persists_unique_opportunities(self):
        repository = InMemoryOpportunityRepository()
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

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.opportunities["opportunity-1"], opportunity)
        self.assertEqual(repository.get_opportunity("opportunity-1"), opportunity)
        self.assertEqual(repository.list_opportunities(), [opportunity])

    @unittest.skip("InMemoryMarketRepository removed — use InMemoryUserNicheRepository")
    def test_market_repository_persists_unique_markets(self):
        pass

    def test_agent_preferences_repository_persists_preferences(self):
        repository = InMemoryAgentPreferencesRepository()
        preferences = AgentPreferences.create(
            user_niche_id="workspace-tools",
            preferred_source_families=["reviews"],
        )

        self.assertTrue(repository.save_agent_preferences(preferences))
        self.assertEqual(
            repository.get_agent_preferences("workspace-tools"),
            preferences,
        )
        self.assertTrue(repository.delete_agent_preferences("workspace-tools"))
        self.assertIsNone(repository.get_agent_preferences("workspace-tools"))

    def test_agent_feedback_repository_persists_feedback(self):
        repository = InMemoryAgentFeedbackRepository()
        feedback = AgentFeedback.create(
            id="feedback-1",
            user_niche_id="workspace-tools",
            opportunity_id="opportunity-1",
            action="save",
            reason="Useful",
            comment="Track this for roadmap planning.",
        )
        dismissed = AgentFeedback.create(
            id="feedback-2",
            user_niche_id="workspace-tools",
            opportunity_id="opportunity-1",
            action="dismiss",
            reason="Evidence too thin",
            comment="Needs more sources.",
        )

        self.assertTrue(repository.save_agent_feedback(feedback))
        self.assertTrue(repository.save_agent_feedback(dismissed))
        self.assertEqual(
            repository.list_agent_feedback(user_niche_id="workspace-tools"),
            [dismissed],
        )
        self.assertEqual(dismissed.comment, "Needs more sources.")
        self.assertEqual(
            repository.list_agent_feedback(action="save"),
            [],
        )
        self.assertTrue(
            repository.delete_agent_feedback(
                user_niche_id="workspace-tools",
                opportunity_id="opportunity-1",
                action="dismiss",
            )
        )
        self.assertEqual(
            repository.list_agent_feedback(user_niche_id="workspace-tools"),
            [],
        )

    def test_agent_activity_repository_persists_activity(self):
        repository = InMemoryAgentActivityRepository()
        activity = AgentActivity.create(
            id="activity-1",
            user_niche_id="workspace-tools",
            event_type="run_completed",
            title="Scan completed",
            metadata={"fetched_count": 12},
        )

        self.assertTrue(repository.save_agent_activity(activity))
        self.assertFalse(repository.save_agent_activity(activity))
        self.assertEqual(
            repository.list_agent_activity(user_niche_id="workspace-tools"),
            [activity],
        )
        self.assertEqual(
            repository.list_agent_activity(event_type="source_failed"),
            [],
        )

    def test_agent_follow_up_repository_updates_status(self):
        repository = InMemoryAgentFollowUpRepository()
        follow_up = AgentFollowUp.create(
            id="follow-up-1",
            user_niche_id="workspace-tools",
            question="What evidence supports this?",
            metadata={"source": "user"},
        )

        self.assertTrue(repository.save_agent_follow_up(follow_up))
        updated = repository.update_agent_follow_up(
            "follow-up-1",
            status="answered",
            response="The agent found two supporting quotes.",
            metadata={"answered_by": "agent"},
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "answered")
        self.assertEqual(updated.response, "The agent found two supporting quotes.")
        self.assertEqual(updated.metadata["source"], "user")
        self.assertEqual(updated.metadata["answered_by"], "agent")
        self.assertEqual(
            repository.list_agent_follow_ups(status="answered"),
            [updated],
        )

    def test_source_locator_repository_persists_unique_locators(self):
        repository = InMemorySourceLocatorRepository()
        locator = SourceLocator.create(
            id="locator-1",
            locator="https://example.com/reviews",
        )

        saved_count = repository.save_source_locators([locator, locator])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.source_locators["locator-1"], locator)
        self.assertEqual(repository.get_source_locator("locator-1"), locator)
        self.assertEqual(repository.list_source_locators(enabled=True), [locator])

    def test_source_repository_persists_and_filters_canonical_sources(self):
        repository = InMemorySourceRepository()
        source = Source.create(
            id="source-1",
            locator="https://api.github.com/search/issues?q=repo:owner/repo",
            source_type="github_issues_search",
            source_family="technical_forum",
            access_mode="api",
        )
        review_source = Source.create(
            id="source-2",
            locator="https://www.g2.com/search?query=crm",
            source_type="g2",
            source_family="reviews",
            access_mode="proxy_required",
            requires_proxy=True,
        )

        saved_count = repository.save_sources([source, source, review_source])

        self.assertEqual(saved_count, 2)
        self.assertEqual(repository.get_source("source-1"), source)
        self.assertEqual(
            repository.get_source_by_identity(
                "github_issues_search",
                "https://api.github.com/search/issues?q=repo:owner/repo",
            ),
            source,
        )
        self.assertEqual(
            repository.list_sources(source_family="reviews"),
            [review_source],
        )
        self.assertEqual(
            repository.list_sources(source_type="github_issues_search"),
            [source],
        )

    def test_template_source_binding_repository_filters_template_defaults(self):
        repository = InMemoryTemplateSourceBindingRepository()
        enabled = TemplateSourceBinding.create(
            id="binding-1",
            template_niche_id="template-1",
            source_id="source-1",
            default_enabled=True,
        )
        disabled = TemplateSourceBinding.create(
            id="binding-2",
            template_niche_id="template-1",
            source_id="source-2",
            default_enabled=False,
        )
        other_template = TemplateSourceBinding.create(
            id="binding-3",
            template_niche_id="template-2",
            source_id="source-1",
        )

        saved_count = repository.save_template_source_bindings(
            [enabled, disabled, other_template, enabled],
        )

        self.assertEqual(saved_count, 3)
        self.assertEqual(
            repository.list_template_source_bindings("template-1"),
            [enabled, disabled],
        )
        self.assertEqual(
            repository.list_template_source_bindings(
                "template-1",
                default_enabled=True,
            ),
            [enabled],
        )
        self.assertTrue(repository.delete_template_source_binding("binding-2"))
        self.assertEqual(
            repository.list_template_source_bindings("template-1"),
            [enabled],
        )

    def test_user_source_preference_repository_finds_and_deletes_preferences(self):
        repository = InMemoryUserSourcePreferenceRepository()
        preference = UserSourcePreference.create(
            id="preference-1",
            user_niche_id="user-niche-1",
            source_id="source-1",
            enabled=False,
            limit_override=10,
        )
        other_preference = UserSourcePreference.create(
            id="preference-2",
            user_niche_id="user-niche-2",
            source_id="source-1",
            muted=True,
        )

        self.assertTrue(repository.save_user_source_preference(preference))
        self.assertTrue(repository.save_user_source_preference(other_preference))
        self.assertFalse(repository.save_user_source_preference(preference))
        self.assertEqual(
            repository.get_user_source_preference("user-niche-1", "source-1"),
            preference,
        )
        updated_preference = UserSourcePreference.create(
            id="preference-replacement",
            user_niche_id="user-niche-1",
            source_id="source-1",
            enabled=False,
            limit_override=5,
        )
        self.assertFalse(repository.save_user_source_preference(updated_preference))
        saved_preference = repository.get_user_source_preference(
            "user-niche-1",
            "source-1",
        )
        self.assertEqual(saved_preference.id, "preference-1")
        self.assertEqual(saved_preference.limit_override, 5)
        self.assertEqual(
            repository.list_user_source_preferences("user-niche-1"),
            [saved_preference],
        )
        self.assertTrue(repository.delete_user_source_preference("preference-1"))
        self.assertIsNone(
            repository.get_user_source_preference("user-niche-1", "source-1"),
        )

    def test_user_source_repository_upserts_and_filters_sources(self):
        repository = InMemoryUserSourceRepository()
        source = UserSource.create(
            id="user-source-1",
            user_niche_id="user-niche-1",
            source_id="source-1",
            template_source_binding_id="binding-1",
            enabled=True,
            priority=2,
            limit=10,
        )
        muted_source = UserSource.create(
            id="user-source-2",
            user_niche_id="user-niche-1",
            source_id="source-2",
            enabled=True,
            muted=True,
            priority=1,
        )

        self.assertEqual(
            repository.save_user_sources([source, muted_source, source]),
            2,
        )
        self.assertEqual(
            repository.get_user_source("user-niche-1", "source-1"),
            source,
        )
        updated_source = UserSource.create(
            id="user-source-replacement",
            user_niche_id="user-niche-1",
            source_id="source-1",
            enabled=False,
            limit=5,
        )
        self.assertEqual(repository.save_user_sources([updated_source]), 0)
        saved_source = repository.get_user_source("user-niche-1", "source-1")
        self.assertEqual(saved_source.id, "user-source-1")
        self.assertEqual(saved_source.limit, 5)
        self.assertEqual(
            repository.list_user_sources("user-niche-1", include_muted=False),
            [saved_source],
        )
        self.assertEqual(
            repository.list_user_sources("user-niche-1", enabled=True),
            [muted_source],
        )
        self.assertTrue(repository.delete_user_source("user-source-1"))
        self.assertIsNone(repository.get_user_source("user-niche-1", "source-1"))

    def test_user_source_run_stats_repository_persists_stats(self):
        repository = InMemoryUserSourceRunStatsRepository()
        stats = UserSourceRunStats.create(
            user_niche_id="user-niche-1",
            source_id="source-1",
            template_source_binding_id="binding-1",
            total_runs=1,
            success_count=1,
            posts_fetched_count=10,
            relevant_posts_count=3,
            last_status="healthy",
            rejection_breakdown={"wrong_subject": 2},
        )
        other_stats = UserSourceRunStats.create(
            user_niche_id="user-niche-2",
            source_id="source-1",
            total_runs=1,
        )

        self.assertTrue(repository.upsert_user_source_run_stats(stats))
        self.assertTrue(repository.upsert_user_source_run_stats(other_stats))
        self.assertFalse(repository.upsert_user_source_run_stats(stats))
        self.assertEqual(
            repository.get_user_source_run_stats("user-niche-1", "source-1"),
            stats,
        )
        self.assertEqual(
            repository.list_user_source_run_stats("user-niche-1"),
            [stats],
        )
        self.assertEqual(
            repository.list_user_source_run_stats(
                "user-niche-1",
                ["source-1"],
            ),
            [stats],
        )
        self.assertEqual(
            repository.list_user_source_run_stats(
                "user-niche-1",
                ["missing"],
            ),
            [],
        )

    @unittest.skip("InMemoryNicheCompanyRepository API changed — save_competitors replaced by save_niche_companies")
    def test_competitor_repository_persists_unique_competitors(self):
        repository = InMemoryNicheCompanyRepository()
        competitor = Competitor.create(id="competitor-1", name="Acme CRM")

        saved_count = repository.save_competitors([competitor, competitor])

        self.assertEqual(saved_count, 1)
        self.assertEqual(repository.competitors["competitor-1"], competitor)
        self.assertEqual(repository.get_competitor("competitor-1"), competitor)
        self.assertEqual(repository.list_competitors(), [competitor])

    @unittest.skip("InMemorySourceHealthRepository removed — health tracked on NicheSource")
    def test_source_health_repository_persists_snapshots(self):
        pass


if __name__ == "__main__":
    unittest.main()
