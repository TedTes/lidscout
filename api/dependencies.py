"""Runtime dependency wiring for API routes."""
from adapters.hackernews import HackerNewsActivityAdapter
from adapters.reddit import RedditActivityAdapter
from api.routes.signals import SignalApiDependencies
from infrastructure.db import (
    PostgresClusterRepository,
    PostgresPostRepository,
    PostgresScoreRepository,
    PostgresSignalRepository,
)
from shared.config import AppConfig, get_app_config


def build_signal_api_dependencies(
    config: AppConfig | None = None,
) -> SignalApiDependencies:
    """Build signal API dependencies from runtime configuration."""
    app_config = config or get_app_config()
    database_url = app_config.DATABASE_URL.strip()
    if not _is_postgres_url(database_url):
        raise ValueError("DATABASE_URL must be a Supabase/Postgres URL")

    return SignalApiDependencies(
        post_repository=PostgresPostRepository(database_url),
        signal_repository=PostgresSignalRepository(database_url),
        score_repository=PostgresScoreRepository(database_url),
        cluster_repository=PostgresClusterRepository(database_url),
        reddit_adapter=RedditActivityAdapter(),
        hackernews_adapter=HackerNewsActivityAdapter(),
    )


def _is_postgres_url(database_url: str) -> bool:
    return database_url.startswith(("postgresql://", "postgres://"))
