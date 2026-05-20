"""Database repository implementations for domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any

from application.ports import (
    ClusterRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
)
from domain.cluster import SignalCluster
from domain.post import RawPost
from domain.score import OpportunityScore
from domain.signal import Signal


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
                confidence REAL NOT NULL
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
                    category, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        self.connection.commit()
        return inserted_count

    def get_signal(self, signal_id: str) -> Signal | None:
        row = self.connection.execute(
            "SELECT * FROM signals WHERE id = %s",
            (signal_id,),
        ).fetchone()
        return _signal_from_row(row) if row else None

    def list_signals(self) -> list[Signal]:
        rows = self.connection.execute("SELECT * FROM signals ORDER BY id").fetchall()
        return [_signal_from_row(row) for row in rows]


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


def _connect_postgres(database_url: str) -> Any:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("psycopg[binary] is required for Supabase Postgres") from exc

    return psycopg.connect(database_url, row_factory=dict_row)


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
