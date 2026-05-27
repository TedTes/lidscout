"""Redis client singleton backed by a connection pool."""
from __future__ import annotations

import logging

import redis
from redis import Redis

logger = logging.getLogger(__name__)

_client: Redis | None = None


def get_redis_client() -> Redis | None:
    """Return the shared Redis client, or None if REDIS_URL is not configured.

    Builds a connection pool on first call and reuses it for the lifetime of
    the process. Callers must check for None before use.
    """
    global _client
    if _client is not None:
        return _client

    from shared.config import get_app_config
    redis_url = get_app_config().REDIS_URL
    if not redis_url:
        logger.debug("REDIS_URL not set — Redis client unavailable")
        return None

    pool = redis.ConnectionPool.from_url(
        redis_url,
        max_connections=10,
        decode_responses=True,
    )
    _client = Redis(connection_pool=pool)
    return _client
