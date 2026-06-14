from datetime import UTC, datetime
import json
import unittest
from unittest.mock import patch

from domain.agent import AgentActivity, AgentFeedback, AgentPreferences
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.finding import Finding
from domain.market import Market
from domain.niche import (
    NicheSource,
    NicheSourceRunStats,
    TemplateSourceBinding,
    UserSource,
    UserSourcePreference,
    UserSourceRunStats,
)
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import Source, SourceLocator
from domain.theme import Theme, ThemeFinding
from infrastructure.db import (
    PostgresAgentActivityRepository,
    PostgresAgentFeedbackRepository,
    PostgresAgentPreferencesRepository,
    PostgresClusterRepository,
    PostgresFindingRepository,
    PostgresNicheCompanyRepository,
    PostgresOpportunityRepository,
    PostgresPipelineRunMetricsRepository,
    PostgresPostRepository,
    PostgresScoreRepository,
    PostgresSignalRepository,
    PostgresSourceRepository,
    PostgresSourceLocatorRepository,
    PostgresTemplateSourceBindingRepository,
    PostgresThemeRepository,
    PostgresUserSourceRepository,
    PostgresUserSourcePreferenceRepository,
    PostgresUserSourceRunStatsRepository,
    connect_postgres,
)


class FakeCursor:
    def __init__(self, *, rowcount: int = 0, row=None, rows=None):
        self.rowcount = rowcount
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, cursors: list[FakeCursor]):
        self.cursors = cursors
        self.calls: list[tuple[str, tuple]] = []
        self.commit_count = 0
        self.closed = False

    def execute(self, query: str, params: tuple = ()):
        self.calls.append((query, params))
        return self.cursors.pop(0)

    def commit(self):
        self.commit_count += 1

    def close(self):
        self.closed = True


