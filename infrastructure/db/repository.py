"""Database repository implementations for domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from application.ports import (
    AgentActionRepository,
    AgentActivityRepository,
    AgentAlertRepository,
    AgentFeedbackRepository,
    AgentFollowUpRepository,
    AgentPreferencesRepository,
    ClusterRepository,
    FindingRepository,
    OpportunityRepository,
    PipelineRunMetricsRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceLocatorRepository,
    ThemeRepository,
)
from domain.agent import (
    AgentAction,
    AgentActivity,
    AgentAlert,
    AgentFeedback,
    AgentFollowUp,
    AgentPreferences,
)
from domain.cluster import SignalCluster
from domain.finding import Finding
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import SourceLocator
from domain.theme import Theme, ThemeFinding


@dataclass
class InMemoryPostRepository(PostRepository):
    """In-memory raw post repository."""

    posts: dict[str, RawPost] = field(default_factory=dict)

    def save_posts(self, posts: list[RawPost]) -> int:
        inserted_count = 0
        for post in posts:
            if post.id in self.posts:
                continue
            self.posts[post.id] = post
            inserted_count += 1
        return inserted_count

    def get_post(self, post_id: str) -> RawPost | None:
        return self.posts.get(post_id)

    def list_posts(self) -> list[RawPost]:
        return list(self.posts.values())


@dataclass
class InMemorySignalRepository(SignalRepository):
    """In-memory signal repository."""

    signals: dict[str, Signal] = field(default_factory=dict)

    def save_signals(self, signals: list[Signal]) -> int:
        inserted_count = 0
        for signal in signals:
            if signal.id in self.signals:
                continue
            self.signals[signal.id] = signal
            inserted_count += 1
        return inserted_count

    def get_signal(self, signal_id: str) -> Signal | None:
        return self.signals.get(signal_id)

    def delete_signal(self, signal_id: str) -> bool:
        return self.signals.pop(signal_id, None) is not None

    def list_signals(self) -> list[Signal]:
        return list(self.signals.values())


@dataclass
class InMemoryScoreRepository(ScoreRepository):
    """In-memory opportunity score repository."""

    scores: dict[str, OpportunityScore] = field(default_factory=dict)

    def save_scores(self, scores: list[OpportunityScore]) -> int:
        inserted_count = 0
        for score in scores:
            if score.signal_id in self.scores:
                continue
            self.scores[score.signal_id] = score
            inserted_count += 1
        return inserted_count

    def get_score(self, signal_id: str) -> OpportunityScore | None:
        return self.scores.get(signal_id)

    def delete_score(self, signal_id: str) -> bool:
        return self.scores.pop(signal_id, None) is not None

    def list_scores(self) -> list[OpportunityScore]:
        return list(self.scores.values())


@dataclass
class InMemoryClusterRepository(ClusterRepository):
    """In-memory signal cluster repository."""

    clusters: dict[str, SignalCluster] = field(default_factory=dict)

    def save_clusters(self, clusters: list[SignalCluster]) -> int:
        saved_count = 0
        seen_ids: set[str] = set()
        for cluster in clusters:
            if cluster.id in seen_ids:
                continue
            seen_ids.add(cluster.id)
            self.clusters[cluster.id] = cluster
            saved_count += 1
        return saved_count

    def get_cluster(self, cluster_id: str) -> SignalCluster | None:
        return self.clusters.get(cluster_id)

    def list_clusters(self) -> list[SignalCluster]:
        return list(self.clusters.values())


@dataclass
class InMemoryOpportunityRepository(OpportunityRepository):
    """In-memory synthesized opportunity repository."""

    opportunities: dict[str, Opportunity] = field(default_factory=dict)

    def save_opportunities(self, opportunities: list[Opportunity]) -> int:
        saved_count = 0
        seen_ids: set[str] = set()
        for opportunity in opportunities:
            if opportunity.id in seen_ids:
                continue
            seen_ids.add(opportunity.id)
            self.opportunities[opportunity.id] = opportunity
            saved_count += 1
        return saved_count

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        return self.opportunities.get(opportunity_id)

    def list_opportunities(self) -> list[Opportunity]:
        return list(self.opportunities.values())


@dataclass
class InMemoryAgentActionRepository(AgentActionRepository):
    """In-memory agent action repository."""

    actions_by_id: dict[str, AgentAction] = field(default_factory=dict)

    def save_agent_action(self, action: AgentAction) -> bool:
        if action.id in self.actions_by_id:
            return False
        self.actions_by_id[action.id] = action
        return True

    def list_agent_actions(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        action_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAction]:
        actions = list(self.actions_by_id.values())
        if user_niche_id is not None:
            actions = [item for item in actions if item.user_niche_id == user_niche_id]
        if status is not None:
            actions = [item for item in actions if item.status == status]
        if action_type is not None:
            actions = [item for item in actions if item.action_type == action_type]
        actions = sorted(
            actions,
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        return actions[:limit] if limit is not None else actions

    def update_agent_action_status(
        self,
        action_id: str,
        status: str,
    ) -> AgentAction | None:
        action = self.actions_by_id.get(action_id)
        if action is None:
            return None
        updated = AgentAction.create(
            id=action.id,
            user_niche_id=action.user_niche_id,
            action_type=action.action_type,
            status=status,
            reason=action.reason,
            metadata=action.metadata,
            created_at=action.created_at,
            completed_at=datetime.now(UTC)
            if status in {"completed", "failed"}
            else action.completed_at,
        )
        self.actions_by_id[action_id] = updated
        return updated


@dataclass
class InMemoryAgentPreferencesRepository(AgentPreferencesRepository):
    """In-memory agent preferences repository."""

    preferences_by_user_niche: dict[str, AgentPreferences] = field(default_factory=dict)

    def save_agent_preferences(self, preferences: AgentPreferences) -> bool:
        self.preferences_by_user_niche[preferences.user_niche_id] = preferences
        return True

    def get_agent_preferences(self, user_niche_id: str) -> AgentPreferences | None:
        return self.preferences_by_user_niche.get(user_niche_id)

    def delete_agent_preferences(self, user_niche_id: str) -> bool:
        return self.preferences_by_user_niche.pop(user_niche_id, None) is not None


@dataclass
class InMemoryAgentFeedbackRepository(AgentFeedbackRepository):
    """In-memory agent feedback repository."""

    feedback_by_id: dict[str, AgentFeedback] = field(default_factory=dict)

    def save_agent_feedback(self, feedback: AgentFeedback) -> bool:
        self.feedback_by_id[feedback.id] = feedback
        return True

    def list_agent_feedback(
        self,
        *,
        user_niche_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        feedback = list(self.feedback_by_id.values())
        if user_niche_id is not None:
            feedback = [item for item in feedback if item.user_niche_id == user_niche_id]
        if opportunity_id is not None:
            feedback = [
                item for item in feedback if item.opportunity_id == opportunity_id
            ]
        if action is not None:
            feedback = [item for item in feedback if item.action == action]
        return sorted(feedback, key=lambda item: item.created_at or datetime.min)


@dataclass
class InMemoryAgentActivityRepository(AgentActivityRepository):
    """In-memory agent activity repository."""

    activity_by_id: dict[str, AgentActivity] = field(default_factory=dict)

    def save_agent_activity(self, activity: AgentActivity) -> bool:
        if activity.id in self.activity_by_id:
            return False
        self.activity_by_id[activity.id] = activity
        return True

    def list_agent_activity(
        self,
        *,
        user_niche_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentActivity]:
        activity = list(self.activity_by_id.values())
        if user_niche_id is not None:
            activity = [item for item in activity if item.user_niche_id == user_niche_id]
        if event_type is not None:
            activity = [item for item in activity if item.event_type == event_type]
        activity = sorted(
            activity,
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        return activity[:limit] if limit is not None else activity


@dataclass
class InMemoryAgentAlertRepository(AgentAlertRepository):
    """In-memory agent alert repository."""

    alerts_by_id: dict[str, AgentAlert] = field(default_factory=dict)

    def save_agent_alert(self, alert: AgentAlert) -> bool:
        if alert.id in self.alerts_by_id:
            return False
        self.alerts_by_id[alert.id] = alert
        return True

    def get_agent_alert(self, alert_id: str) -> AgentAlert | None:
        return self.alerts_by_id.get(alert_id)

    def list_agent_alerts(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAlert]:
        alerts = list(self.alerts_by_id.values())
        if user_niche_id is not None:
            alerts = [item for item in alerts if item.user_niche_id == user_niche_id]
        if status is not None:
            alerts = [item for item in alerts if item.status == status]
        alerts = sorted(
            alerts,
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        return alerts[:limit] if limit is not None else alerts

    def acknowledge_agent_alert(self, alert_id: str) -> AgentAlert | None:
        alert = self.alerts_by_id.get(alert_id)
        if alert is None:
            return None
        acknowledged = alert.acknowledge()
        self.alerts_by_id[alert_id] = acknowledged
        return acknowledged


@dataclass
class InMemoryAgentFollowUpRepository(AgentFollowUpRepository):
    """In-memory agent follow-up repository."""

    follow_ups_by_id: dict[str, AgentFollowUp] = field(default_factory=dict)

    def save_agent_follow_up(self, follow_up: AgentFollowUp) -> bool:
        if follow_up.id in self.follow_ups_by_id:
            return False
        self.follow_ups_by_id[follow_up.id] = follow_up
        return True

    def list_agent_follow_ups(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentFollowUp]:
        follow_ups = list(self.follow_ups_by_id.values())
        if user_niche_id is not None:
            follow_ups = [
                item for item in follow_ups if item.user_niche_id == user_niche_id
            ]
        if status is not None:
            follow_ups = [item for item in follow_ups if item.status == status]
        follow_ups = sorted(
            follow_ups,
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        return follow_ups[:limit] if limit is not None else follow_ups

    def update_agent_follow_up(
        self,
        follow_up_id: str,
        *,
        status: str,
        response: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentFollowUp | None:
        follow_up = self.follow_ups_by_id.get(follow_up_id)
        if follow_up is None:
            return None
        updated = _updated_agent_follow_up(
            follow_up,
            status=status,
            response=response,
            metadata=metadata,
        )
        if updated is None:
            return None
        self.follow_ups_by_id[follow_up_id] = updated
        return updated


@dataclass
class InMemoryPipelineRunMetricsRepository(PipelineRunMetricsRepository):
    """In-memory pipeline run metrics repository."""

    metrics: dict[str, PipelineRunMetrics] = field(default_factory=dict)

    def save_pipeline_run_metrics(self, metrics: PipelineRunMetrics) -> bool:
        if metrics.id in self.metrics:
            return False
        self.metrics[metrics.id] = metrics
        return True

    def list_pipeline_run_metrics(self) -> list[PipelineRunMetrics]:
        return list(self.metrics.values())


@dataclass
class InMemorySourceLocatorRepository(SourceLocatorRepository):
    """In-memory source locator repository."""

    source_locators: dict[str, SourceLocator] = field(default_factory=dict)

    def save_source_locators(self, locators: list[SourceLocator]) -> int:
        inserted_count = 0
        for locator in locators:
            if locator.id in self.source_locators:
                continue
            self.source_locators[locator.id] = locator
            inserted_count += 1
        return inserted_count

    def get_source_locator(self, locator_id: str) -> SourceLocator | None:
        return self.source_locators.get(locator_id)

    def list_source_locators(self, enabled: bool | None = None) -> list[SourceLocator]:
        locators = list(self.source_locators.values())
        if enabled is None:
            return locators
        return [locator for locator in locators if locator.enabled == enabled]


@dataclass
class InMemoryNicheRepository:
    """In-memory niche repository."""

    _niches: dict = field(default_factory=dict)

    def save_niches(self, niches: list) -> int:
        count = 0
        for niche in niches:
            if niche.id not in self._niches:
                self._niches[niche.id] = niche
                count += 1
        return count

    def get_niche(self, niche_id: str):
        return self._niches.get(niche_id)

    def list_niches(self, *, category=None, status=None) -> list:
        niches = list(self._niches.values())
        if category is not None:
            niches = [n for n in niches if n.category == category]
        if status is not None:
            niches = [n for n in niches if n.status == status]
        return niches

    def update_niche(self, niche) -> bool:
        if niche.id not in self._niches:
            return False
        self._niches[niche.id] = niche
        return True

    def delete_niche(self, niche_id: str) -> bool:
        return self._niches.pop(niche_id, None) is not None


@dataclass
class InMemoryUserNicheRepository:
    """In-memory user niche repository."""

    _user_niches: dict = field(default_factory=dict)

    def save_user_niche(self, user_niche) -> bool:
        if user_niche.id in self._user_niches:
            return False
        self._user_niches[user_niche.id] = user_niche
        return True

    def get_user_niche(self, user_niche_id: str):
        return self._user_niches.get(user_niche_id)

    def list_user_niches(self, user_id: str) -> list:
        return [n for n in self._user_niches.values() if n.user_id == user_id]

    def list_all_user_niches(self) -> list:
        return list(self._user_niches.values())

    def update_user_niche(self, user_niche) -> bool:
        if user_niche.id not in self._user_niches:
            return False
        self._user_niches[user_niche.id] = user_niche
        return True

    def delete_user_niche(self, user_niche_id: str) -> bool:
        return self._user_niches.pop(user_niche_id, None) is not None


@dataclass
class InMemoryNicheCompanyRepository:
    """In-memory niche company repository."""

    _companies: dict = field(default_factory=dict)

    def save_niche_companies(self, companies: list) -> int:
        count = 0
        for company in companies:
            if company.id not in self._companies:
                self._companies[company.id] = company
                count += 1
        return count

    def list_niche_companies(self, niche_id: str) -> list:
        return [c for c in self._companies.values() if c.niche_id == niche_id]

    def delete_niche_company(self, company_id: str) -> bool:
        return self._companies.pop(company_id, None) is not None


@dataclass
class InMemoryNicheSourceRepository:
    """In-memory niche source repository."""

    _sources: dict = field(default_factory=dict)
    _run_stats: dict = field(default_factory=dict)

    def save_niche_sources(self, sources: list) -> int:
        count = 0
        for source in sources:
            if source.id not in self._sources:
                self._sources[source.id] = source
                count += 1
        return count

    def list_niche_sources(
        self,
        niche_id: str,
        *,
        enabled=None,
        is_gate_free=None,
        buyer_voice_verified=None,
    ) -> list:
        sources = [s for s in self._sources.values() if s.niche_id == niche_id]
        if enabled is not None:
            sources = [s for s in sources if s.enabled == enabled]
        if is_gate_free is not None:
            sources = [s for s in sources if s.is_gate_free == is_gate_free]
        if buyer_voice_verified is not None:
            sources = [s for s in sources if s.buyer_voice_verified == buyer_voice_verified]
        return sources

    def update_niche_source_health(
        self,
        source_id: str,
        health_status: str,
        last_scanned_at=None,
        last_error: str | None = None,
    ) -> bool:
        source = self._sources.get(source_id)
        if source is None:
            return False
        from dataclasses import replace
        self._sources[source_id] = replace(
            source,
            health_status=health_status,
            last_scanned_at=last_scanned_at,
            last_error=last_error,
        )
        return True

    def update_niche_source_quality(
        self,
        source_id: str,
        signal_quality_score: float,
        *,
        buyer_voice_verified: bool | None = None,
    ) -> bool:
        source = self._sources.get(source_id)
        if source is None:
            return False
        from dataclasses import replace
        updates = {"signal_quality_score": signal_quality_score}
        if buyer_voice_verified is not None:
            updates["buyer_voice_verified"] = buyer_voice_verified
        self._sources[source_id] = replace(source, **updates)
        return True

    def upsert_niche_source_run_stats(self, stats) -> bool:
        self._run_stats[stats.niche_source_id] = stats
        return True

    def get_niche_source_run_stats(self, source_id: str):
        return self._run_stats.get(source_id)

    def list_niche_source_run_stats(self, source_ids: list[str] | None = None) -> list:
        if source_ids is None:
            return list(self._run_stats.values())
        allowed = set(source_ids)
        return [
            stats
            for stats in self._run_stats.values()
            if stats.niche_source_id in allowed
        ]

    def update_niche_source(self, source) -> bool:
        if source.id not in self._sources:
            return False
        self._sources[source.id] = source
        return True

    def delete_niche_source(self, source_id: str) -> bool:
        self._run_stats.pop(source_id, None)
        return self._sources.pop(source_id, None) is not None


class _SQLiteRepository:
    """Shared SQLite connection and schema setup."""

    def __init__(self, database_path: str | Path = ":memory:"):
        self.connection = sqlite3.connect(str(database_path))
        self.connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def close(self) -> None:
        self.connection.close()

    def _initialize_schema(self) -> None:
        raise NotImplementedError


class SQLitePostRepository(_SQLiteRepository, PostRepository):
    """SQLite-backed raw post repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                author TEXT,
                url TEXT,
                created_at TEXT,
                upvotes INTEGER,
                comments_count INTEGER,
                metadata TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_posts(self, posts: list[RawPost]) -> int:
        inserted_count = 0
        for post in posts:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO posts (
                    id, source, source_id, title, body, author, url,
                    created_at, upvotes, comments_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.id,
                    post.source,
                    post.source_id,
                    post.title,
                    post.body,
                    post.author,
                    post.url,
                    _datetime_to_text(post.created_at),
                    post.upvotes,
                    post.comments_count,
                    _to_json(post.metadata),
                ),
            )
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

    def get_post(self, post_id: str) -> RawPost | None:
        row = self.connection.execute(
            "SELECT * FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        return _post_from_row(row) if row else None

    def list_posts(self) -> list[RawPost]:
        rows = self.connection.execute("SELECT * FROM posts ORDER BY id").fetchall()
        return [_post_from_row(row) for row in rows]


class SQLiteSignalRepository(_SQLiteRepository, SignalRepository):
    """SQLite-backed signal repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                pain TEXT NOT NULL,
                user_type TEXT,
                job_to_be_done TEXT,
                current_workaround TEXT,
                urgency TEXT NOT NULL,
                severity TEXT NOT NULL,
                willingness_to_pay INTEGER,
                category TEXT,
                confidence REAL NOT NULL,
                niche_company_id TEXT,
                niche_id TEXT,
                evidence_url TEXT,
                evidence_text TEXT,
                detected_at TEXT
            )
            """
        )
        self.connection.commit()

    def save_signals(self, signals: list[Signal]) -> int:
        inserted_count = 0
        for signal in signals:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO signals (
                    id, post_id, pain, user_type, job_to_be_done,
                    current_workaround, urgency, severity, willingness_to_pay,
                    category, confidence, niche_company_id, niche_id,
                    evidence_url, evidence_text, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.id,
                    signal.post_id,
                    signal.pain,
                    signal.user_type,
                    signal.job_to_be_done,
                    signal.current_workaround,
                    signal.urgency,
                    signal.severity,
                    _bool_to_int(signal.willingness_to_pay),
                    signal.category,
                    signal.confidence,
                    signal.niche_company_id,
                    signal.niche_id,
                    signal.evidence_url,
                    signal.evidence_text,
                    _datetime_to_text(signal.detected_at),
                ),
            )
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

    def get_signal(self, signal_id: str) -> Signal | None:
        row = self.connection.execute(
            "SELECT * FROM signals WHERE id = ?",
            (signal_id,),
        ).fetchone()
        return _signal_from_row(row) if row else None

    def delete_signal(self, signal_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM signals WHERE id = ?",
            (signal_id,),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_signals(self) -> list[Signal]:
        rows = self.connection.execute("SELECT * FROM signals ORDER BY id").fetchall()
        return [_signal_from_row(row) for row in rows]


class SQLiteScoreRepository(_SQLiteRepository, ScoreRepository):
    """SQLite-backed opportunity score repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                signal_id TEXT PRIMARY KEY,
                total_score REAL NOT NULL,
                urgency_score REAL NOT NULL,
                severity_score REAL NOT NULL,
                willingness_score REAL NOT NULL,
                confidence_score REAL NOT NULL,
                reasoning TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_scores(self, scores: list[OpportunityScore]) -> int:
        inserted_count = 0
        for score in scores:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO scores (
                    signal_id, total_score, urgency_score, severity_score,
                    willingness_score, confidence_score, reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.signal_id,
                    score.total_score,
                    score.urgency_score,
                    score.severity_score,
                    score.willingness_score,
                    score.confidence_score,
                    score.reasoning,
                ),
            )
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

    def get_score(self, signal_id: str) -> OpportunityScore | None:
        row = self.connection.execute(
            "SELECT * FROM scores WHERE signal_id = ?",
            (signal_id,),
        ).fetchone()
        return _score_from_row(row) if row else None

    def delete_score(self, signal_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM scores WHERE signal_id = ?",
            (signal_id,),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_scores(self) -> list[OpportunityScore]:
        rows = self.connection.execute("SELECT * FROM scores ORDER BY signal_id").fetchall()
        return [_score_from_row(row) for row in rows]


class SQLiteClusterRepository(_SQLiteRepository, ClusterRepository):
    """SQLite-backed signal cluster repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS clusters (
                id TEXT PRIMARY KEY,
                theme TEXT NOT NULL,
                summary TEXT NOT NULL,
                signal_ids TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                average_score REAL NOT NULL,
                top_examples TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_clusters(self, clusters: list[SignalCluster]) -> int:
        saved_count = 0
        seen_ids: set[str] = set()
        for cluster in clusters:
            if cluster.id in seen_ids:
                continue
            seen_ids.add(cluster.id)
            cursor = self.connection.execute(
                """
                INSERT INTO clusters (
                    id, theme, summary, signal_ids, frequency,
                    average_score, top_examples
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    theme = excluded.theme,
                    summary = excluded.summary,
                    signal_ids = excluded.signal_ids,
                    frequency = excluded.frequency,
                    average_score = excluded.average_score,
                    top_examples = excluded.top_examples
                """,
                (
                    cluster.id,
                    cluster.theme,
                    cluster.summary,
                    _to_json(cluster.signal_ids),
                    cluster.frequency,
                    cluster.average_score,
                    _to_json(cluster.top_examples),
                ),
            )
            saved_count += cursor.rowcount
        self.connection.commit()
        return saved_count

    def get_cluster(self, cluster_id: str) -> SignalCluster | None:
        row = self.connection.execute(
            "SELECT * FROM clusters WHERE id = ?",
            (cluster_id,),
        ).fetchone()
        return _cluster_from_row(row) if row else None

    def list_clusters(self) -> list[SignalCluster]:
        rows = self.connection.execute("SELECT * FROM clusters ORDER BY id").fetchall()
        return [_cluster_from_row(row) for row in rows]


class SQLiteOpportunityRepository(_SQLiteRepository, OpportunityRepository):
    """SQLite-backed synthesized opportunity repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                cluster_id TEXT,
                title TEXT NOT NULL,
                target_user TEXT NOT NULL,
                pain_summary TEXT NOT NULL,
                why_it_matters TEXT NOT NULL,
                suggested_wedge TEXT NOT NULL,
                evidence_count INTEGER NOT NULL,
                confidence REAL NOT NULL,
                evidence_signal_ids TEXT NOT NULL,
                unmet_need_type TEXT,
                source_theme_id TEXT
            )
            """
        )
        _ensure_sqlite_column(
            self.connection,
            "opportunities",
            "unmet_need_type",
            "TEXT",
        )
        _ensure_sqlite_column(
            self.connection,
            "opportunities",
            "source_theme_id",
            "TEXT",
        )
        self.connection.commit()

    def save_opportunities(self, opportunities: list[Opportunity]) -> int:
        saved_count = 0
        seen_ids: set[str] = set()
        for opportunity in opportunities:
            if opportunity.id in seen_ids:
                continue
            seen_ids.add(opportunity.id)
            cursor = self.connection.execute(
                """
                INSERT INTO opportunities (
                    id, cluster_id, title, target_user, pain_summary,
                    why_it_matters, suggested_wedge, evidence_count,
                    confidence, evidence_signal_ids, unmet_need_type,
                    source_theme_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    cluster_id = excluded.cluster_id,
                    title = excluded.title,
                    target_user = excluded.target_user,
                    pain_summary = excluded.pain_summary,
                    why_it_matters = excluded.why_it_matters,
                    suggested_wedge = excluded.suggested_wedge,
                    evidence_count = excluded.evidence_count,
                    confidence = excluded.confidence,
                    evidence_signal_ids = excluded.evidence_signal_ids,
                    unmet_need_type = excluded.unmet_need_type,
                    source_theme_id = excluded.source_theme_id
                """,
                (
                    opportunity.id,
                    opportunity.cluster_id,
                    opportunity.title,
                    opportunity.target_user,
                    opportunity.pain_summary,
                    opportunity.why_it_matters,
                    opportunity.suggested_wedge,
                    opportunity.evidence_count,
                    opportunity.confidence,
                    _to_json(opportunity.evidence_signal_ids),
                    opportunity.unmet_need_type,
                    opportunity.source_theme_id,
                ),
            )
            saved_count += cursor.rowcount
        self.connection.commit()
        return saved_count

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        row = self.connection.execute(
            "SELECT * FROM opportunities WHERE id = ?",
            (opportunity_id,),
        ).fetchone()
        return _opportunity_from_row(row) if row else None

    def list_opportunities(self) -> list[Opportunity]:
        rows = self.connection.execute(
            "SELECT * FROM opportunities ORDER BY id"
        ).fetchall()
        return [_opportunity_from_row(row) for row in rows]


class SQLiteAgentPreferencesRepository(_SQLiteRepository, AgentPreferencesRepository):
    """SQLite-backed agent preferences repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_preferences (
                user_niche_id TEXT PRIMARY KEY,
                preferred_source_families TEXT NOT NULL,
                ignored_themes TEXT NOT NULL,
                ignored_categories TEXT NOT NULL,
                muted_source_ids TEXT NOT NULL,
                extra_instructions TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_agent_preferences(self, preferences: AgentPreferences) -> bool:
        self.connection.execute(
            """
            INSERT INTO agent_preferences (
                user_niche_id, preferred_source_families, ignored_themes,
                ignored_categories, muted_source_ids, extra_instructions,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_niche_id) DO UPDATE SET
                preferred_source_families = excluded.preferred_source_families,
                ignored_themes = excluded.ignored_themes,
                ignored_categories = excluded.ignored_categories,
                muted_source_ids = excluded.muted_source_ids,
                extra_instructions = excluded.extra_instructions,
                updated_at = excluded.updated_at
            """,
            _agent_preferences_values(preferences, sqlite=True),
        )
        self.connection.commit()
        return True

    def get_agent_preferences(self, user_niche_id: str) -> AgentPreferences | None:
        row = self.connection.execute(
            "SELECT * FROM agent_preferences WHERE user_niche_id = ?",
            (user_niche_id,),
        ).fetchone()
        return _agent_preferences_from_row(row) if row else None

    def delete_agent_preferences(self, user_niche_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM agent_preferences WHERE user_niche_id = ?",
            (user_niche_id,),
        )
        self.connection.commit()
        return cursor.rowcount > 0


class SQLiteAgentFeedbackRepository(_SQLiteRepository, AgentFeedbackRepository):
    """SQLite-backed agent feedback repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_feedback (
                id TEXT PRIMARY KEY,
                user_niche_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_agent_feedback(self, feedback: AgentFeedback) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO agent_feedback (
                id, user_niche_id, opportunity_id, action, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            _agent_feedback_values(feedback, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_agent_feedback(
        self,
        *,
        user_niche_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        query = "SELECT * FROM agent_feedback"
        clauses: list[str] = []
        params: list[str] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = ?")
            params.append(user_niche_id)
        if opportunity_id is not None:
            clauses.append("opportunity_id = ?")
            params.append(opportunity_id)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_feedback_from_row(row) for row in rows]


class SQLiteAgentActivityRepository(_SQLiteRepository, AgentActivityRepository):
    """SQLite-backed agent activity repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_activity (
                id TEXT PRIMARY KEY,
                user_niche_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_agent_activity(self, activity: AgentActivity) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO agent_activity (
                id, user_niche_id, event_type, title, detail, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _agent_activity_values(activity, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_agent_activity(
        self,
        *,
        user_niche_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentActivity]:
        query = "SELECT * FROM agent_activity"
        clauses: list[str] = []
        params: list[str | int] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = ?")
            params.append(user_niche_id)
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_activity_from_row(row) for row in rows]


class SQLiteAgentAlertRepository(_SQLiteRepository, AgentAlertRepository):
    """SQLite-backed agent alert repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_alerts (
                id TEXT PRIMARY KEY,
                user_niche_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                detail TEXT,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                acknowledged_at TEXT
            )
            """
        )
        self.connection.commit()

    def save_agent_alert(self, alert: AgentAlert) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO agent_alerts (
                id, user_niche_id, alert_type, title, severity, status, detail,
                metadata, created_at, acknowledged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _agent_alert_values(alert, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def get_agent_alert(self, alert_id: str) -> AgentAlert | None:
        row = self.connection.execute(
            "SELECT * FROM agent_alerts WHERE id = ?",
            (alert_id,),
        ).fetchone()
        return _agent_alert_from_row(row) if row else None

    def list_agent_alerts(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAlert]:
        query = "SELECT * FROM agent_alerts"
        clauses: list[str] = []
        params: list[str | int] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = ?")
            params.append(user_niche_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_alert_from_row(row) for row in rows]

    def acknowledge_agent_alert(self, alert_id: str) -> AgentAlert | None:
        alert = self.get_agent_alert(alert_id)
        if alert is None:
            return None
        acknowledged = alert.acknowledge()
        self.connection.execute(
            """
            UPDATE agent_alerts
            SET status = ?, acknowledged_at = ?
            WHERE id = ?
            """,
            (
                acknowledged.status,
                _datetime_to_text(acknowledged.acknowledged_at),
                alert_id,
            ),
        )
        self.connection.commit()
        return acknowledged


class SQLiteAgentFollowUpRepository(_SQLiteRepository, AgentFollowUpRepository):
    """SQLite-backed agent follow-up repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_follow_ups (
                id TEXT PRIMARY KEY,
                user_niche_id TEXT NOT NULL,
                question TEXT NOT NULL,
                opportunity_id TEXT,
                cluster_id TEXT,
                status TEXT NOT NULL,
                response TEXT,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_agent_follow_up(self, follow_up: AgentFollowUp) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO agent_follow_ups (
                id, user_niche_id, question, opportunity_id, cluster_id, status,
                response, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _agent_follow_up_values(follow_up, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_agent_follow_ups(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentFollowUp]:
        query = "SELECT * FROM agent_follow_ups"
        clauses: list[str] = []
        params: list[str | int] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = ?")
            params.append(user_niche_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_follow_up_from_row(row) for row in rows]

    def update_agent_follow_up(
        self,
        follow_up_id: str,
        *,
        status: str,
        response: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentFollowUp | None:
        row = self.connection.execute(
            "SELECT * FROM agent_follow_ups WHERE id = ?",
            (follow_up_id,),
        ).fetchone()
        if row is None:
            return None
        updated = _updated_agent_follow_up(
            _agent_follow_up_from_row(row),
            status=status,
            response=response,
            metadata=metadata,
        )
        if updated is None:
            return None
        self.connection.execute(
            """
            UPDATE agent_follow_ups
            SET status = ?, response = ?, metadata = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated.status,
                updated.response,
                _to_json(updated.metadata),
                _datetime_to_text(updated.updated_at),
                updated.id,
            ),
        )
        self.connection.commit()
        return updated


class SQLitePipelineRunMetricsRepository(
    _SQLiteRepository,
    PipelineRunMetricsRepository,
):
    """SQLite-backed pipeline run metrics repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_run_metrics (
                id TEXT PRIMARY KEY,
                ran_at TEXT NOT NULL,
                fetched_count INTEGER NOT NULL,
                fetch_failed_count INTEGER NOT NULL,
                rule_filtered_count INTEGER NOT NULL,
                llm_filtered_count INTEGER NOT NULL,
                relevance_failed_count INTEGER NOT NULL,
                extraction_attempted_count INTEGER NOT NULL,
                extracted_count INTEGER NOT NULL,
                no_signal_count INTEGER NOT NULL,
                extraction_failed_count INTEGER NOT NULL,
                signal_inserted_count INTEGER NOT NULL,
                scored_count INTEGER NOT NULL,
                scoring_failed_count INTEGER NOT NULL,
                average_score REAL NOT NULL,
                embedding_failed_count INTEGER NOT NULL,
                clustered_count INTEGER NOT NULL,
                cluster_inserted_count INTEGER NOT NULL,
                opportunity_synthesized_count INTEGER NOT NULL,
                opportunity_inserted_count INTEGER NOT NULL,
                opportunity_failed_count INTEGER NOT NULL,
                email_sent INTEGER NOT NULL,
                email_error TEXT
            )
            """
        )
        self.connection.commit()

    def save_pipeline_run_metrics(self, metrics: PipelineRunMetrics) -> bool:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO pipeline_run_metrics (
                id, ran_at, fetched_count, fetch_failed_count,
                rule_filtered_count, llm_filtered_count, relevance_failed_count,
                extraction_attempted_count, extracted_count, no_signal_count,
                extraction_failed_count, signal_inserted_count, scored_count,
                scoring_failed_count, average_score, embedding_failed_count,
                clustered_count, cluster_inserted_count,
                opportunity_synthesized_count, opportunity_inserted_count,
                opportunity_failed_count, email_sent, email_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _pipeline_run_metrics_values(metrics, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_pipeline_run_metrics(self) -> list[PipelineRunMetrics]:
        rows = self.connection.execute(
            "SELECT * FROM pipeline_run_metrics ORDER BY ran_at, id"
        ).fetchall()
        return [_pipeline_run_metrics_from_row(row) for row in rows]


class SQLiteSourceLocatorRepository(_SQLiteRepository, SourceLocatorRepository):
    """SQLite-backed source locator repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_locators (
                id TEXT PRIMARY KEY,
                locator TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL,
                limit_value INTEGER,
                options TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_source_locators(self, locators: list[SourceLocator]) -> int:
        inserted_count = 0
        for locator in locators:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO source_locators (
                    id, locator, enabled, limit_value, options
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    locator.id,
                    locator.locator,
                    _bool_to_int(locator.enabled),
                    locator.limit,
                    _to_json(locator.options),
                ),
            )
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

    def get_source_locator(self, locator_id: str) -> SourceLocator | None:
        row = self.connection.execute(
            "SELECT * FROM source_locators WHERE id = ?",
            (locator_id,),
        ).fetchone()
        return _source_locator_from_row(row) if row else None

    def list_source_locators(self, enabled: bool | None = None) -> list[SourceLocator]:
        if enabled is None:
            rows = self.connection.execute(
                "SELECT * FROM source_locators ORDER BY id"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM source_locators WHERE enabled = ? ORDER BY id",
                (_bool_to_int(enabled),),
            ).fetchall()
        return [_source_locator_from_row(row) for row in rows]


class _PostgresRepository:
    """Shared Postgres connection handling."""

    def __init__(
        self,
        database_url: str | None = None,
        *,
        connection: Any | None = None,
    ):
        if connection is None:
            if not database_url:
                raise ValueError("database_url is required")
            self.connection = _connect_postgres(database_url)
            self._owns_connection = True
        else:
            self.connection = connection
            self._owns_connection = False

    def close(self) -> None:
        if self._owns_connection:
            self.connection.close()


class PostgresPostRepository(_PostgresRepository, PostRepository):
    """Postgres-backed raw post repository."""

    def save_posts(self, posts: list[RawPost]) -> int:
        inserted_count = 0
        for post in posts:
            cursor = self.connection.execute(
                """
                INSERT INTO posts (
                    id, source, source_id, title, body, author, url,
                    created_at, upvotes, comments_count, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                )
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    post.id,
                    post.source,
                    post.source_id,
                    post.title,
                    post.body,
                    post.author,
                    post.url,
                    post.created_at,
                    post.upvotes,
                    post.comments_count,
                    _to_json(post.metadata),
                ),
            )
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

    def get_post(self, post_id: str) -> RawPost | None:
        row = self.connection.execute(
            "SELECT * FROM posts WHERE id = %s",
            (post_id,),
        ).fetchone()
        return _post_from_row(row) if row else None

    def list_posts(self) -> list[RawPost]:
        rows = self.connection.execute("SELECT * FROM posts ORDER BY id").fetchall()
        return [_post_from_row(row) for row in rows]


class PostgresSignalRepository(_PostgresRepository, SignalRepository):
    """Postgres-backed signal repository."""

    def save_signals(self, signals: list[Signal]) -> int:
        inserted_count = 0
        for signal in signals:
            cursor = self.connection.execute(
                """
                INSERT INTO signals (
                    id, post_id, pain, user_type, job_to_be_done,
                    current_workaround, urgency, severity, willingness_to_pay,
                    category, confidence
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    signal.id,
                    signal.post_id,
                    signal.pain,
                    signal.user_type,
                    signal.job_to_be_done,
                    signal.current_workaround,
                    signal.urgency,
                    signal.severity,
                    signal.willingness_to_pay,
                    signal.category,
                    signal.confidence,
                ),
            )
            inserted_count += _rowcount(cursor)
            self._save_signal_evidence(signal)
        self.connection.commit()
        return inserted_count

    def get_signal(self, signal_id: str) -> Signal | None:
        row = self.connection.execute(
            """
            SELECT
                s.*,
                e.niche_company_id,
                e.niche_id,
                e.evidence_url,
                e.evidence_text,
                e.detected_at
            FROM signals s
            LEFT JOIN signal_evidence e ON e.signal_id = s.id
            WHERE s.id = %s
            """,
            (signal_id,),
        ).fetchone()
        return _signal_from_row(row) if row else None

    def delete_signal(self, signal_id: str) -> bool:
        self.connection.execute(
            "DELETE FROM signal_evidence WHERE signal_id = %s",
            (signal_id,),
        )
        cursor = self.connection.execute(
            "DELETE FROM signals WHERE id = %s",
            (signal_id,),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_signals(self) -> list[Signal]:
        rows = self.connection.execute(
            """
            SELECT
                s.*,
                e.niche_company_id,
                e.niche_id,
                e.evidence_url,
                e.evidence_text,
                e.detected_at
            FROM signals s
            LEFT JOIN signal_evidence e ON e.signal_id = s.id
            ORDER BY s.id
            """
        ).fetchall()
        return [_signal_from_row(row) for row in rows]

    def _save_signal_evidence(self, signal: Signal) -> None:
        if not any(
            [
                signal.niche_company_id,
                signal.niche_id,
                signal.evidence_url,
                signal.evidence_text,
                signal.detected_at,
            ]
        ):
            return

        self.connection.execute(
            """
            INSERT INTO signal_evidence (
                signal_id, niche_company_id, niche_id, evidence_url,
                evidence_text, detected_at
            ) VALUES (%s, %s::uuid, %s::uuid, %s, %s, %s)
            ON CONFLICT (signal_id) DO UPDATE SET
                niche_company_id = EXCLUDED.niche_company_id,
                niche_id = EXCLUDED.niche_id,
                evidence_url = EXCLUDED.evidence_url,
                evidence_text = EXCLUDED.evidence_text,
                detected_at = EXCLUDED.detected_at,
                updated_at = now()
            """,
            (
                signal.id,
                signal.niche_company_id,
                signal.niche_id,
                signal.evidence_url,
                signal.evidence_text,
                signal.detected_at or datetime.now(tz=UTC),
            ),
        )


class PostgresScoreRepository(_PostgresRepository, ScoreRepository):
    """Postgres-backed opportunity score repository."""

    def save_scores(self, scores: list[OpportunityScore]) -> int:
        inserted_count = 0
        for score in scores:
            cursor = self.connection.execute(
                """
                INSERT INTO scores (
                    signal_id, total_score, urgency_score, severity_score,
                    willingness_score, confidence_score, reasoning
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (signal_id) DO NOTHING
                """,
                (
                    score.signal_id,
                    score.total_score,
                    score.urgency_score,
                    score.severity_score,
                    score.willingness_score,
                    score.confidence_score,
                    score.reasoning,
                ),
            )
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

    def get_score(self, signal_id: str) -> OpportunityScore | None:
        row = self.connection.execute(
            "SELECT * FROM scores WHERE signal_id = %s",
            (signal_id,),
        ).fetchone()
        return _score_from_row(row) if row else None

    def delete_score(self, signal_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM scores WHERE signal_id = %s",
            (signal_id,),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_scores(self) -> list[OpportunityScore]:
        rows = self.connection.execute("SELECT * FROM scores ORDER BY signal_id").fetchall()
        return [_score_from_row(row) for row in rows]


class PostgresClusterRepository(_PostgresRepository, ClusterRepository):
    """Postgres-backed signal cluster repository."""

    def save_clusters(self, clusters: list[SignalCluster]) -> int:
        saved_count = 0
        seen_ids: set[str] = set()
        for cluster in clusters:
            if cluster.id in seen_ids:
                continue
            seen_ids.add(cluster.id)
            cursor = self.connection.execute(
                """
                INSERT INTO clusters (
                    id, theme, summary, signal_ids, frequency,
                    average_score, top_examples
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    theme = EXCLUDED.theme,
                    summary = EXCLUDED.summary,
                    signal_ids = EXCLUDED.signal_ids,
                    frequency = EXCLUDED.frequency,
                    average_score = EXCLUDED.average_score,
                    top_examples = EXCLUDED.top_examples,
                    updated_at = now()
                """,
                (
                    cluster.id,
                    cluster.theme,
                    cluster.summary,
                    cluster.signal_ids,
                    cluster.frequency,
                    cluster.average_score,
                    cluster.top_examples,
                ),
            )
            saved_count += _rowcount(cursor)
        self.connection.commit()
        return saved_count

    def get_cluster(self, cluster_id: str) -> SignalCluster | None:
        row = self.connection.execute(
            "SELECT * FROM clusters WHERE id = %s",
            (cluster_id,),
        ).fetchone()
        return _cluster_from_row(row) if row else None

    def list_clusters(self) -> list[SignalCluster]:
        rows = self.connection.execute("SELECT * FROM clusters ORDER BY id").fetchall()
        return [_cluster_from_row(row) for row in rows]


class PostgresOpportunityRepository(_PostgresRepository, OpportunityRepository):
    """Postgres-backed synthesized opportunity repository."""

    def save_opportunities(self, opportunities: list[Opportunity]) -> int:
        saved_count = 0
        seen_ids: set[str] = set()
        for opportunity in opportunities:
            if opportunity.id in seen_ids:
                continue
            seen_ids.add(opportunity.id)
            cursor = self.connection.execute(
                """
                INSERT INTO opportunities (
                    id, cluster_id, title, target_user, pain_summary,
                    why_it_matters, suggested_wedge, evidence_count,
                    confidence, evidence_signal_ids, unmet_need_type,
                    source_theme_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::uuid)
                ON CONFLICT (id) DO UPDATE SET
                    cluster_id = EXCLUDED.cluster_id,
                    title = EXCLUDED.title,
                    target_user = EXCLUDED.target_user,
                    pain_summary = EXCLUDED.pain_summary,
                    why_it_matters = EXCLUDED.why_it_matters,
                    suggested_wedge = EXCLUDED.suggested_wedge,
                    evidence_count = EXCLUDED.evidence_count,
                    confidence = EXCLUDED.confidence,
                    evidence_signal_ids = EXCLUDED.evidence_signal_ids,
                    unmet_need_type = EXCLUDED.unmet_need_type,
                    source_theme_id = EXCLUDED.source_theme_id,
                    updated_at = now()
                """,
                (
                    opportunity.id,
                    opportunity.cluster_id,
                    opportunity.title,
                    opportunity.target_user,
                    opportunity.pain_summary,
                    opportunity.why_it_matters,
                    opportunity.suggested_wedge,
                    opportunity.evidence_count,
                    opportunity.confidence,
                    _to_json(opportunity.evidence_signal_ids),
                    opportunity.unmet_need_type,
                    opportunity.source_theme_id,
                ),
            )
            saved_count += _rowcount(cursor)
        self.connection.commit()
        return saved_count

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        row = self.connection.execute(
            "SELECT * FROM opportunities WHERE id = %s",
            (opportunity_id,),
        ).fetchone()
        return _opportunity_from_row(row) if row else None

    def list_opportunities(self) -> list[Opportunity]:
        rows = self.connection.execute(
            "SELECT * FROM opportunities ORDER BY id"
        ).fetchall()
        return [_opportunity_from_row(row) for row in rows]


class PostgresFindingRepository(_PostgresRepository, FindingRepository):
    """Postgres-backed accumulated finding repository."""

    def save_findings(self, findings: list[Finding]) -> int:
        saved_count = 0
        seen_keys: set[tuple[str, str]] = set()
        for finding in findings:
            dedupe_key = (finding.user_niche_id, finding.post_id)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            cursor = self.connection.execute(
                """
                INSERT INTO findings (
                    id, user_niche_id, niche_id, source_id, company_id,
                    post_id, post_title, source_url, evidence_url,
                    evidence_text, pain, affected_user, job_to_be_done,
                    current_workaround, category, urgency, severity,
                    willingness_to_pay, confidence, detected_at, extracted_at,
                    pipeline_run_id, structured_embedding_text, embedding,
                    metadata
                ) VALUES (
                    %s::uuid, %s::uuid, %s::uuid, %s::uuid, %s::uuid,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s::extensions.vector,
                    %s::jsonb
                )
                ON CONFLICT (user_niche_id, post_id) DO UPDATE SET
                    niche_id = EXCLUDED.niche_id,
                    source_id = EXCLUDED.source_id,
                    company_id = EXCLUDED.company_id,
                    post_title = EXCLUDED.post_title,
                    source_url = EXCLUDED.source_url,
                    evidence_url = EXCLUDED.evidence_url,
                    evidence_text = EXCLUDED.evidence_text,
                    pain = EXCLUDED.pain,
                    affected_user = EXCLUDED.affected_user,
                    job_to_be_done = EXCLUDED.job_to_be_done,
                    current_workaround = EXCLUDED.current_workaround,
                    category = EXCLUDED.category,
                    urgency = EXCLUDED.urgency,
                    severity = EXCLUDED.severity,
                    willingness_to_pay = EXCLUDED.willingness_to_pay,
                    confidence = EXCLUDED.confidence,
                    detected_at = EXCLUDED.detected_at,
                    extracted_at = EXCLUDED.extracted_at,
                    pipeline_run_id = EXCLUDED.pipeline_run_id,
                    structured_embedding_text = EXCLUDED.structured_embedding_text,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """,
                _finding_values(finding),
            )
            saved_count += _rowcount(cursor)
        self.connection.commit()
        return saved_count

    def get_seen_post_ids(
        self,
        user_niche_id: str,
        post_ids: list[str],
    ) -> set[str]:
        if not post_ids:
            return set()
        cursor = self.connection.execute(
            """
            SELECT post_id FROM findings
            WHERE user_niche_id = %s::uuid AND post_id = ANY(%s)
            """,
            (user_niche_id, post_ids),
        )
        return {row["post_id"] for row in cursor.fetchall()}

    def list_findings(
        self,
        *,
        user_niche_id: str | None = None,
        unassigned_only: bool = False,
    ) -> list[Finding]:
        query = "SELECT f.* FROM findings f"
        clauses: list[str] = []
        params: list[str] = []
        if user_niche_id is not None:
            clauses.append("f.user_niche_id = %s")
            params.append(user_niche_id)
        if unassigned_only:
            clauses.append(
                """
                NOT EXISTS (
                    SELECT 1 FROM theme_findings tf WHERE tf.finding_id = f.id
                )
                """
            )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY f.extracted_at, f.id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_finding_from_row(row) for row in rows]


class PostgresThemeRepository(_PostgresRepository, ThemeRepository):
    """Postgres-backed accumulated theme repository."""

    def save_themes(self, themes: list[Theme]) -> int:
        saved_count = 0
        seen_ids: set[str] = set()
        for theme in themes:
            if theme.id in seen_ids:
                continue
            seen_ids.add(theme.id)
            cursor = self.connection.execute(
                """
                INSERT INTO themes (
                    id, user_niche_id, niche_id, title, summary, status,
                    qualification_reason, finding_count, source_count,
                    company_count, average_confidence, latest_finding_at,
                    last_qualified_at, last_synthesized_at, centroid_embedding,
                    created_at, updated_at, metadata
                ) VALUES (
                    %s::uuid, %s::uuid, %s::uuid, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s::extensions.vector,
                    %s, %s, %s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                    niche_id = EXCLUDED.niche_id,
                    title = EXCLUDED.title,
                    summary = EXCLUDED.summary,
                    status = EXCLUDED.status,
                    qualification_reason = EXCLUDED.qualification_reason,
                    finding_count = EXCLUDED.finding_count,
                    source_count = EXCLUDED.source_count,
                    company_count = EXCLUDED.company_count,
                    average_confidence = EXCLUDED.average_confidence,
                    latest_finding_at = EXCLUDED.latest_finding_at,
                    last_qualified_at = EXCLUDED.last_qualified_at,
                    last_synthesized_at = EXCLUDED.last_synthesized_at,
                    centroid_embedding = EXCLUDED.centroid_embedding,
                    updated_at = EXCLUDED.updated_at,
                    metadata = EXCLUDED.metadata
                """,
                _theme_values(theme),
            )
            saved_count += _rowcount(cursor)
        self.connection.commit()
        return saved_count

    def save_theme_findings(self, assignments: list[ThemeFinding]) -> int:
        saved_count = 0
        seen_keys: set[tuple[str, str]] = set()
        for assignment in assignments:
            key = (assignment.theme_id, assignment.finding_id)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            cursor = self.connection.execute(
                """
                INSERT INTO theme_findings (
                    theme_id, finding_id, assigned_at, assignment_method,
                    similarity_score, llm_decision, metadata
                ) VALUES (
                    %s::uuid, %s::uuid, %s, %s, %s, %s::jsonb, %s::jsonb
                )
                ON CONFLICT (theme_id, finding_id) DO UPDATE SET
                    assignment_method = EXCLUDED.assignment_method,
                    similarity_score = EXCLUDED.similarity_score,
                    llm_decision = EXCLUDED.llm_decision,
                    metadata = EXCLUDED.metadata
                """,
                _theme_finding_values(assignment),
            )
            saved_count += _rowcount(cursor)
        self.connection.commit()
        return saved_count

    def list_themes(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
    ) -> list[Theme]:
        query = "SELECT * FROM themes"
        clauses: list[str] = []
        params: list[str] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = %s")
            params.append(user_niche_id)
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY latest_finding_at DESC NULLS LAST, created_at DESC, id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_theme_from_row(row) for row in rows]

    def list_changed_themes(
        self,
        *,
        user_niche_id: str,
        since: datetime,
    ) -> list[Theme]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM themes
            WHERE user_niche_id = %s
              AND updated_at >= %s
            ORDER BY updated_at DESC, id
            """,
            (user_niche_id, since),
        ).fetchall()
        return [_theme_from_row(row) for row in rows]

    def find_similar_themes(
        self,
        user_niche_id: str,
        embedding: list[float],
        *,
        top_k: int = 5,
        min_similarity: float = 0.70,
    ) -> list[Theme]:
        # pgvector <=> is cosine DISTANCE (0 = identical). Convert similarity
        # threshold to distance threshold: distance = 1 - similarity.
        max_distance = round(1.0 - min_similarity, 6)
        vec = _to_pgvector(embedding)
        if vec is None:
            return []
        rows = self.connection.execute(
            """
            SELECT *
            FROM themes
            WHERE user_niche_id = %s::uuid
              AND centroid_embedding IS NOT NULL
              AND (centroid_embedding <=> %s::extensions.vector) <= %s
            ORDER BY centroid_embedding <=> %s::extensions.vector ASC
            LIMIT %s
            """,
            (user_niche_id, vec, max_distance, vec, top_k),
        ).fetchall()
        return [_theme_from_row(row) for row in rows]

    def list_findings_for_theme(self, theme_id: str) -> list[Finding]:
        rows = self.connection.execute(
            """
            SELECT f.*
            FROM findings f
            JOIN theme_findings tf ON tf.finding_id = f.id
            WHERE tf.theme_id = %s
            ORDER BY tf.assigned_at, f.extracted_at, f.id
            """,
            (theme_id,),
        ).fetchall()
        return [_finding_from_row(row) for row in rows]

    def refresh_theme_rollups(self, theme_ids: list[str]) -> int:
        normalized_ids = [theme_id.strip() for theme_id in theme_ids if theme_id.strip()]
        if not normalized_ids:
            return 0
        cursor = self.connection.execute(
            """
            WITH stats AS (
                SELECT
                    tf.theme_id,
                    count(*)::integer AS finding_count,
                    count(DISTINCT f.source_id)::integer AS source_count,
                    count(DISTINCT f.company_id)::integer AS company_count,
                    coalesce(avg(f.confidence), 0)::double precision AS average_confidence,
                    max(coalesce(f.detected_at, f.extracted_at)) AS latest_finding_at,
                    avg(f.embedding) FILTER (WHERE f.embedding IS NOT NULL) AS centroid_embedding
                FROM theme_findings tf
                JOIN findings f ON f.id = tf.finding_id
                WHERE tf.theme_id = ANY(%s::uuid[])
                GROUP BY tf.theme_id
            )
            UPDATE themes t
            SET
                finding_count = stats.finding_count,
                source_count = stats.source_count,
                company_count = stats.company_count,
                average_confidence = stats.average_confidence,
                latest_finding_at = stats.latest_finding_at,
                centroid_embedding = coalesce(stats.centroid_embedding, t.centroid_embedding),
                updated_at = now()
            FROM stats
            WHERE t.id = stats.theme_id
            """,
            (normalized_ids,),
        )
        self.connection.commit()
        return _rowcount(cursor)


class PostgresAgentPreferencesRepository(
    _PostgresRepository,
    AgentPreferencesRepository,
):
    """Postgres-backed agent preferences repository."""

    def save_agent_preferences(self, preferences: AgentPreferences) -> bool:
        self.connection.execute(
            """
            INSERT INTO agent_preferences (
                user_niche_id, preferred_source_families, ignored_themes,
                ignored_categories, muted_source_ids, extra_instructions,
                created_at, updated_at
            ) VALUES (%s::uuid, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
            ON CONFLICT (user_niche_id) DO UPDATE SET
                preferred_source_families = EXCLUDED.preferred_source_families,
                ignored_themes = EXCLUDED.ignored_themes,
                ignored_categories = EXCLUDED.ignored_categories,
                muted_source_ids = EXCLUDED.muted_source_ids,
                extra_instructions = EXCLUDED.extra_instructions,
                updated_at = EXCLUDED.updated_at
            """,
            _agent_preferences_values(preferences, sqlite=False),
        )
        self.connection.commit()
        return True

    def get_agent_preferences(self, user_niche_id: str) -> AgentPreferences | None:
        row = self.connection.execute(
            "SELECT * FROM agent_preferences WHERE user_niche_id = %s",
            (user_niche_id,),
        ).fetchone()
        return _agent_preferences_from_row(row) if row else None

    def delete_agent_preferences(self, user_niche_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM agent_preferences WHERE user_niche_id = %s",
            (user_niche_id,),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresAgentFeedbackRepository(_PostgresRepository, AgentFeedbackRepository):
    """Postgres-backed agent feedback repository."""

    def save_agent_feedback(self, feedback: AgentFeedback) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO agent_feedback (
                id, user_niche_id, opportunity_id, action, reason, created_at
            ) VALUES (%s, %s::uuid, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            _agent_feedback_values(feedback, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_agent_feedback(
        self,
        *,
        user_niche_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        query = "SELECT * FROM agent_feedback"
        clauses: list[str] = []
        params: list[str] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = %s")
            params.append(user_niche_id)
        if opportunity_id is not None:
            clauses.append("opportunity_id = %s")
            params.append(opportunity_id)
        if action is not None:
            clauses.append("action = %s")
            params.append(action)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_feedback_from_row(row) for row in rows]


class PostgresAgentActivityRepository(_PostgresRepository, AgentActivityRepository):
    """Postgres-backed agent activity repository."""

    def save_agent_activity(self, activity: AgentActivity) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO agent_activity (
                id, user_niche_id, event_type, title, detail, metadata, created_at
            ) VALUES (%s, %s::uuid, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            _agent_activity_values(activity, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_agent_activity(
        self,
        *,
        user_niche_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentActivity]:
        query = "SELECT * FROM agent_activity"
        clauses: list[str] = []
        params: list[str | int] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = %s")
            params.append(user_niche_id)
        if event_type is not None:
            clauses.append("event_type = %s")
            params.append(event_type)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_activity_from_row(row) for row in rows]


class PostgresAgentAlertRepository(_PostgresRepository, AgentAlertRepository):
    """Postgres-backed agent alert repository."""

    def save_agent_alert(self, alert: AgentAlert) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO agent_alerts (
                id, user_niche_id, alert_type, title, severity, status, detail,
                metadata, created_at, acknowledged_at
            ) VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            _agent_alert_values(alert, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def get_agent_alert(self, alert_id: str) -> AgentAlert | None:
        row = self.connection.execute(
            "SELECT * FROM agent_alerts WHERE id = %s",
            (alert_id,),
        ).fetchone()
        return _agent_alert_from_row(row) if row else None

    def list_agent_alerts(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAlert]:
        query = "SELECT * FROM agent_alerts"
        clauses: list[str] = []
        params: list[str | int] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = %s")
            params.append(user_niche_id)
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_alert_from_row(row) for row in rows]

    def acknowledge_agent_alert(self, alert_id: str) -> AgentAlert | None:
        alert = self.get_agent_alert(alert_id)
        if alert is None:
            return None
        acknowledged = alert.acknowledge()
        self.connection.execute(
            """
            UPDATE agent_alerts
            SET status = %s, acknowledged_at = %s
            WHERE id = %s
            """,
            (acknowledged.status, acknowledged.acknowledged_at, alert_id),
        )
        self.connection.commit()
        return acknowledged


class PostgresAgentFollowUpRepository(_PostgresRepository, AgentFollowUpRepository):
    """Postgres-backed agent follow-up repository."""

    def save_agent_follow_up(self, follow_up: AgentFollowUp) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO agent_follow_ups (
                id, user_niche_id, question, opportunity_id, cluster_id, status,
                response, metadata, created_at, updated_at
            ) VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            _agent_follow_up_values(follow_up, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_agent_follow_ups(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentFollowUp]:
        query = "SELECT * FROM agent_follow_ups"
        clauses: list[str] = []
        params: list[str | int] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = %s")
            params.append(user_niche_id)
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_follow_up_from_row(row) for row in rows]

    def update_agent_follow_up(
        self,
        follow_up_id: str,
        *,
        status: str,
        response: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentFollowUp | None:
        row = self.connection.execute(
            "SELECT * FROM agent_follow_ups WHERE id = %s",
            (follow_up_id,),
        ).fetchone()
        if row is None:
            return None
        updated = _updated_agent_follow_up(
            _agent_follow_up_from_row(row),
            status=status,
            response=response,
            metadata=metadata,
        )
        if updated is None:
            return None
        self.connection.execute(
            """
            UPDATE agent_follow_ups
            SET status = %s, response = %s, metadata = %s::jsonb, updated_at = %s
            WHERE id = %s
            """,
            (
                updated.status,
                updated.response,
                _to_json(updated.metadata),
                updated.updated_at,
                updated.id,
            ),
        )
        self.connection.commit()
        return updated


class PostgresAgentActionRepository(_PostgresRepository, AgentActionRepository):
    """Postgres-backed planned agent action repository."""

    def save_agent_action(self, action: AgentAction) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO agent_actions (
                id, user_niche_id, action_type, status, reason, metadata,
                created_at, completed_at
            ) VALUES (%s, %s::uuid, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                reason = EXCLUDED.reason,
                metadata = EXCLUDED.metadata,
                completed_at = EXCLUDED.completed_at
            """,
            _agent_action_values(action, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_agent_actions(
        self,
        *,
        user_niche_id: str | None = None,
        status: str | None = None,
        action_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAction]:
        query = "SELECT * FROM agent_actions"
        clauses: list[str] = []
        params: list[str | int] = []
        if user_niche_id is not None:
            clauses.append("user_niche_id = %s")
            params.append(user_niche_id)
        if status is not None:
            clauses.append("status = %s")
            params.append(status)
        if action_type is not None:
            clauses.append("action_type = %s")
            params.append(action_type)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_agent_action_from_row(row) for row in rows]

    def update_agent_action_status(
        self,
        action_id: str,
        status: str,
    ) -> AgentAction | None:
        existing = self.connection.execute(
            "SELECT * FROM agent_actions WHERE id = %s",
            (action_id,),
        ).fetchone()
        if existing is None:
            return None
        completed_at = (
            datetime.now(tz=UTC)
            if status in {"completed", "failed", "dismissed"}
            else None
        )
        self.connection.execute(
            """
            UPDATE agent_actions
            SET status = %s, completed_at = %s
            WHERE id = %s
            """,
            (status, completed_at, action_id),
        )
        self.connection.commit()
        row = self.connection.execute(
            "SELECT * FROM agent_actions WHERE id = %s",
            (action_id,),
        ).fetchone()
        return _agent_action_from_row(row) if row else None


class PostgresPipelineRunMetricsRepository(
    _PostgresRepository,
    PipelineRunMetricsRepository,
):
    """Postgres-backed pipeline run metrics repository."""

    def save_pipeline_run_metrics(self, metrics: PipelineRunMetrics) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO pipeline_run_metrics (
                id, ran_at, fetched_count, fetch_failed_count,
                rule_filtered_count, llm_filtered_count, relevance_failed_count,
                extraction_attempted_count, extracted_count, no_signal_count,
                extraction_failed_count, signal_inserted_count, scored_count,
                scoring_failed_count, average_score, embedding_failed_count,
                clustered_count, cluster_inserted_count,
                opportunity_synthesized_count, opportunity_inserted_count,
                opportunity_failed_count, email_sent, email_error
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            _pipeline_run_metrics_values(metrics, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_pipeline_run_metrics(self) -> list[PipelineRunMetrics]:
        rows = self.connection.execute(
            "SELECT * FROM pipeline_run_metrics ORDER BY ran_at, id"
        ).fetchall()
        return [_pipeline_run_metrics_from_row(row) for row in rows]


class PostgresSourceLocatorRepository(_PostgresRepository, SourceLocatorRepository):
    """Postgres-backed source locator repository."""

    def save_source_locators(self, locators: list[SourceLocator]) -> int:
        inserted_count = 0
        for locator in locators:
            cursor = self.connection.execute(
                """
                INSERT INTO source_locators (
                    id, locator, enabled, limit_value, options
                ) VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    locator.id,
                    locator.locator,
                    locator.enabled,
                    locator.limit,
                    _to_json(locator.options),
                ),
            )
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

    def get_source_locator(self, locator_id: str) -> SourceLocator | None:
        row = self.connection.execute(
            "SELECT * FROM source_locators WHERE id = %s",
            (locator_id,),
        ).fetchone()
        return _source_locator_from_row(row) if row else None

    def list_source_locators(self, enabled: bool | None = None) -> list[SourceLocator]:
        if enabled is None:
            rows = self.connection.execute(
                "SELECT * FROM source_locators ORDER BY id"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM source_locators WHERE enabled = %s ORDER BY id",
                (enabled,),
            ).fetchall()
        return [_source_locator_from_row(row) for row in rows]


def connect_postgres(database_url: str) -> Any:
    """Create a Postgres connection for repository wiring."""
    return _connect_postgres(database_url)


def _connect_postgres(database_url: str) -> Any:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg[binary] is required for Supabase Postgres") from exc

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        autocommit=True,
        # Supabase transaction pooling does not support session-pinned prepared
        # statements reliably. Keep psycopg from auto-preparing statements.
        prepare_threshold=None,
    )


def _rowcount(cursor: Any) -> int:
    rowcount = getattr(cursor, "rowcount", 0)
    return rowcount if rowcount and rowcount > 0 else 0


def _to_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _from_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return json.loads(value)


def _to_pgvector(value: list[float] | None) -> str | None:
    if value is None:
        return None
    return "[" + ",".join(str(float(item)) for item in value) + "]"


def _vector_from_row(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, tuple):
        return [float(item) for item in value]
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1]
        if not cleaned:
            return []
        return [float(item.strip()) for item in cleaned.split(",")]
    return [float(item) for item in value]


def _datetime_to_text(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_from_text(value: datetime | str | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value) if value else None


def _bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _bool_from_int(value: bool | int | None) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return bool(value)


def _float(value: Any) -> float:
    return float(value)


def _post_from_row(row: sqlite3.Row) -> RawPost:
    return RawPost.create(
        source=row["source"],
        source_id=row["source_id"],
        title=row["title"],
        body=row["body"],
        author=row["author"],
        url=row["url"],
        created_at=_datetime_from_text(row["created_at"]),
        upvotes=row["upvotes"],
        comments_count=row["comments_count"],
        metadata=_from_json(row["metadata"]),
    )


def _signal_from_row(row: sqlite3.Row) -> Signal:
    return Signal.create(
        id=row["id"],
        post_id=row["post_id"],
        pain=row["pain"],
        user_type=row["user_type"],
        job_to_be_done=row["job_to_be_done"],
        current_workaround=row["current_workaround"],
        urgency=row["urgency"],
        severity=row["severity"],
        willingness_to_pay=_bool_from_int(row["willingness_to_pay"]),
        category=row["category"],
        confidence=_float(row["confidence"]),
        niche_company_id=_row_get(row, "niche_company_id"),
        niche_id=_row_get(row, "niche_id"),
        evidence_url=_row_get(row, "evidence_url"),
        evidence_text=_row_get(row, "evidence_text"),
        detected_at=_datetime_from_text(_row_get(row, "detected_at")),
    )


def _score_from_row(row: sqlite3.Row) -> OpportunityScore:
    return OpportunityScore(
        signal_id=row["signal_id"],
        total_score=_float(row["total_score"]),
        urgency_score=_float(row["urgency_score"]),
        severity_score=_float(row["severity_score"]),
        willingness_score=_float(row["willingness_score"]),
        confidence_score=_float(row["confidence_score"]),
        reasoning=row["reasoning"],
    )


def _cluster_from_row(row: sqlite3.Row) -> SignalCluster:
    return SignalCluster.create(
        id=row["id"],
        theme=row["theme"],
        summary=row["summary"],
        signal_ids=_from_json(row["signal_ids"]),
        frequency=row["frequency"],
        average_score=_float(row["average_score"]),
        top_examples=_from_json(row["top_examples"]),
    )


def _opportunity_from_row(row: sqlite3.Row) -> Opportunity:
    return Opportunity.create(
        id=row["id"],
        cluster_id=row["cluster_id"],
        title=row["title"],
        target_user=row["target_user"],
        pain_summary=row["pain_summary"],
        why_it_matters=row["why_it_matters"],
        suggested_wedge=row["suggested_wedge"],
        evidence_count=row["evidence_count"],
        confidence=_float(row["confidence"]),
        evidence_signal_ids=_from_json(row["evidence_signal_ids"]),
        unmet_need_type=_row_get(row, "unmet_need_type"),
        source_theme_id=_row_get(row, "source_theme_id"),
    )


def _finding_values(finding: Finding) -> tuple:
    return (
        finding.id,
        finding.user_niche_id,
        finding.niche_id,
        finding.source_id,
        finding.company_id,
        finding.post_id,
        finding.post_title,
        finding.source_url,
        finding.evidence_url,
        finding.evidence_text,
        finding.pain,
        finding.affected_user,
        finding.job_to_be_done,
        finding.current_workaround,
        finding.category,
        finding.urgency,
        finding.severity,
        finding.willingness_to_pay,
        finding.confidence,
        finding.detected_at,
        finding.extracted_at,
        finding.pipeline_run_id,
        finding.structured_embedding_text,
        _to_pgvector(finding.embedding),
        _to_json(finding.metadata),
    )


def _finding_from_row(row: sqlite3.Row) -> Finding:
    return Finding.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        niche_id=str(row["niche_id"]) if row["niche_id"] else None,
        source_id=str(row["source_id"]) if row["source_id"] else None,
        company_id=str(row["company_id"]) if row["company_id"] else None,
        post_id=row["post_id"],
        post_title=row["post_title"],
        source_url=row["source_url"],
        evidence_url=row["evidence_url"],
        evidence_text=row["evidence_text"],
        pain=row["pain"],
        affected_user=row["affected_user"],
        job_to_be_done=row["job_to_be_done"],
        current_workaround=row["current_workaround"],
        category=row["category"],
        urgency=row["urgency"],
        severity=row["severity"],
        willingness_to_pay=_bool_from_int(row["willingness_to_pay"]),
        confidence=_float(row["confidence"]),
        detected_at=_datetime_from_text(row["detected_at"]),
        extracted_at=_datetime_from_text(row["extracted_at"]),
        pipeline_run_id=row["pipeline_run_id"],
        structured_embedding_text=row["structured_embedding_text"],
        embedding=_vector_from_row(row["embedding"]),
        metadata=_from_json(row["metadata"]),
    )


def _theme_values(theme: Theme) -> tuple:
    return (
        theme.id,
        theme.user_niche_id,
        theme.niche_id,
        theme.title,
        theme.summary,
        theme.status,
        theme.qualification_reason,
        theme.finding_count,
        theme.source_count,
        theme.company_count,
        theme.average_confidence,
        theme.latest_finding_at,
        theme.last_qualified_at,
        theme.last_synthesized_at,
        _to_pgvector(theme.centroid_embedding),
        theme.created_at,
        theme.updated_at,
        _to_json(theme.metadata),
    )


def _theme_from_row(row: sqlite3.Row) -> Theme:
    return Theme.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        niche_id=str(row["niche_id"]) if row["niche_id"] else None,
        title=row["title"],
        summary=row["summary"],
        status=row["status"],
        qualification_reason=row["qualification_reason"],
        finding_count=row["finding_count"],
        source_count=row["source_count"],
        company_count=row["company_count"],
        average_confidence=_float(row["average_confidence"]),
        latest_finding_at=_datetime_from_text(row["latest_finding_at"]),
        last_qualified_at=_datetime_from_text(row["last_qualified_at"]),
        last_synthesized_at=_datetime_from_text(row["last_synthesized_at"]),
        centroid_embedding=_vector_from_row(row["centroid_embedding"]),
        created_at=_datetime_from_text(row["created_at"]),
        updated_at=_datetime_from_text(row["updated_at"]),
        metadata=_from_json(row["metadata"]),
    )


def _theme_finding_values(assignment: ThemeFinding) -> tuple:
    return (
        assignment.theme_id,
        assignment.finding_id,
        assignment.assigned_at,
        assignment.assignment_method,
        assignment.similarity_score,
        _to_json(assignment.llm_decision),
        _to_json(assignment.metadata),
    )


def _agent_action_values(action: AgentAction, *, sqlite: bool) -> tuple:
    return (
        action.id,
        action.user_niche_id,
        action.action_type,
        action.status,
        action.reason,
        _to_json(action.metadata),
        _datetime_to_text(action.created_at) if sqlite else action.created_at,
        _datetime_to_text(action.completed_at) if sqlite else action.completed_at,
    )


def _agent_action_from_row(row: sqlite3.Row) -> AgentAction:
    return AgentAction.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        action_type=row["action_type"],
        status=row["status"],
        reason=row["reason"],
        metadata=_from_json(row["metadata"]),
        created_at=_datetime_from_text(row["created_at"]),
        completed_at=_datetime_from_text(row["completed_at"]),
    )


def _agent_preferences_values(
    preferences: AgentPreferences,
    *,
    sqlite: bool,
) -> tuple:
    return (
        preferences.user_niche_id,
        _to_json(preferences.preferred_source_families),
        _to_json(preferences.ignored_themes),
        _to_json(preferences.ignored_categories),
        _to_json(preferences.muted_source_ids),
        preferences.extra_instructions,
        _datetime_to_text(preferences.created_at) if sqlite else preferences.created_at,
        _datetime_to_text(preferences.updated_at) if sqlite else preferences.updated_at,
    )


def _agent_preferences_from_row(row: sqlite3.Row) -> AgentPreferences:
    return AgentPreferences.create(
        user_niche_id=str(row["user_niche_id"]),
        preferred_source_families=_from_json(row["preferred_source_families"]),
        ignored_themes=_from_json(row["ignored_themes"]),
        ignored_categories=_from_json(row["ignored_categories"]),
        muted_source_ids=_from_json(row["muted_source_ids"]),
        extra_instructions=row["extra_instructions"],
        created_at=_datetime_from_text(row["created_at"]),
        updated_at=_datetime_from_text(row["updated_at"]),
    )


def _agent_feedback_values(feedback: AgentFeedback, *, sqlite: bool) -> tuple:
    return (
        feedback.id,
        feedback.user_niche_id,
        feedback.opportunity_id,
        feedback.action,
        feedback.reason,
        _datetime_to_text(feedback.created_at) if sqlite else feedback.created_at,
    )


def _agent_feedback_from_row(row: sqlite3.Row) -> AgentFeedback:
    return AgentFeedback.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        opportunity_id=str(row["opportunity_id"]) if row["opportunity_id"] else None,
        action=row["action"],
        reason=row["reason"],
        created_at=_datetime_from_text(row["created_at"]),
    )


def _agent_activity_values(activity: AgentActivity, *, sqlite: bool) -> tuple:
    return (
        activity.id,
        activity.user_niche_id,
        activity.event_type,
        activity.title,
        activity.detail,
        _to_json(activity.metadata),
        _datetime_to_text(activity.created_at) if sqlite else activity.created_at,
    )


def _agent_activity_from_row(row: sqlite3.Row) -> AgentActivity:
    return AgentActivity.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        event_type=row["event_type"],
        title=row["title"],
        detail=row["detail"],
        metadata=_from_json(row["metadata"]),
        created_at=_datetime_from_text(row["created_at"]),
    )


def _agent_alert_values(alert: AgentAlert, *, sqlite: bool) -> tuple:
    return (
        alert.id,
        alert.user_niche_id,
        alert.alert_type,
        alert.title,
        alert.severity,
        alert.status,
        alert.detail,
        _to_json(alert.metadata),
        _datetime_to_text(alert.created_at) if sqlite else alert.created_at,
        (
            _datetime_to_text(alert.acknowledged_at)
            if sqlite
            else alert.acknowledged_at
        ),
    )


def _agent_alert_from_row(row: sqlite3.Row) -> AgentAlert:
    return AgentAlert.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        alert_type=row["alert_type"],
        title=row["title"],
        severity=row["severity"],
        status=row["status"],
        detail=row["detail"],
        metadata=_from_json(row["metadata"]),
        created_at=_datetime_from_text(row["created_at"]),
        acknowledged_at=_datetime_from_text(row["acknowledged_at"]),
    )


def _agent_follow_up_values(follow_up: AgentFollowUp, *, sqlite: bool) -> tuple:
    return (
        follow_up.id,
        follow_up.user_niche_id,
        follow_up.question,
        follow_up.opportunity_id,
        follow_up.cluster_id,
        follow_up.status,
        follow_up.response,
        _to_json(follow_up.metadata),
        (
            _datetime_to_text(follow_up.created_at)
            if sqlite
            else follow_up.created_at
        ),
        (
            _datetime_to_text(follow_up.updated_at)
            if sqlite
            else follow_up.updated_at
        ),
    )


def _updated_agent_follow_up(
    follow_up: AgentFollowUp,
    *,
    status: str,
    response: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentFollowUp | None:
    normalized_status = status.strip().lower()
    if normalized_status == "answered":
        if response is None:
            return None
        return follow_up.answer(response, metadata=metadata)
    if normalized_status == "dismissed":
        return follow_up.dismiss(metadata=metadata)
    if normalized_status == "queued":
        return AgentFollowUp.create(
            id=follow_up.id,
            user_niche_id=follow_up.user_niche_id,
            question=follow_up.question,
            opportunity_id=follow_up.opportunity_id,
            cluster_id=follow_up.cluster_id,
            status="queued",
            response=response,
            metadata={**follow_up.metadata, **(metadata or {})},
            created_at=follow_up.created_at,
            updated_at=datetime.now(tz=UTC),
        )
    return None


def _agent_follow_up_from_row(row: sqlite3.Row) -> AgentFollowUp:
    return AgentFollowUp.create(
        id=str(row["id"]),
        user_niche_id=str(row["user_niche_id"]),
        question=row["question"],
        opportunity_id=row["opportunity_id"],
        cluster_id=row["cluster_id"],
        status=row["status"],
        response=row["response"],
        metadata=_from_json(row["metadata"]),
        created_at=_datetime_from_text(row["created_at"]),
        updated_at=_datetime_from_text(row["updated_at"]),
    )


def _pipeline_run_metrics_values(
    metrics: PipelineRunMetrics,
    *,
    sqlite: bool,
) -> tuple:
    return (
        metrics.id,
        _datetime_to_text(metrics.ran_at) if sqlite else metrics.ran_at,
        metrics.fetched_count,
        metrics.fetch_failed_count,
        metrics.rule_filtered_count,
        metrics.llm_filtered_count,
        metrics.relevance_failed_count,
        metrics.extraction_attempted_count,
        metrics.extracted_count,
        metrics.no_signal_count,
        metrics.extraction_failed_count,
        metrics.signal_inserted_count,
        metrics.scored_count,
        metrics.scoring_failed_count,
        metrics.average_score,
        metrics.embedding_failed_count,
        metrics.clustered_count,
        metrics.cluster_inserted_count,
        metrics.opportunity_synthesized_count,
        metrics.opportunity_inserted_count,
        metrics.opportunity_failed_count,
        _bool_to_int(metrics.email_sent) if sqlite else metrics.email_sent,
        metrics.email_error,
    )


def _pipeline_run_metrics_from_row(row: sqlite3.Row) -> PipelineRunMetrics:
    return PipelineRunMetrics.create(
        id=row["id"],
        ran_at=_datetime_from_text(row["ran_at"]),
        fetched_count=row["fetched_count"],
        fetch_failed_count=row["fetch_failed_count"],
        rule_filtered_count=row["rule_filtered_count"],
        llm_filtered_count=row["llm_filtered_count"],
        relevance_failed_count=row["relevance_failed_count"],
        extraction_attempted_count=row["extraction_attempted_count"],
        extracted_count=row["extracted_count"],
        no_signal_count=row["no_signal_count"],
        extraction_failed_count=row["extraction_failed_count"],
        signal_inserted_count=row["signal_inserted_count"],
        scored_count=row["scored_count"],
        scoring_failed_count=row["scoring_failed_count"],
        average_score=row["average_score"],
        embedding_failed_count=row["embedding_failed_count"],
        clustered_count=row["clustered_count"],
        cluster_inserted_count=row["cluster_inserted_count"],
        opportunity_synthesized_count=row["opportunity_synthesized_count"],
        opportunity_inserted_count=row["opportunity_inserted_count"],
        opportunity_failed_count=row["opportunity_failed_count"],
        email_sent=bool(row["email_sent"]),
        email_error=row["email_error"],
    )


def _source_locator_from_row(row: sqlite3.Row) -> SourceLocator:
    return SourceLocator.create(
        id=row["id"],
        locator=row["locator"],
        enabled=bool(row["enabled"]),
        limit=row["limit_value"],
        options=_from_json(row["options"]),
    )


def _ensure_sqlite_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {row["name"] for row in rows}
    if column_name in existing_columns:
        return
    connection.execute(
        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
    )


def _row_get(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError):
        return None
