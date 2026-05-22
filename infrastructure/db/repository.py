"""Database repository implementations for domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from application.ports import (
    ClusterRepository,
    CompetitorRepository,
    MonitoredSourceRepository,
    OpportunityRepository,
    PipelineRunMetricsRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceLocatorRepository,
)
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal
from domain.source import MonitoredSource, SourceLocator


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
        inserted_count = 0
        for cluster in clusters:
            if cluster.id in self.clusters:
                continue
            self.clusters[cluster.id] = cluster
            inserted_count += 1
        return inserted_count

    def get_cluster(self, cluster_id: str) -> SignalCluster | None:
        return self.clusters.get(cluster_id)

    def list_clusters(self) -> list[SignalCluster]:
        return list(self.clusters.values())


@dataclass
class InMemoryOpportunityRepository(OpportunityRepository):
    """In-memory synthesized opportunity repository."""

    opportunities: dict[str, Opportunity] = field(default_factory=dict)

    def save_opportunities(self, opportunities: list[Opportunity]) -> int:
        inserted_count = 0
        for opportunity in opportunities:
            if opportunity.id in self.opportunities:
                continue
            self.opportunities[opportunity.id] = opportunity
            inserted_count += 1
        return inserted_count

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        return self.opportunities.get(opportunity_id)

    def list_opportunities(self) -> list[Opportunity]:
        return list(self.opportunities.values())


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
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        sources = list(self.monitored_sources.values())
        if competitor_id is not None:
            sources = [source for source in sources if source.competitor_id == competitor_id]
        if enabled is not None:
            sources = [source for source in sources if source.enabled == enabled]
        return sources


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
                    category, confidence, competitor_id, evidence_url,
                    evidence_text, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        inserted_count = 0
        for cluster in clusters:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO clusters (
                    id, theme, summary, signal_ids, frequency,
                    average_score, top_examples
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

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
        inserted_count = 0
        for opportunity in opportunities:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO opportunities (
                    id, cluster_id, title, target_user, pain_summary,
                    why_it_matters, suggested_wedge, evidence_count,
                    confidence, evidence_signal_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            inserted_count += cursor.rowcount
        self.connection.commit()
        return inserted_count

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
                    id, name, website, category, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    competitor.id,
                    competitor.name,
                    competitor.website,
                    competitor.category,
                    competitor.description,
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
                competitor_id TEXT NOT NULL,
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
                    id, competitor_id, locator, source_type, enabled,
                    limit_value, scan_frequency, last_scanned_at, last_error, options
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source.id,
                    source.competitor_id,
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
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        query = "SELECT * FROM monitored_sources"
        clauses = []
        params = []
        if competitor_id is not None:
            clauses.append("competitor_id = ?")
            params.append(competitor_id)
        if enabled is not None:
            clauses.append("enabled = ?")
            params.append(_bool_to_int(enabled))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_monitored_source_from_row(row) for row in rows]


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
                signal.evidence_url,
                signal.evidence_text,
                signal.detected_at,
            ]
        ):
            return

        self.connection.execute(
            """
            INSERT INTO signal_evidence (
                signal_id, competitor_id, evidence_url, evidence_text, detected_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (signal_id) DO UPDATE SET
                competitor_id = EXCLUDED.competitor_id,
                evidence_url = EXCLUDED.evidence_url,
                evidence_text = EXCLUDED.evidence_text,
                detected_at = EXCLUDED.detected_at,
                updated_at = now()
            """,
            (
                signal.id,
                signal.competitor_id,
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
        inserted_count = 0
        for cluster in clusters:
            cursor = self.connection.execute(
                """
                INSERT INTO clusters (
                    id, theme, summary, signal_ids, frequency,
                    average_score, top_examples
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
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
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

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
        inserted_count = 0
        for opportunity in opportunities:
            cursor = self.connection.execute(
                """
                INSERT INTO opportunities (
                    id, cluster_id, title, target_user, pain_summary,
                    why_it_matters, suggested_wedge, evidence_count,
                    confidence, evidence_signal_ids
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO NOTHING
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
            inserted_count += _rowcount(cursor)
        self.connection.commit()
        return inserted_count

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
                    id, name, website, category, description, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    competitor.id,
                    competitor.name,
                    competitor.website,
                    competitor.category,
                    competitor.description,
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
                    id, competitor_id, locator, source_type, enabled,
                    limit_value, scan_frequency, last_scanned_at, last_error, options
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    source.id,
                    source.competitor_id,
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
        enabled: bool | None = None,
    ) -> list[MonitoredSource]:
        query = "SELECT * FROM monitored_sources"
        clauses = []
        params = []
        if competitor_id is not None:
            clauses.append("competitor_id = %s")
            params.append(competitor_id)
        if enabled is not None:
            clauses.append("enabled = %s")
            params.append(enabled)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id"
        rows = self.connection.execute(query, tuple(params)).fetchall()
        return [_monitored_source_from_row(row) for row in rows]


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
        created_at=_datetime_from_text(row["created_at"]),
    )


def _monitored_source_from_row(row: sqlite3.Row) -> MonitoredSource:
    return MonitoredSource.create(
        id=row["id"],
        competitor_id=row["competitor_id"],
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