class PostgresRepositoryTests(unittest.TestCase):
    def test_connect_postgres_uses_autocommit(self):
        with patch("psycopg.connect") as connect:
            connection = connect_postgres("postgresql://postgres.example/lidscout")

        self.assertIs(connection, connect.return_value)
        self.assertTrue(connect.call_args.kwargs["autocommit"])

    def test_post_repository_saves_and_loads_posts(self):
        created_at = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)
        post = RawPost.create(
            source="reddit",
            source_id="abc",
            title="Reporting pain",
            body="Manual reporting is slow.",
            author="founder",
            url="https://reddit.example/post",
            created_at=created_at,
            upvotes=10,
            comments_count=3,
            metadata={"subreddit": "startups"},
        )
        row = {
            "source": "reddit",
            "source_id": "abc",
            "title": "Reporting pain",
            "body": "Manual reporting is slow.",
            "author": "founder",
            "url": "https://reddit.example/post",
            "created_at": created_at,
            "upvotes": 10,
            "comments_count": 3,
            "metadata": {"subreddit": "startups"},
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresPostRepository(connection=connection)

        self.assertEqual(repository.save_posts([post]), 1)
        self.assertEqual(repository.get_post("reddit:abc"), post)
        self.assertEqual(repository.list_posts(), [post])
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "reddit:abc")
        self.assertEqual(json.loads(connection.calls[0][1][-1]), {"subreddit": "startups"})
        self.assertEqual(connection.commit_count, 1)

    def test_signal_repository_saves_and_loads_signals(self):
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
        row = {
            "id": "signal-1",
            "post_id": "reddit:abc",
            "pain": "Manual reporting is slow",
            "user_type": "founder",
            "job_to_be_done": "understand revenue",
            "current_workaround": "spreadsheets",
            "urgency": "high",
            "severity": "medium",
            "willingness_to_pay": True,
            "category": "reporting",
            "confidence": 0.8,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rowcount=1),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresSignalRepository(connection=connection)

        self.assertEqual(repository.save_signals([signal]), 1)
        self.assertEqual(repository.get_signal("signal-1"), signal)
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertTrue(repository.delete_signal("signal-1"))
        self.assertIn("DELETE FROM signal_evidence", connection.calls[2][0])
        self.assertIn("DELETE FROM signals", connection.calls[3][0])
        self.assertEqual(connection.commit_count, 2)

    def test_score_repository_saves_and_loads_scores(self):
        score = OpportunityScore(
            signal_id="signal-1",
            total_score=8.4,
            urgency_score=5.0,
            severity_score=3.0,
            willingness_score=5.0,
            confidence_score=4.0,
            reasoning="high reporting pain",
        )
        row = {
            "signal_id": "signal-1",
            "total_score": 8.4,
            "urgency_score": 5.0,
            "severity_score": 3.0,
            "willingness_score": 5.0,
            "confidence_score": 4.0,
            "reasoning": "high reporting pain",
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresScoreRepository(connection=connection)

        self.assertEqual(repository.save_scores([score]), 1)
        self.assertEqual(repository.get_score("signal-1"), score)
        self.assertIn("ON CONFLICT (signal_id) DO NOTHING", connection.calls[0][0])
        self.assertTrue(repository.delete_score("signal-1"))
        self.assertIn("DELETE FROM scores", connection.calls[2][0])
        self.assertEqual(connection.commit_count, 2)

    def test_cluster_repository_saves_and_loads_clusters(self):
        cluster = SignalCluster.create(
            id="cluster-1",
            theme="reporting",
            summary="Teams need faster reports.",
            signal_ids=["signal-1", "signal-2"],
            frequency=2,
            average_score=8.4,
            top_examples=["Manual reporting is slow."],
        )
        row = {
            "id": "cluster-1",
            "theme": "reporting",
            "summary": "Teams need faster reports.",
            "signal_ids": ["signal-1", "signal-2"],
            "frequency": 2,
            "average_score": 8.4,
            "top_examples": ["Manual reporting is slow."],
        }
        connection = FakeConnection([FakeCursor(rowcount=1), FakeCursor(row=row)])
        repository = PostgresClusterRepository(connection=connection)

        self.assertEqual(repository.save_clusters([cluster]), 1)
        self.assertEqual(repository.get_cluster("cluster-1"), cluster)
        self.assertIn("ON CONFLICT (id) DO UPDATE", connection.calls[0][0])
        self.assertEqual(connection.commit_count, 1)

    def test_opportunity_repository_saves_and_loads_opportunities(self):
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
        row = {
            "id": "opportunity-1",
            "cluster_id": "cluster-1",
            "title": "Reduce reporting setup friction",
            "target_user": "finance teams",
            "pain_summary": "Finance teams cannot get useful reports quickly.",
            "why_it_matters": "The cluster has repeated evidence of reporting pain.",
            "suggested_wedge": "Ship a focused reporting setup assistant.",
            "evidence_count": 2,
            "confidence": 0.82,
            "evidence_signal_ids": ["signal-1", "signal-2"],
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresOpportunityRepository(connection=connection)

        self.assertEqual(repository.save_opportunities([opportunity]), 1)
        self.assertEqual(repository.get_opportunity("opportunity-1"), opportunity)
        self.assertEqual(repository.list_opportunities(), [opportunity])
        self.assertIn("ON CONFLICT (id) DO UPDATE", connection.calls[0][0])
        self.assertEqual(json.loads(connection.calls[0][1][-3]), ["signal-1", "signal-2"])
        self.assertEqual(connection.commit_count, 1)

    def test_finding_repository_saves_and_lists_findings(self):
        extracted_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
        finding = Finding.create(
            id="349d4322-1614-48c1-a7d3-b50b3821a27c",
            user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
            niche_id="7d9fda17-aa22-4d3a-b463-3dd0b2cfd6a4",
            source_id="a815ccce-9fec-4528-8d9f-946c2d42ac29",
            company_id="564f3f05-bcc7-472f-bfeb-44e34aa9657e",
            post_id="hn:123",
            post_title="Incremental schema changes",
            source_url="https://hn.algolia.com/api/v1/search",
            evidence_url="https://news.ycombinator.com/item?id=123",
            evidence_text="Incremental models break on schema changes.",
            pain="dbt incremental models break on schema changes",
            affected_user="analytics engineers",
            job_to_be_done="keep warehouse transforms reliable",
            current_workaround="manual rebuilds",
            category="data reliability",
            urgency="high",
            severity="medium",
            willingness_to_pay=True,
            confidence=0.82,
            detected_at=extracted_at,
            extracted_at=extracted_at,
            pipeline_run_id="run-1",
            structured_embedding_text="dbt incremental models break",
            embedding=[0.1, 0.2],
            metadata={"source_family": "forums"},
        )
        row = {
            "id": finding.id,
            "user_niche_id": finding.user_niche_id,
            "niche_id": finding.niche_id,
            "source_id": finding.source_id,
            "company_id": finding.company_id,
            "post_id": finding.post_id,
            "post_title": finding.post_title,
            "source_url": finding.source_url,
            "evidence_url": finding.evidence_url,
            "evidence_text": finding.evidence_text,
            "pain": finding.pain,
            "affected_user": finding.affected_user,
            "job_to_be_done": finding.job_to_be_done,
            "current_workaround": finding.current_workaround,
            "category": finding.category,
            "urgency": finding.urgency,
            "severity": finding.severity,
            "willingness_to_pay": finding.willingness_to_pay,
            "confidence": finding.confidence,
            "detected_at": finding.detected_at,
            "extracted_at": finding.extracted_at,
            "pipeline_run_id": finding.pipeline_run_id,
            "structured_embedding_text": finding.structured_embedding_text,
            "embedding": "[0.1,0.2]",
            "metadata": finding.metadata,
        }
        connection = FakeConnection([FakeCursor(rowcount=1), FakeCursor(rows=[row])])
        repository = PostgresFindingRepository(connection=connection)

        self.assertEqual(repository.save_findings([finding]), 1)
        self.assertEqual(
            repository.list_findings(user_niche_id=finding.user_niche_id, unassigned_only=True),
            [finding],
        )
        self.assertIn("ON CONFLICT (user_niche_id, post_id) DO UPDATE", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][-2], "[0.1,0.2]")
        self.assertIn("NOT EXISTS", connection.calls[1][0])
        self.assertEqual(connection.commit_count, 1)

    def test_theme_repository_saves_themes_and_assignments(self):
        updated_at = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)
        theme = Theme.create(
            id="c9158d97-9449-4bf2-9ef5-17bb825d522f",
            user_niche_id="8de09fb9-75d0-40d5-b3ea-703ffea6a853",
            niche_id="7d9fda17-aa22-4d3a-b463-3dd0b2cfd6a4",
            title="Schema change reliability",
            summary="Analytics engineers need safer schema changes.",
            finding_count=2,
            source_count=2,
            company_count=1,
            average_confidence=0.76,
            latest_finding_at=updated_at,
            centroid_embedding=[0.4, 0.5],
            created_at=updated_at,
            updated_at=updated_at,
            metadata={"families": ["forums"]},
        )
        assignment = ThemeFinding.create(
            theme_id=theme.id,
            finding_id="349d4322-1614-48c1-a7d3-b50b3821a27c",
            assignment_method="auto_borderline_llm",
            similarity_score=0.77,
            llm_decision={"same_unmet_need": True},
        )
        row = {
            "id": theme.id,
            "user_niche_id": theme.user_niche_id,
            "niche_id": theme.niche_id,
            "title": theme.title,
            "summary": theme.summary,
            "status": theme.status,
            "qualification_reason": theme.qualification_reason,
            "finding_count": theme.finding_count,
            "source_count": theme.source_count,
            "company_count": theme.company_count,
            "average_confidence": theme.average_confidence,
            "latest_finding_at": theme.latest_finding_at,
            "last_qualified_at": theme.last_qualified_at,
            "last_synthesized_at": theme.last_synthesized_at,
            "centroid_embedding": "[0.4,0.5]",
            "created_at": theme.created_at,
            "updated_at": theme.updated_at,
            "metadata": theme.metadata,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(rowcount=1),
                FakeCursor(rows=[row]),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresThemeRepository(connection=connection)

        self.assertEqual(repository.save_themes([theme]), 1)
        self.assertEqual(repository.save_theme_findings([assignment]), 1)
        self.assertEqual(repository.list_themes(user_niche_id=theme.user_niche_id), [theme])
        self.assertEqual(
            repository.list_changed_themes(user_niche_id=theme.user_niche_id, since=updated_at),
            [theme],
        )
        self.assertIn("ON CONFLICT (id) DO UPDATE", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][14], "[0.4,0.5]")
        self.assertIn("ON CONFLICT (theme_id, finding_id) DO UPDATE", connection.calls[1][0])
        self.assertEqual(json.loads(connection.calls[1][1][-2]), {"same_unmet_need": True})
        self.assertEqual(connection.commit_count, 2)

    def test_theme_repository_refreshes_rollups(self):
        connection = FakeConnection([FakeCursor(rowcount=2)])
        repository = PostgresThemeRepository(connection=connection)

        self.assertEqual(
            repository.refresh_theme_rollups(
                [
                    "c9158d97-9449-4bf2-9ef5-17bb825d522f",
                    " ",
                    "349d4322-1614-48c1-a7d3-b50b3821a27c",
                ]
            ),
            2,
        )

        query, params = connection.calls[0]
        self.assertIn("JOIN findings f ON f.id = tf.finding_id", query)
        self.assertIn("avg(f.embedding)", query)
        self.assertEqual(
            params[0],
            [
                "c9158d97-9449-4bf2-9ef5-17bb825d522f",
                "349d4322-1614-48c1-a7d3-b50b3821a27c",
            ],
        )
        self.assertEqual(connection.commit_count, 1)

    def test_theme_repository_lists_findings_for_theme(self):
        extracted_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
        row = {
            "id": "349d4322-1614-48c1-a7d3-b50b3821a27c",
            "user_niche_id": "8de09fb9-75d0-40d5-b3ea-703ffea6a853",
            "niche_id": None,
            "source_id": "a815ccce-9fec-4528-8d9f-946c2d42ac29",
            "company_id": None,
            "post_id": "hn:123",
            "post_title": "Schema change issue",
            "source_url": "https://hn.algolia.com/api/v1/search",
            "evidence_url": "https://news.ycombinator.com/item?id=123",
            "evidence_text": "Incremental models break on schema changes.",
            "pain": "dbt incremental models break on schema changes",
            "affected_user": "analytics engineers",
            "job_to_be_done": "keep warehouse transforms reliable",
            "current_workaround": None,
            "category": "data reliability",
            "urgency": "high",
            "severity": "medium",
            "willingness_to_pay": False,
            "confidence": 0.82,
            "detected_at": extracted_at,
            "extracted_at": extracted_at,
            "pipeline_run_id": "run-1",
            "structured_embedding_text": "dbt incremental models break",
            "embedding": "[0.1,0.2]",
            "metadata": {"source_family": "forums"},
        }
        connection = FakeConnection([FakeCursor(rows=[row])])
        repository = PostgresThemeRepository(connection=connection)

        findings = repository.list_findings_for_theme(
            "c9158d97-9449-4bf2-9ef5-17bb825d522f"
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].pain, "dbt incremental models break on schema changes")
        self.assertIn("JOIN theme_findings tf", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1], ("c9158d97-9449-4bf2-9ef5-17bb825d522f",))

    def test_pipeline_run_metrics_repository_saves_and_loads_metrics(self):
        metrics = PipelineRunMetrics.create(
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
        row = {
            "id": metrics.id,
            "ran_at": metrics.ran_at,
            "fetched_count": 10,
            "fetch_failed_count": 1,
            "rule_filtered_count": 2,
            "llm_filtered_count": 3,
            "relevance_failed_count": 0,
            "extraction_attempted_count": 4,
            "extracted_count": 3,
            "no_signal_count": 1,
            "extraction_failed_count": 0,
            "signal_inserted_count": 3,
            "scored_count": 3,
            "scoring_failed_count": 0,
            "average_score": 7.5,
            "embedding_failed_count": 0,
            "clustered_count": 2,
            "cluster_inserted_count": 2,
            "opportunity_synthesized_count": 1,
            "opportunity_inserted_count": 1,
            "opportunity_failed_count": 0,
            "email_sent": True,
            "email_error": None,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresPipelineRunMetricsRepository(connection=connection)

        self.assertTrue(repository.save_pipeline_run_metrics(metrics))
        self.assertEqual(repository.list_pipeline_run_metrics(), [metrics])
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "run-1")
        self.assertEqual(connection.commit_count, 1)

    def test_source_locator_repository_saves_and_loads_enabled_locators(self):
        locator = SourceLocator.create(
            id="locator-1",
            locator="https://example.com/reviews",
            limit=10,
            options={"section": "reviews"},
        )
        row = {
            "id": "locator-1",
            "locator": "https://example.com/reviews",
            "enabled": True,
            "limit_value": 10,
            "options": {"section": "reviews"},
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresSourceLocatorRepository(connection=connection)

        self.assertEqual(repository.save_source_locators([locator]), 1)
        self.assertEqual(repository.get_source_locator("locator-1"), locator)
        self.assertEqual(repository.list_source_locators(enabled=True), [locator])
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "locator-1")
        self.assertEqual(json.loads(connection.calls[0][1][-1]), {"section": "reviews"})
        self.assertEqual(connection.calls[2][1], (True,))
        self.assertEqual(connection.commit_count, 1)

    def test_source_repository_saves_loads_and_filters_sources(self):
        created_at = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
        source = Source.create(
            id="source-1",
            locator="https://api.github.com/search/issues?q=repo:owner/repo",
            source_type="github_issues_search",
            source_family="technical_forum",
            access_mode="api",
            is_gate_free=True,
            created_at=created_at,
            updated_at=created_at,
        )
        row = {
            "id": "source-1",
            "locator": source.locator,
            "source_type": "github_issues_search",
            "source_family": "technical_forum",
            "is_gate_free": True,
            "access_mode": "api",
            "requires_proxy": False,
            "requires_auth": False,
            "created_at": created_at,
            "updated_at": created_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresSourceRepository(connection=connection)

        self.assertEqual(repository.save_sources([source]), 1)
        self.assertEqual(repository.get_source("source-1"), source)
        self.assertEqual(
            repository.get_source_by_identity("github_issues_search", source.locator),
            source,
        )
        self.assertEqual(
            repository.list_sources(source_family="technical_forum"),
            [source],
        )
        self.assertIn(
            "ON CONFLICT (source_type, locator) DO NOTHING",
            connection.calls[0][0],
        )
        self.assertEqual(connection.calls[0][1][0], "source-1")
        self.assertEqual(
            connection.calls[2][1],
            ("github_issues_search", source.locator),
        )
        self.assertEqual(connection.calls[3][1], ("technical_forum",))
        self.assertEqual(connection.commit_count, 1)

    def test_template_source_binding_repository_saves_lists_and_deletes(self):
        created_at = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
        binding = TemplateSourceBinding.create(
            id="binding-1",
            template_niche_id="template-1",
            source_id="source-1",
            default_limit=25,
            default_options={"adapter": "json"},
            tier=1,
            signal_quality_score=0.95,
            created_at=created_at,
            updated_at=created_at,
        )
        row = {
            "id": "binding-1",
            "template_niche_id": "template-1",
            "source_id": "source-1",
            "company_id": None,
            "default_enabled": True,
            "default_limit_value": 25,
            "default_scan_frequency": None,
            "default_buyer_voice_verified": False,
            "default_options": {"adapter": "json"},
            "tier": 1,
            "signal_quality_score": 0.95,
            "recommended_cadence": None,
            "created_at": created_at,
            "updated_at": created_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(rows=[row]),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresTemplateSourceBindingRepository(connection=connection)

        self.assertEqual(repository.save_template_source_bindings([binding]), 1)
        self.assertEqual(
            repository.list_template_source_bindings(
                "template-1",
                default_enabled=True,
            ),
            [binding],
        )
        self.assertTrue(repository.delete_template_source_binding("binding-1"))
        self.assertIn(
            "ON CONFLICT (template_niche_id, source_id) DO NOTHING",
            connection.calls[0][0],
        )
        self.assertEqual(json.loads(connection.calls[0][1][8]), {"adapter": "json"})
        self.assertEqual(connection.calls[1][1], ("template-1", True))
        self.assertEqual(connection.calls[2][1], ("binding-1",))
        self.assertEqual(connection.commit_count, 2)

    def test_user_source_preference_repository_upserts_loads_and_deletes(self):
        created_at = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
        preference = UserSourcePreference.create(
            id="preference-1",
            user_niche_id="user-niche-1",
            source_id="source-1",
            enabled=False,
            muted=True,
            cadence_override="weekly",
            priority_override=2,
            limit_override=10,
            options_override={"topic": "bugs"},
            created_at=created_at,
            updated_at=created_at,
        )
        row = {
            "id": "preference-1",
            "user_niche_id": "user-niche-1",
            "source_id": "source-1",
            "enabled": False,
            "muted": True,
            "cadence_override": "weekly",
            "priority_override": 2,
            "limit_override": 10,
            "options_override": {"topic": "bugs"},
            "created_at": created_at,
            "updated_at": created_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresUserSourcePreferenceRepository(connection=connection)

        self.assertTrue(repository.save_user_source_preference(preference))
        self.assertEqual(
            repository.get_user_source_preference("user-niche-1", "source-1"),
            preference,
        )
        self.assertEqual(
            repository.list_user_source_preferences("user-niche-1"),
            [preference],
        )
        self.assertTrue(repository.delete_user_source_preference("preference-1"))
        self.assertIn(
            "ON CONFLICT (user_niche_id, source_id) DO UPDATE",
            connection.calls[0][0],
        )
        self.assertEqual(json.loads(connection.calls[0][1][8]), {"topic": "bugs"})
        self.assertEqual(connection.calls[1][1], ("user-niche-1", "source-1"))
        self.assertEqual(connection.calls[2][1], ("user-niche-1",))
        self.assertEqual(connection.calls[3][1], ("preference-1",))
        self.assertEqual(connection.commit_count, 2)

    def test_user_source_repository_upserts_loads_lists_and_deletes(self):
        created_at = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)
        source = UserSource.create(
            id="user-source-1",
            user_niche_id="user-niche-1",
            source_id="source-1",
            template_source_binding_id="binding-1",
            enabled=True,
            muted=False,
            cadence="daily",
            priority=2,
            limit=10,
            options={"adapter": "json"},
            created_at=created_at,
            updated_at=created_at,
        )
        row = {
            "id": "user-source-1",
            "user_niche_id": "user-niche-1",
            "source_id": "source-1",
            "template_source_binding_id": "binding-1",
            "enabled": True,
            "muted": False,
            "cadence": "daily",
            "priority": 2,
            "limit_value": 10,
            "options": {"adapter": "json"},
            "created_at": created_at,
            "updated_at": created_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresUserSourceRepository(connection=connection)

        self.assertEqual(repository.save_user_sources([source]), 1)
        self.assertEqual(
            repository.get_user_source("user-niche-1", "source-1"),
            source,
        )
        self.assertEqual(
            repository.list_user_sources(
                "user-niche-1",
                enabled=True,
                include_muted=False,
            ),
            [source],
        )
        self.assertTrue(repository.delete_user_source("user-source-1"))
        self.assertIn("INSERT INTO user_sources", connection.calls[0][0])
        self.assertIn(
            "ON CONFLICT (user_niche_id, source_id) DO UPDATE",
            connection.calls[0][0],
        )
        self.assertEqual(json.loads(connection.calls[0][1][9]), {"adapter": "json"})
        self.assertEqual(connection.calls[1][1], ("user-niche-1", "source-1"))
        self.assertEqual(connection.calls[2][1], ("user-niche-1", True))
        self.assertEqual(connection.calls[3][1], ("user-source-1",))
        self.assertEqual(connection.commit_count, 2)

    def test_user_source_run_stats_repository_upserts_and_loads_stats(self):
        scanned_at = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)
        updated_at = datetime(2026, 6, 13, 12, 1, tzinfo=UTC)
        stats = UserSourceRunStats.create(
            user_niche_id="user-niche-1",
            source_id="source-1",
            template_source_binding_id="binding-1",
            total_runs=2,
            success_count=1,
            failure_count=1,
            consecutive_failures=1,
            posts_fetched_count=30,
            relevant_posts_count=6,
            rule_filtered_count=12,
            llm_filtered_count=5,
            relevance_failed_count=1,
            extracted_signals_count=3,
            gap_count=1,
            last_status="failing",
            last_error="blocked",
            last_rule_filtered_count=4,
            last_llm_filtered_count=2,
            last_relevance_failed_count=1,
            rejection_breakdown={"wrong_subject": 7, "tutorial_or_template": 5},
            last_rejection_breakdown={"wrong_subject": 3, "tutorial_or_template": 2},
            last_scanned_at=scanned_at,
            updated_at=updated_at,
        )
        row = {
            "user_niche_id": "user-niche-1",
            "source_id": "source-1",
            "template_source_binding_id": "binding-1",
            "total_runs": 2,
            "success_count": 1,
            "failure_count": 1,
            "consecutive_failures": 1,
            "posts_fetched_count": 30,
            "relevant_posts_count": 6,
            "rule_filtered_count": 12,
            "llm_filtered_count": 5,
            "relevance_failed_count": 1,
            "extracted_signals_count": 3,
            "gap_count": 1,
            "last_status": "failing",
            "last_error": "blocked",
            "last_fetched_count": 0,
            "last_relevant_count": 0,
            "last_rule_filtered_count": 4,
            "last_llm_filtered_count": 2,
            "last_relevance_failed_count": 1,
            "last_extracted_count": 0,
            "last_gap_count": 0,
            "rejection_breakdown": {"wrong_subject": 7, "tutorial_or_template": 5},
            "last_rejection_breakdown": {"wrong_subject": 3, "tutorial_or_template": 2},
            "last_scanned_at": scanned_at,
            "updated_at": updated_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresUserSourceRunStatsRepository(connection=connection)

        self.assertTrue(repository.upsert_user_source_run_stats(stats))
        self.assertEqual(
            repository.get_user_source_run_stats("user-niche-1", "source-1"),
            stats,
        )
        self.assertEqual(
            repository.list_user_source_run_stats("user-niche-1", ["source-1"]),
            [stats],
        )
        self.assertIn("INSERT INTO user_source_run_stats", connection.calls[0][0])
        self.assertIn("ON CONFLICT (user_niche_id, source_id)", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "user-niche-1")
        self.assertEqual(connection.calls[0][1][1], "source-1")
        self.assertEqual(connection.calls[0][1][2], "binding-1")
        self.assertEqual(connection.calls[1][1], ("user-niche-1", "source-1"))
        self.assertEqual(connection.calls[2][1], ("user-niche-1", "source-1"))
        self.assertEqual(connection.commit_count, 1)

    @unittest.skip("PostgresNicheCompanyRepository API changed — save_competitors replaced by save_niche_companies")
    def test_competitor_repository_saves_and_loads_competitors(self):
        created_at = datetime(2026, 5, 21, 12, 0, tzinfo=UTC)
        competitor = Competitor.create(
            id="competitor-1",
            name="Acme CRM",
            website="https://acme.example",
            category="crm",
            market_id="market-1",
            created_at=created_at,
        )
        row = {
            "id": "competitor-1",
            "name": "Acme CRM",
            "website": "https://acme.example",
            "category": "crm",
            "description": None,
            "market_id": "market-1",
            "created_at": created_at,
        }
        connection = FakeConnection([FakeCursor(rowcount=1), FakeCursor(row=row)])
        repository = PostgresNicheCompanyRepository(connection=connection)

        self.assertEqual(repository.save_competitors([competitor]), 1)
        self.assertEqual(repository.get_competitor("competitor-1"), competitor)
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.commit_count, 1)

    @unittest.skip("PostgresMarketRepository removed — use PostgresUserNicheRepository")
    def test_market_repository_saves_and_loads_markets(self):
        created_at = datetime(2026, 5, 23, 11, 0, tzinfo=UTC)
        market = Market.create(
            id="workspace-tools",
            name="Workspace tools",
            description="Tools for async teams.",
            target_user="product teams",
            idea_prompt="Find workflow gaps in collaboration tools.",
            created_at=created_at,
        )
        row = {
            "id": "workspace-tools",
            "name": "Workspace tools",
            "description": "Tools for async teams.",
            "target_user": "product teams",
            "idea_prompt": "Find workflow gaps in collaboration tools.",
            "created_at": created_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
                FakeCursor(rowcount=1),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresMarketRepository(connection=connection)

        self.assertEqual(repository.save_markets([market]), 1)
        self.assertEqual(repository.get_market("workspace-tools"), market)
        self.assertEqual(repository.list_markets(), [market])
        self.assertTrue(
            repository.update_market(
                Market.create(
                    id="workspace-tools",
                    name="Workspace intelligence",
                    created_at=created_at,
                )
            )
        )
        self.assertTrue(repository.delete_market("workspace-tools"))
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "workspace-tools")
        self.assertIn("UPDATE markets", connection.calls[3][0])
        self.assertIn("DELETE FROM markets", connection.calls[4][0])
        self.assertEqual(connection.commit_count, 3)

    def test_agent_preferences_repository_saves_and_loads_preferences(self):
        created_at = datetime(2026, 5, 25, 16, 0, tzinfo=UTC)
        preferences = AgentPreferences.create(
            user_niche_id="workspace-tools",
            preferred_source_families=["reviews"],
            ignored_themes=["pricing"],
            created_at=created_at,
        )
        row = {
            "user_niche_id": "workspace-tools",
            "preferred_source_families": ["reviews"],
            "ignored_themes": ["pricing"],
            "ignored_categories": [],
            "muted_source_ids": [],
            "extra_instructions": None,
            "created_at": created_at,
            "updated_at": preferences.updated_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresAgentPreferencesRepository(connection=connection)

        self.assertTrue(repository.save_agent_preferences(preferences))
        self.assertEqual(
            repository.get_agent_preferences("workspace-tools"),
            preferences,
        )
        self.assertTrue(repository.delete_agent_preferences("workspace-tools"))
        self.assertIn("INSERT INTO agent_preferences", connection.calls[0][0])
        self.assertIn("SELECT * FROM agent_preferences", connection.calls[1][0])
        self.assertIn("DELETE FROM agent_preferences", connection.calls[2][0])
        self.assertEqual(connection.commit_count, 2)

    def test_agent_feedback_repository_saves_and_loads_feedback(self):
        created_at = datetime(2026, 5, 25, 16, 10, tzinfo=UTC)
        feedback = AgentFeedback.create(
            id="feedback-1",
            user_niche_id="workspace-tools",
            opportunity_id="opportunity-1",
            action="save",
            created_at=created_at,
        )
        row = {
            "id": "feedback-1",
            "user_niche_id": "workspace-tools",
            "opportunity_id": "opportunity-1",
            "action": "save",
            "reason": None,
            "created_at": created_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresAgentFeedbackRepository(connection=connection)

        self.assertTrue(repository.save_agent_feedback(feedback))
        self.assertEqual(
            repository.list_agent_feedback(user_niche_id="workspace-tools"),
            [feedback],
        )
        self.assertIn("INSERT INTO agent_feedback", connection.calls[0][0])
        self.assertIn("SELECT * FROM agent_feedback", connection.calls[1][0])
        self.assertEqual(connection.commit_count, 1)

    def test_agent_activity_repository_saves_and_loads_activity(self):
        created_at = datetime(2026, 5, 25, 16, 20, tzinfo=UTC)
        activity = AgentActivity.create(
            id="activity-1",
            user_niche_id="workspace-tools",
            event_type="run_completed",
            title="Scan completed",
            metadata={"fetched_count": 12},
            created_at=created_at,
        )
        row = {
            "id": "activity-1",
            "user_niche_id": "workspace-tools",
            "event_type": "run_completed",
            "title": "Scan completed",
            "detail": None,
            "metadata": {"fetched_count": 12},
            "created_at": created_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresAgentActivityRepository(connection=connection)

        self.assertTrue(repository.save_agent_activity(activity))
        self.assertEqual(
            repository.list_agent_activity(user_niche_id="workspace-tools", limit=5),
            [activity],
        )
        self.assertIn("INSERT INTO agent_activity", connection.calls[0][0])
        self.assertIn("SELECT * FROM agent_activity", connection.calls[1][0])
        self.assertIn("workspace-tools", connection.calls[1][1])
        self.assertEqual(connection.commit_count, 1)

    @unittest.skip("PostgresNicheSourceRepository API changed — MonitoredSource replaced by NicheSource")
    def test_monitored_source_repository_saves_and_loads_enabled_sources(self):
        source = MonitoredSource.create(
            id="source-1",
            competitor_id="competitor-1",
            market_id="market-1",
            locator="https://acme.example/reviews",
            source_type="reviews",
            limit=10,
            options={"section": "reviews"},
        )
        row = {
            "id": "source-1",
            "competitor_id": "competitor-1",
            "market_id": "market-1",
            "locator": "https://acme.example/reviews",
            "source_type": "reviews",
            "enabled": True,
            "limit_value": 10,
            "scan_frequency": None,
            "last_scanned_at": None,
            "last_error": None,
            "options": {"section": "reviews"},
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
                FakeCursor(rowcount=1),
            ]
        )
        repository = PostgresNicheSourceRepository(connection=connection)

        self.assertEqual(repository.save_monitored_sources([source]), 1)
        self.assertEqual(repository.get_monitored_source("source-1"), source)
        self.assertEqual(
            repository.list_monitored_sources(
                competitor_id="competitor-1",
                market_id="market-1",
                enabled=True,
            ),
            [source],
        )
        self.assertIn("ON CONFLICT (id) DO NOTHING", connection.calls[0][0])
        self.assertEqual(json.loads(connection.calls[0][1][-1]), {"section": "reviews"})
        self.assertEqual(connection.calls[2][1], ("competitor-1", "market-1", True))
        self.assertIn("market_id = %s", connection.calls[2][0])
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
        self.assertIn("UPDATE monitored_sources", connection.calls[3][0])
        self.assertEqual(connection.calls[3][1][0], "forum")
        self.assertEqual(connection.calls[3][1][1], "competitor-1")
        self.assertEqual(connection.calls[3][1][2], "market-1")
        self.assertEqual(connection.calls[3][1][3], False)
        self.assertEqual(connection.calls[3][1][4], 25)
        self.assertEqual(json.loads(connection.calls[3][1][-2]), {"section": "support"})
        self.assertEqual(connection.calls[3][1][-1], "source-1")
        self.assertEqual(connection.commit_count, 2)

    def test_niche_source_repository_persists_run_stats(self):
        scanned_at = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
        updated_at = datetime(2026, 6, 2, 12, 1, tzinfo=UTC)
        stats = NicheSourceRunStats.create(
            niche_source_id="source-1",
            total_runs=2,
            success_count=1,
            failure_count=1,
            consecutive_failures=1,
            posts_fetched_count=30,
            relevant_posts_count=6,
            rule_filtered_count=12,
            llm_filtered_count=5,
            relevance_failed_count=1,
            extracted_signals_count=3,
            gap_count=1,
            last_status="failing",
            last_error="blocked",
            last_rule_filtered_count=4,
            last_llm_filtered_count=2,
            last_relevance_failed_count=1,
            rejection_breakdown={"wrong_subject": 7, "tutorial_or_template": 5},
            last_rejection_breakdown={"wrong_subject": 3, "tutorial_or_template": 2},
            last_scanned_at=scanned_at,
            updated_at=updated_at,
        )
        row = {
            "niche_source_id": "source-1",
            "total_runs": 2,
            "success_count": 1,
            "failure_count": 1,
            "consecutive_failures": 1,
            "posts_fetched_count": 30,
            "relevant_posts_count": 6,
            "rule_filtered_count": 12,
            "llm_filtered_count": 5,
            "relevance_failed_count": 1,
            "extracted_signals_count": 3,
            "gap_count": 1,
            "last_status": "failing",
            "last_error": "blocked",
            "last_fetched_count": 0,
            "last_relevant_count": 0,
            "last_rule_filtered_count": 4,
            "last_llm_filtered_count": 2,
            "last_relevance_failed_count": 1,
            "last_extracted_count": 0,
            "last_gap_count": 0,
            "rejection_breakdown": {"wrong_subject": 7, "tutorial_or_template": 5},
            "last_rejection_breakdown": {"wrong_subject": 3, "tutorial_or_template": 2},
            "last_scanned_at": scanned_at,
            "updated_at": updated_at,
        }
        connection = FakeConnection([
            FakeCursor(rowcount=1),
            FakeCursor(row=row),
            FakeCursor(rows=[row]),
        ])
        repository = PostgresNicheSourceRepository(connection=connection)

        self.assertTrue(repository.upsert_niche_source_run_stats(stats))
        self.assertEqual(repository.get_niche_source_run_stats("source-1"), stats)
        self.assertEqual(repository.list_niche_source_run_stats(["source-1"]), [stats])
        self.assertIn("INSERT INTO niche_source_health_stats", connection.calls[0][0])
        self.assertIn("ON CONFLICT (niche_source_id)", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "source-1")
        self.assertEqual(connection.calls[1][1], ("source-1",))
        self.assertEqual(connection.calls[2][1], ("source-1",))
        self.assertEqual(connection.commit_count, 1)

    def test_niche_source_repository_updates_quality_score(self):
        connection = FakeConnection([FakeCursor(rowcount=1)])
        repository = PostgresNicheSourceRepository(connection=connection)

        self.assertTrue(
            repository.update_niche_source_quality(
                "source-1",
                0.74,
                buyer_voice_verified=True,
            )
        )

        self.assertIn("UPDATE niche_sources", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1], (0.74, True, "source-1"))
        self.assertEqual(connection.commit_count, 1)

    def test_niche_source_repository_updates_source(self):
        source = NicheSource.create(
            id="source-1",
            niche_id="niche-1",
            locator="https://example.com/forum.json",
            source_type="discourse_json",
            source_family="forum",
            is_gate_free=True,
            enabled=False,
            limit=15,
            scan_frequency="daily",
            buyer_voice_verified=True,
            health_status="productive",
            options={"adapter": "json", "source_family": "forum"},
            tier=2,
            signal_quality_score=0.82,
            access_mode="json",
            recommended_cadence="daily",
        )
        connection = FakeConnection([FakeCursor(rowcount=1)])
        repository = PostgresNicheSourceRepository(connection=connection)

        self.assertTrue(repository.update_niche_source(source))

        self.assertIn("UPDATE niche_sources", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], None)
        self.assertEqual(connection.calls[0][1][1], "https://example.com/forum.json")
        self.assertEqual(connection.calls[0][1][2], "discourse_json")
        self.assertEqual(json.loads(connection.calls[0][1][12]), source.options)
        self.assertEqual(connection.calls[0][1][-1], "source-1")
        self.assertEqual(connection.commit_count, 1)

    @unittest.skip("PostgresSourceHealthRepository removed — health tracked on NicheSource")
    def test_source_health_repository_saves_and_loads_health(self):
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
        row = {
            "monitored_source_id": "source-1",
            "total_runs": 1,
            "success_count": 1,
            "failure_count": 0,
            "consecutive_failures": 0,
            "posts_fetched_count": 5,
            "relevant_posts_count": 2,
            "extracted_signals_count": 1,
            "opportunity_count": 1,
            "last_status": "healthy",
            "last_error": None,
            "last_fetched_count": 5,
            "last_relevant_count": 2,
            "last_extracted_count": 1,
            "last_opportunity_count": 1,
            "last_scanned_at": scanned_at,
            "updated_at": scanned_at,
        }
        connection = FakeConnection(
            [
                FakeCursor(rowcount=1),
                FakeCursor(row=row),
                FakeCursor(rows=[row]),
            ]
        )
        repository = PostgresSourceHealthRepository(connection=connection)

        self.assertTrue(repository.save_source_health(health))
        self.assertEqual(repository.get_source_health("source-1"), health)
        self.assertEqual(
            repository.list_source_health(status="healthy"),
            [health],
        )
        self.assertIn("INSERT INTO source_health", connection.calls[0][0])
        self.assertIn("ON CONFLICT (monitored_source_id)", connection.calls[0][0])
        self.assertEqual(connection.calls[0][1][0], "source-1")
        self.assertEqual(connection.calls[2][1], ("healthy",))
        self.assertEqual(connection.commit_count, 1)


if __name__ == "__main__":
    unittest.main()
