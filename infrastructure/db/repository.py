"""Database repository implementations for domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from application.ports import (
    AgentActivityRepository,
    AgentAlertRepository,
    AgentFeedbackRepository,
    AgentFollowUpRepository,
    AgentPreferencesRepository,
    ClusterRepository,
    CompetitorRepository,
    MarketRepository,
    MonitoredSourceRepository,
    OpportunityRepository,
    PipelineRunMetricsRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceHealthRepository,
    SourceLocatorRepository,
)
from domain.agent import (
    AgentActivity,
    AgentAlert,
    AgentFeedback,
    AgentFollowUp,
    AgentPreferences,
)
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.market import Market
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import MonitoredSource, SourceHealth, SourceLocator


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
class InMemoryMarketRepository(MarketRepository):
    """In-memory market repository."""

    markets: dict[str, Market] = field(default_factory=dict)

    def save_markets(self, markets: list[Market]) -> int:
        inserted_count = 0
        for market in markets:
            if market.id in self.markets:
                continue
            self.markets[market.id] = market
            inserted_count += 1
        return inserted_count

    def get_market(self, market_id: str) -> Market | None:
        return self.markets.get(market_id)

    def list_markets(self, user_id: str | None = None) -> list[Market]:
        markets = list(self.markets.values())
        if user_id is not None:
            markets = [m for m in markets if m.user_id == user_id]
        return markets

    def update_market(self, market: Market) -> bool:
        if market.id not in self.markets:
            return False
        self.markets[market.id] = market
        return True

    def delete_market(self, market_id: str) -> bool:
        return self.markets.pop(market_id, None) is not None


@dataclass
class InMemoryAgentPreferencesRepository(AgentPreferencesRepository):
    """In-memory agent preferences repository."""

    preferences_by_market: dict[str, AgentPreferences] = field(default_factory=dict)

    def save_agent_preferences(self, preferences: AgentPreferences) -> bool:
        self.preferences_by_market[preferences.market_id] = preferences
        return True

    def get_agent_preferences(self, market_id: str) -> AgentPreferences | None:
        return self.preferences_by_market.get(market_id)

    def delete_agent_preferences(self, market_id: str) -> bool:
        return self.preferences_by_market.pop(market_id, None) is not None


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
        market_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        feedback = list(self.feedback_by_id.values())
        if market_id is not None:
            feedback = [item for item in feedback if item.market_id == market_id]
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
        market_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentActivity]:
        activity = list(self.activity_by_id.values())
        if market_id is not None:
            activity = [item for item in activity if item.market_id == market_id]
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
        market_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAlert]:
        alerts = list(self.alerts_by_id.values())
        if market_id is not None:
            alerts = [item for item in alerts if item.market_id == market_id]
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
        market_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentFollowUp]:
        follow_ups = list(self.follow_ups_by_id.values())
        if market_id is not None:
            follow_ups = [
                item for item in follow_ups if item.market_id == market_id
            ]
        if status is not None:
            follow_ups = [item for item in follow_ups if item.status == status]
        follow_ups = sorted(
            follow_ups,
            key=lambda item: item.created_at or datetime.min,
            reverse=True,
        )
        return follow_ups[:limit] if limit is not None else follow_ups


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
class InMemoryCompetitorRepository(CompetitorRepository):
    """In-memory competitor repository."""

    competitors: dict[str, Competitor] = field(default_factory=dict)

    def save_competitors(self, competitors: list[Competitor]) -> int:
        inserted_count = 0
        for competitor in competitors:
            if competitor.id in self.competitors:
                continue
            self.competitors[competitor.id] = competitor
            inserted_count += 1
        return inserted_count

    def get_competitor(self, competitor_id: str) -> Competitor | None:
        return self.competitors.get(competitor_id)

    def list_competitors(self) -> list[Competitor]:
        return list(self.competitors.values())


@dataclass
class InMemoryMonitoredSourceRepository(MonitoredSourceRepository):
    """In-memory monitored source repository."""

    monitored_sources: dict[str, MonitoredSource] = field(default_factory=dict)

    def save_monitored_sources(self, sources: list[MonitoredSource]) -> int:
        inserted_count = 0
        for source in sources:
            if source.id in self.monitored_sources:
                continue
            self.monitored_sources[source.id] = source
            inserted_count += 1
        return inserted_count

    def get_monitored_source(self, source_id: str) -> MonitoredSource | None:
        return self.monitored_sources.get(source_id)

    def update_monitored_source(self, source: MonitoredSource) -> bool:
        if source.id not in self.monitored_sources:
            return False
        self.monitored_sources[source.id] = source
        return True

    def list_monitored_sources(
        self,
        *,
        competitor_id: str | None = None,
        market_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        sources = list(self.monitored_sources.values())
        if competitor_id is not None:
            sources = [source for source in sources if source.competitor_id == competitor_id]
        if market_id is not None:
            sources = [source for source in sources if source.market_id == market_id]
        if enabled is not None:
            sources = [source for source in sources if source.enabled == enabled]
        return sources


@dataclass
class InMemorySourceHealthRepository(SourceHealthRepository):
    """In-memory monitored source health repository."""

    source_health: dict[str, SourceHealth] = field(default_factory=dict)

    def save_source_health(self, health: SourceHealth) -> bool:
        self.source_health[health.monitored_source_id] = health
        return True

    def get_source_health(self, monitored_source_id: str) -> SourceHealth | None:
        return self.source_health.get(monitored_source_id)

    def list_source_health(
        self,
        *,
        monitored_source_id: str | None = None,
        status: str | None = None,
    ) -> list[SourceHealth]:
        snapshots = list(self.source_health.values())
        if monitored_source_id is not None:
            snapshots = [
                health
                for health in snapshots
                if health.monitored_source_id == monitored_source_id
            ]
        if status is not None:
            snapshots = [
                health for health in snapshots if health.last_status == status
            ]
        return sorted(snapshots, key=lambda health: health.monitored_source_id)


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
                competitor_id TEXT,
                market_id TEXT,
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
                    category, confidence, competitor_id, market_id,
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
                    signal.competitor_id,
                    signal.market_id,
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
                cluster_id TEXT NOT NULL,
                title TEXT NOT NULL,
                target_user TEXT NOT NULL,
                pain_summary TEXT NOT NULL,
                why_it_matters TEXT NOT NULL,
                suggested_wedge TEXT NOT NULL,
                evidence_count INTEGER NOT NULL,
                confidence REAL NOT NULL,
                evidence_signal_ids TEXT NOT NULL
            )
            """
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
                    confidence, evidence_signal_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    cluster_id = excluded.cluster_id,
                    title = excluded.title,
                    target_user = excluded.target_user,
                    pain_summary = excluded.pain_summary,
                    why_it_matters = excluded.why_it_matters,
                    suggested_wedge = excluded.suggested_wedge,
                    evidence_count = excluded.evidence_count,
                    confidence = excluded.confidence,
                    evidence_signal_ids = excluded.evidence_signal_ids
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


class SQLiteMarketRepository(_SQLiteRepository, MarketRepository):
    """SQLite-backed market repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                target_user TEXT,
                idea_prompt TEXT,
                created_at TEXT
            )
            """
        )
        self.connection.commit()

    def save_markets(self, markets: list[Market]) -> int:
        inserted_count = 0
        for market in markets:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO markets (
                    id, name, description, target_user, idea_prompt, user_id, template_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    market.id,
                    market.name,
                    market.description,
                    market.target_user,
                    market.idea_prompt,
                    market.user_id,
                    market.template_id,
                    _datetime_to_text(market.created_at),
                ),
            )
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

    def get_market(self, market_id: str) -> Market | None:
        row = self.connection.execute(
            "SELECT * FROM markets WHERE id = ?",
            (market_id,),
        ).fetchone()
        return _market_from_row(row) if row else None

    def list_markets(self, user_id: str | None = None) -> list[Market]:
        if user_id is not None:
            rows = self.connection.execute(
                "SELECT * FROM markets WHERE user_id = ? ORDER BY name", (user_id,)
            ).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM markets ORDER BY name").fetchall()
        return [_market_from_row(row) for row in rows]

    def update_market(self, market: Market) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE markets
            SET name = ?,
                description = ?,
                target_user = ?,
                idea_prompt = ?
            WHERE id = ?
            """,
            (
                market.name,
                market.description,
                market.target_user,
                market.idea_prompt,
                market.id,
            ),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def delete_market(self, market_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM markets WHERE id = ?",
            (market_id,),
        )
        self.connection.commit()
        return cursor.rowcount > 0


class SQLiteAgentPreferencesRepository(_SQLiteRepository, AgentPreferencesRepository):
    """SQLite-backed agent preferences repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_preferences (
                market_id TEXT PRIMARY KEY,
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
                market_id, preferred_source_families, ignored_themes,
                ignored_categories, muted_source_ids, extra_instructions,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(market_id) DO UPDATE SET
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

    def get_agent_preferences(self, market_id: str) -> AgentPreferences | None:
        row = self.connection.execute(
            "SELECT * FROM agent_preferences WHERE market_id = ?",
            (market_id,),
        ).fetchone()
        return _agent_preferences_from_row(row) if row else None

    def delete_agent_preferences(self, market_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM agent_preferences WHERE market_id = ?",
            (market_id,),
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
                market_id TEXT NOT NULL,
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
                id, market_id, opportunity_id, action, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            _agent_feedback_values(feedback, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_agent_feedback(
        self,
        *,
        market_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        query = "SELECT * FROM agent_feedback"
        clauses: list[str] = []
        params: list[str] = []
        if market_id is not None:
            clauses.append("market_id = ?")
            params.append(market_id)
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
                market_id TEXT NOT NULL,
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
                id, market_id, event_type, title, detail, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            _agent_activity_values(activity, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_agent_activity(
        self,
        *,
        market_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentActivity]:
        query = "SELECT * FROM agent_activity"
        clauses: list[str] = []
        params: list[str | int] = []
        if market_id is not None:
            clauses.append("market_id = ?")
            params.append(market_id)
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
                market_id TEXT NOT NULL,
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
                id, market_id, alert_type, title, severity, status, detail,
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
        market_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAlert]:
        query = "SELECT * FROM agent_alerts"
        clauses: list[str] = []
        params: list[str | int] = []
        if market_id is not None:
            clauses.append("market_id = ?")
            params.append(market_id)
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
                market_id TEXT NOT NULL,
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
                id, market_id, question, opportunity_id, cluster_id, status,
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
        market_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentFollowUp]:
        query = "SELECT * FROM agent_follow_ups"
        clauses: list[str] = []
        params: list[str | int] = []
        if market_id is not None:
            clauses.append("market_id = ?")
            params.append(market_id)
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


class SQLiteCompetitorRepository(_SQLiteRepository, CompetitorRepository):
    """SQLite-backed competitor repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS competitors (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                website TEXT,
                category TEXT,
                description TEXT,
                market_id TEXT,
                created_at TEXT
            )
            """
        )
        self.connection.commit()

    def save_competitors(self, competitors: list[Competitor]) -> int:
        inserted_count = 0
        for competitor in competitors:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO competitors (
                    id, name, website, category, description, market_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    competitor.id,
                    competitor.name,
                    competitor.website,
                    competitor.category,
                    competitor.description,
                    competitor.market_id,
                    _datetime_to_text(competitor.created_at),
                ),
            )
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

    def get_competitor(self, competitor_id: str) -> Competitor | None:
        row = self.connection.execute(
            "SELECT * FROM competitors WHERE id = ?",
            (competitor_id,),
        ).fetchone()
        return _competitor_from_row(row) if row else None

    def list_competitors(self) -> list[Competitor]:
        rows = self.connection.execute("SELECT * FROM competitors ORDER BY name").fetchall()
        return [_competitor_from_row(row) for row in rows]


class SQLiteMonitoredSourceRepository(_SQLiteRepository, MonitoredSourceRepository):
    """SQLite-backed monitored source repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS monitored_sources (
                id TEXT PRIMARY KEY,
                competitor_id TEXT,
                market_id TEXT,
                locator TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                limit_value INTEGER,
                scan_frequency TEXT,
                last_scanned_at TEXT,
                last_error TEXT,
                options TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_monitored_sources(self, sources: list[MonitoredSource]) -> int:
        inserted_count = 0
        for source in sources:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO monitored_sources (
                    id, competitor_id, market_id, locator, source_type, enabled,
                    limit_value, scan_frequency, last_scanned_at, last_error, options
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.competitor_id,
                    source.market_id,
                    source.locator,
                    source.source_type,
                    _bool_to_int(source.enabled),
                    source.limit,
                    source.scan_frequency,
                    _datetime_to_text(source.last_scanned_at),
                    source.last_error,
                    _to_json(source.options),
                ),
            )
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

    def get_monitored_source(self, source_id: str) -> MonitoredSource | None:
        row = self.connection.execute(
            "SELECT * FROM monitored_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        return _monitored_source_from_row(row) if row else None

    def update_monitored_source(self, source: MonitoredSource) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE monitored_sources
            SET
                source_type = ?,
                competitor_id = ?,
                market_id = ?,
                enabled = ?,
                limit_value = ?,
                scan_frequency = ?,
                last_scanned_at = ?,
                last_error = ?,
                options = ?
            WHERE id = ?
            """,
            (
                source.source_type,
                source.competitor_id,
                source.market_id,
                _bool_to_int(source.enabled),
                source.limit,
                source.scan_frequency,
                _datetime_to_text(source.last_scanned_at),
                source.last_error,
                _to_json(source.options),
                source.id,
            ),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def list_monitored_sources(
        self,
        *,
        competitor_id: str | None = None,
        market_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        query = "SELECT * FROM monitored_sources"
        clauses = []
        params = []
        if competitor_id is not None:
            clauses.append("competitor_id = ?")
            params.append(competitor_id)
        if market_id is not None:
            clauses.append("market_id = ?")
            params.append(market_id)
        if enabled is not None:
            clauses.append("enabled = ?")
            params.append(_bool_to_int(enabled))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_monitored_source_from_row(row) for row in rows]


class SQLiteSourceHealthRepository(_SQLiteRepository, SourceHealthRepository):
    """SQLite-backed monitored source health repository."""

    def _initialize_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_health (
                monitored_source_id TEXT PRIMARY KEY,
                total_runs INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failure_count INTEGER NOT NULL,
                consecutive_failures INTEGER NOT NULL,
                posts_fetched_count INTEGER NOT NULL,
                relevant_posts_count INTEGER NOT NULL,
                extracted_signals_count INTEGER NOT NULL,
                opportunity_count INTEGER NOT NULL,
                last_status TEXT NOT NULL,
                last_error TEXT,
                last_fetched_count INTEGER NOT NULL,
                last_relevant_count INTEGER NOT NULL,
                last_extracted_count INTEGER NOT NULL,
                last_opportunity_count INTEGER NOT NULL,
                last_scanned_at TEXT,
                updated_at TEXT
            )
            """
        )
        self.connection.commit()

    def save_source_health(self, health: SourceHealth) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO source_health (
                monitored_source_id, total_runs, success_count, failure_count,
                consecutive_failures, posts_fetched_count, relevant_posts_count,
                extracted_signals_count, opportunity_count, last_status,
                last_error, last_fetched_count, last_relevant_count,
                last_extracted_count, last_opportunity_count, last_scanned_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(monitored_source_id) DO UPDATE SET
                total_runs = excluded.total_runs,
                success_count = excluded.success_count,
                failure_count = excluded.failure_count,
                consecutive_failures = excluded.consecutive_failures,
                posts_fetched_count = excluded.posts_fetched_count,
                relevant_posts_count = excluded.relevant_posts_count,
                extracted_signals_count = excluded.extracted_signals_count,
                opportunity_count = excluded.opportunity_count,
                last_status = excluded.last_status,
                last_error = excluded.last_error,
                last_fetched_count = excluded.last_fetched_count,
                last_relevant_count = excluded.last_relevant_count,
                last_extracted_count = excluded.last_extracted_count,
                last_opportunity_count = excluded.last_opportunity_count,
                last_scanned_at = excluded.last_scanned_at,
                updated_at = excluded.updated_at
            """,
            _source_health_values(health, sqlite=True),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def get_source_health(self, monitored_source_id: str) -> SourceHealth | None:
        row = self.connection.execute(
            "SELECT * FROM source_health WHERE monitored_source_id = ?",
            (monitored_source_id,),
        ).fetchone()
        return _source_health_from_row(row) if row else None

    def list_source_health(
        self,
        *,
        monitored_source_id: str | None = None,
        status: str | None = None,
    ) -> list[SourceHealth]:
        query = "SELECT * FROM source_health"
        clauses = []
        params = []
        if monitored_source_id is not None:
            clauses.append("monitored_source_id = ?")
            params.append(monitored_source_id)
        if status is not None:
            clauses.append("last_status = ?")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY monitored_source_id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_source_health_from_row(row) for row in rows]


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
                e.competitor_id,
                e.market_id,
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
                e.competitor_id,
                e.market_id,
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
                signal.competitor_id,
                signal.market_id,
                signal.evidence_url,
                signal.evidence_text,
                signal.detected_at,
            ]
        ):
            return

        self.connection.execute(
            """
            INSERT INTO signal_evidence (
                signal_id, competitor_id, market_id, evidence_url,
                evidence_text, detected_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (signal_id) DO UPDATE SET
                competitor_id = EXCLUDED.competitor_id,
                market_id = EXCLUDED.market_id,
                evidence_url = EXCLUDED.evidence_url,
                evidence_text = EXCLUDED.evidence_text,
                detected_at = EXCLUDED.detected_at,
                updated_at = now()
            """,
            (
                signal.id,
                signal.competitor_id,
                signal.market_id,
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
                    confidence, evidence_signal_ids
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
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


class PostgresMarketRepository(_PostgresRepository, MarketRepository):
    """Postgres-backed market repository."""

    def save_markets(self, markets: list[Market]) -> int:
        inserted_count = 0
        for market in markets:
            cursor = self.connection.execute(
                """
                INSERT INTO markets (
                    id, name, description, target_user, idea_prompt, user_id, template_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    market.id,
                    market.name,
                    market.description,
                    market.target_user,
                    market.idea_prompt,
                    market.user_id,
                    market.template_id,
                    market.created_at,
                ),
            )
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

    def get_market(self, market_id: str) -> Market | None:
        row = self.connection.execute(
            "SELECT * FROM markets WHERE id = %s",
            (market_id,),
        ).fetchone()
        return _market_from_row(row) if row else None

    def list_markets(self, user_id: str | None = None) -> list[Market]:
        if user_id is not None:
            rows = self.connection.execute(
                "SELECT * FROM markets WHERE user_id = %s ORDER BY name", (user_id,)
            ).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM markets ORDER BY name").fetchall()
        return [_market_from_row(row) for row in rows]

    def update_market(self, market: Market) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE markets
            SET name = %s,
                description = %s,
                target_user = %s,
                idea_prompt = %s
            WHERE id = %s
            """,
            (
                market.name,
                market.description,
                market.target_user,
                market.idea_prompt,
                market.id,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def delete_market(self, market_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM markets WHERE id = %s",
            (market_id,),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresAgentPreferencesRepository(
    _PostgresRepository,
    AgentPreferencesRepository,
):
    """Postgres-backed agent preferences repository."""

    def save_agent_preferences(self, preferences: AgentPreferences) -> bool:
        self.connection.execute(
            """
            INSERT INTO agent_preferences (
                market_id, preferred_source_families, ignored_themes,
                ignored_categories, muted_source_ids, extra_instructions,
                created_at, updated_at
            ) VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
            ON CONFLICT (market_id) DO UPDATE SET
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

    def get_agent_preferences(self, market_id: str) -> AgentPreferences | None:
        row = self.connection.execute(
            "SELECT * FROM agent_preferences WHERE market_id = %s",
            (market_id,),
        ).fetchone()
        return _agent_preferences_from_row(row) if row else None

    def delete_agent_preferences(self, market_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM agent_preferences WHERE market_id = %s",
            (market_id,),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0


class PostgresAgentFeedbackRepository(_PostgresRepository, AgentFeedbackRepository):
    """Postgres-backed agent feedback repository."""

    def save_agent_feedback(self, feedback: AgentFeedback) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO agent_feedback (
                id, market_id, opportunity_id, action, reason, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            _agent_feedback_values(feedback, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_agent_feedback(
        self,
        *,
        market_id: str | None = None,
        opportunity_id: str | None = None,
        action: str | None = None,
    ) -> list[AgentFeedback]:
        query = "SELECT * FROM agent_feedback"
        clauses: list[str] = []
        params: list[str] = []
        if market_id is not None:
            clauses.append("market_id = %s")
            params.append(market_id)
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
                id, market_id, event_type, title, detail, metadata, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            _agent_activity_values(activity, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_agent_activity(
        self,
        *,
        market_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AgentActivity]:
        query = "SELECT * FROM agent_activity"
        clauses: list[str] = []
        params: list[str | int] = []
        if market_id is not None:
            clauses.append("market_id = %s")
            params.append(market_id)
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
                id, market_id, alert_type, title, severity, status, detail,
                metadata, created_at, acknowledged_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
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
        market_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAlert]:
        query = "SELECT * FROM agent_alerts"
        clauses: list[str] = []
        params: list[str | int] = []
        if market_id is not None:
            clauses.append("market_id = %s")
            params.append(market_id)
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
                id, market_id, question, opportunity_id, cluster_id, status,
                response, metadata, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            _agent_follow_up_values(follow_up, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_agent_follow_ups(
        self,
        *,
        market_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[AgentFollowUp]:
        query = "SELECT * FROM agent_follow_ups"
        clauses: list[str] = []
        params: list[str | int] = []
        if market_id is not None:
            clauses.append("market_id = %s")
            params.append(market_id)
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


class PostgresCompetitorRepository(_PostgresRepository, CompetitorRepository):
    """Postgres-backed competitor repository."""

    def save_competitors(self, competitors: list[Competitor]) -> int:
        inserted_count = 0
        for competitor in competitors:
            cursor = self.connection.execute(
                """
                INSERT INTO competitors (
                    id, name, website, category, description, market_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    competitor.id,
                    competitor.name,
                    competitor.website,
                    competitor.category,
                    competitor.description,
                    competitor.market_id,
                    competitor.created_at,
                ),
            )
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

    def get_competitor(self, competitor_id: str) -> Competitor | None:
        row = self.connection.execute(
            "SELECT * FROM competitors WHERE id = %s",
            (competitor_id,),
        ).fetchone()
        return _competitor_from_row(row) if row else None

    def list_competitors(self) -> list[Competitor]:
        rows = self.connection.execute("SELECT * FROM competitors ORDER BY name").fetchall()
        return [_competitor_from_row(row) for row in rows]


class PostgresMonitoredSourceRepository(_PostgresRepository, MonitoredSourceRepository):
    """Postgres-backed monitored source repository."""

    def save_monitored_sources(self, sources: list[MonitoredSource]) -> int:
        inserted_count = 0
        for source in sources:
            cursor = self.connection.execute(
                """
                INSERT INTO monitored_sources (
                    id, competitor_id, market_id, locator, source_type, enabled,
                    limit_value, scan_frequency, last_scanned_at, last_error, options
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    source.id,
                    source.competitor_id,
                    source.market_id,
                    source.locator,
                    source.source_type,
                    source.enabled,
                    source.limit,
                    source.scan_frequency,
                    source.last_scanned_at,
                    source.last_error,
                    _to_json(source.options),
                ),
            )
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

    def get_monitored_source(self, source_id: str) -> MonitoredSource | None:
        row = self.connection.execute(
            "SELECT * FROM monitored_sources WHERE id = %s",
            (source_id,),
        ).fetchone()
        return _monitored_source_from_row(row) if row else None

    def update_monitored_source(self, source: MonitoredSource) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE monitored_sources
            SET
                source_type = %s,
                competitor_id = %s,
                market_id = %s,
                enabled = %s,
                limit_value = %s,
                scan_frequency = %s,
                last_scanned_at = %s,
                last_error = %s,
                options = %s::jsonb,
                updated_at = now()
            WHERE id = %s
            """,
            (
                source.source_type,
                source.competitor_id,
                source.market_id,
                source.enabled,
                source.limit,
                source.scan_frequency,
                source.last_scanned_at,
                source.last_error,
                _to_json(source.options),
                source.id,
            ),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def list_monitored_sources(
        self,
        *,
        competitor_id: str | None = None,
        market_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        query = "SELECT * FROM monitored_sources"
        clauses = []
        params = []
        if competitor_id is not None:
            clauses.append("competitor_id = %s")
            params.append(competitor_id)
        if market_id is not None:
            clauses.append("market_id = %s")
            params.append(market_id)
        if enabled is not None:
            clauses.append("enabled = %s")
            params.append(enabled)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_monitored_source_from_row(row) for row in rows]


class PostgresSourceHealthRepository(_PostgresRepository, SourceHealthRepository):
    """Postgres-backed monitored source health repository."""

    def save_source_health(self, health: SourceHealth) -> bool:
        cursor = self.connection.execute(
            """
            INSERT INTO source_health (
                monitored_source_id, total_runs, success_count, failure_count,
                consecutive_failures, posts_fetched_count, relevant_posts_count,
                extracted_signals_count, opportunity_count, last_status,
                last_error, last_fetched_count, last_relevant_count,
                last_extracted_count, last_opportunity_count, last_scanned_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (monitored_source_id) DO UPDATE SET
                total_runs = EXCLUDED.total_runs,
                success_count = EXCLUDED.success_count,
                failure_count = EXCLUDED.failure_count,
                consecutive_failures = EXCLUDED.consecutive_failures,
                posts_fetched_count = EXCLUDED.posts_fetched_count,
                relevant_posts_count = EXCLUDED.relevant_posts_count,
                extracted_signals_count = EXCLUDED.extracted_signals_count,
                opportunity_count = EXCLUDED.opportunity_count,
                last_status = EXCLUDED.last_status,
                last_error = EXCLUDED.last_error,
                last_fetched_count = EXCLUDED.last_fetched_count,
                last_relevant_count = EXCLUDED.last_relevant_count,
                last_extracted_count = EXCLUDED.last_extracted_count,
                last_opportunity_count = EXCLUDED.last_opportunity_count,
                last_scanned_at = EXCLUDED.last_scanned_at,
                updated_at = EXCLUDED.updated_at
            """,
            _source_health_values(health, sqlite=False),
        )
        self.connection.commit()
        return _rowcount(cursor) > 0

    def get_source_health(self, monitored_source_id: str) -> SourceHealth | None:
        row = self.connection.execute(
            "SELECT * FROM source_health WHERE monitored_source_id = %s",
            (monitored_source_id,),
        ).fetchone()
        return _source_health_from_row(row) if row else None

    def list_source_health(
        self,
        *,
        monitored_source_id: str | None = None,
        status: str | None = None,
    ) -> list[SourceHealth]:
        query = "SELECT * FROM source_health"
        clauses = []
        params = []
        if monitored_source_id is not None:
            clauses.append("monitored_source_id = %s")
            params.append(monitored_source_id)
        if status is not None:
            clauses.append("last_status = %s")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY monitored_source_id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_source_health_from_row(row) for row in rows]


def connect_postgres(database_url: str) -> Any:
    """Create a Postgres connection for repository wiring."""
    return _connect_postgres(database_url)


def _connect_postgres(database_url: str) -> Any:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg[binary] is required for Supabase Postgres") from exc

    return psycopg.connect(database_url, row_factory=dict_row, autocommit=True)


def _rowcount(cursor: Any) -> int:
    rowcount = getattr(cursor, "rowcount", 0)
    return rowcount if rowcount and rowcount > 0 else 0


def _to_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _from_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return json.loads(value)


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
        competitor_id=_row_get(row, "competitor_id"),
        market_id=_row_get(row, "market_id"),
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
    )


def _market_from_row(row: sqlite3.Row) -> Market:
    keys = row.keys()
    return Market.create(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        target_user=row["target_user"],
        idea_prompt=row["idea_prompt"],
        user_id=row["user_id"] if "user_id" in keys else None,
        template_id=row["template_id"] if "template_id" in keys else None,
        created_at=_datetime_from_text(row["created_at"]),
    )


def _agent_preferences_values(
    preferences: AgentPreferences,
    *,
    sqlite: bool,
) -> tuple:
    return (
        preferences.market_id,
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
        market_id=row["market_id"],
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
        feedback.market_id,
        feedback.opportunity_id,
        feedback.action,
        feedback.reason,
        _datetime_to_text(feedback.created_at) if sqlite else feedback.created_at,
    )


def _agent_feedback_from_row(row: sqlite3.Row) -> AgentFeedback:
    return AgentFeedback.create(
        id=row["id"],
        market_id=row["market_id"],
        opportunity_id=row["opportunity_id"],
        action=row["action"],
        reason=row["reason"],
        created_at=_datetime_from_text(row["created_at"]),
    )


def _agent_activity_values(activity: AgentActivity, *, sqlite: bool) -> tuple:
    return (
        activity.id,
        activity.market_id,
        activity.event_type,
        activity.title,
        activity.detail,
        _to_json(activity.metadata),
        _datetime_to_text(activity.created_at) if sqlite else activity.created_at,
    )


def _agent_activity_from_row(row: sqlite3.Row) -> AgentActivity:
    return AgentActivity.create(
        id=row["id"],
        market_id=row["market_id"],
        event_type=row["event_type"],
        title=row["title"],
        detail=row["detail"],
        metadata=_from_json(row["metadata"]),
        created_at=_datetime_from_text(row["created_at"]),
    )


def _agent_alert_values(alert: AgentAlert, *, sqlite: bool) -> tuple:
    return (
        alert.id,
        alert.market_id,
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
        id=row["id"],
        market_id=row["market_id"],
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
        follow_up.market_id,
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


def _agent_follow_up_from_row(row: sqlite3.Row) -> AgentFollowUp:
    return AgentFollowUp.create(
        id=row["id"],
        market_id=row["market_id"],
        question=row["question"],
        opportunity_id=row["opportunity_id"],
        cluster_id=row["cluster_id"],
        status=row["status"],
        response=row["response"],
        metadata=_from_json(row["metadata"]),
        created_at=_datetime_from_text(row["created_at"]),
        updated_at=_datetime_from_text(row["updated_at"]),
    )


def _source_health_values(health: SourceHealth, *, sqlite: bool) -> tuple:
    return (
        health.monitored_source_id,
        health.total_runs,
        health.success_count,
        health.failure_count,
        health.consecutive_failures,
        health.posts_fetched_count,
        health.relevant_posts_count,
        health.extracted_signals_count,
        health.opportunity_count,
        health.last_status,
        health.last_error,
        health.last_fetched_count,
        health.last_relevant_count,
        health.last_extracted_count,
        health.last_opportunity_count,
        _datetime_to_text(health.last_scanned_at) if sqlite else health.last_scanned_at,
        _datetime_to_text(health.updated_at) if sqlite else health.updated_at,
    )


def _source_health_from_row(row: sqlite3.Row) -> SourceHealth:
    return SourceHealth.create(
        monitored_source_id=row["monitored_source_id"],
        total_runs=row["total_runs"],
        success_count=row["success_count"],
        failure_count=row["failure_count"],
        consecutive_failures=row["consecutive_failures"],
        posts_fetched_count=row["posts_fetched_count"],
        relevant_posts_count=row["relevant_posts_count"],
        extracted_signals_count=row["extracted_signals_count"],
        opportunity_count=row["opportunity_count"],
        last_status=row["last_status"],
        last_error=row["last_error"],
        last_fetched_count=row["last_fetched_count"],
        last_relevant_count=row["last_relevant_count"],
        last_extracted_count=row["last_extracted_count"],
        last_opportunity_count=row["last_opportunity_count"],
        last_scanned_at=_datetime_from_text(row["last_scanned_at"]),
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


def _competitor_from_row(row: sqlite3.Row) -> Competitor:
    return Competitor.create(
        id=row["id"],
        name=row["name"],
        website=row["website"],
        category=row["category"],
        description=row["description"],
        market_id=_row_get(row, "market_id"),
        created_at=_datetime_from_text(row["created_at"]),
    )


def _monitored_source_from_row(row: sqlite3.Row) -> MonitoredSource:
    return MonitoredSource.create(
        id=row["id"],
        competitor_id=row["competitor_id"],
        market_id=_row_get(row, "market_id"),
        locator=row["locator"],
        source_type=row["source_type"],
        enabled=bool(row["enabled"]),
        limit=row["limit_value"],
        scan_frequency=row["scan_frequency"],
        last_scanned_at=_datetime_from_text(row["last_scanned_at"]),
        last_error=row["last_error"],
        options=_from_json(row["options"]),
    )


def _row_get(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError):
        return None
