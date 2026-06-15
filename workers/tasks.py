"""Celery task definitions."""
from __future__ import annotations

import logging

from celery import shared_task

from infrastructure.redis import get_redis_client
from shared.config import get_app_config

logger = logging.getLogger(__name__)
_COORDINATOR_LOCK_KEY = "lidscout:pipeline:coordinator:lock"
_MARKET_RUN_LOCK_PREFIX = "lidscout:pipeline:market-run:"


@shared_task(
    bind=True,
    name="workers.tasks.run_pipeline_for_market",
    max_retries=3,
    default_retry_delay=60,
)
def run_pipeline_for_market(self, market_id: str) -> dict:
    """Run the full research pipeline for one market."""
    import sys as _sys, os as _os
    _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    from workers.jobs import run_configured_daily_pipeline, _pipeline_job_summary
    run_lock_key = _market_run_lock_key(market_id)
    if not _acquire_market_run_lock(run_lock_key):
        logger.info("pipeline skipped market_id=%s reason=already_running", market_id)
        return {"skipped": "already_running"}
    logger.info("pipeline starting market_id=%s attempt=%d", market_id, self.request.retries + 1)
    try:
        result = run_configured_daily_pipeline(market_id=market_id)
        summary = _pipeline_job_summary(result)
        logger.info("pipeline complete market_id=%s summary=%s", market_id, summary)
        return summary
    except ValueError as exc:
        # Config error (e.g. missing REPORT_RECIPIENT) — don't retry, fix config
        logger.error("pipeline config error market_id=%s error=%s", market_id, exc)
        raise
    except Exception as exc:
        # Transient error — retry with exponential backoff
        delay = 60 * (2 ** self.request.retries)
        logger.warning(
            "pipeline failed market_id=%s attempt=%d retrying_in=%ds error=%s",
            market_id, self.request.retries + 1, delay, exc,
        )
        raise self.retry(exc=exc, countdown=delay)
    finally:
        _release_market_run_lock(run_lock_key)


@shared_task(
    name="workers.tasks.run_daily_pipeline_all",
)
def run_daily_pipeline_all() -> dict:
    """Coordinator task: enqueue one pipeline run per user_niche that has sources."""
    import sys as _sys, os as _os
    _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    from api.dependencies import build_signal_api_dependencies
    from workers.jobs import _enabled_source_count_for_user_niche

    lock_state = _acquire_coordinator_lock()
    if lock_state is False:
        logger.warning("daily coordinator skipped because another coordinator holds the lock")
        return {"enqueued": 0, "total_user_niches": 0, "skipped": "lock_held"}

    deps = build_signal_api_dependencies()
    all_niches = deps.user_niche_repository.list_all_user_niches()
    active = [
        un for un in all_niches
        if un.template_niche_id is not None
        and _enabled_source_count_for_user_niche(deps, un) > 0
    ]

    for user_niche in active:
        run_pipeline_for_market.delay(user_niche.id)
        logger.info("enqueued pipeline user_niche_id=%s job=%s", user_niche.id, user_niche.job)

    logger.info("daily coordinator enqueued %d/%d user_niches", len(active), len(all_niches))
    return {"enqueued": len(active), "total_user_niches": len(all_niches)}


def _acquire_coordinator_lock() -> bool | None:
    """Acquire a short-lived Redis lock that prevents duplicate Beat fan-out."""
    client = get_redis_client()
    if client is None:
        logger.warning("daily coordinator lock unavailable because REDIS_URL is not set")
        return None
    ttl_seconds = get_app_config().PIPELINE_COORDINATOR_LOCK_SECONDS
    try:
        acquired = client.set(
            _COORDINATOR_LOCK_KEY,
            "1",
            nx=True,
            ex=max(ttl_seconds, 60),
        )
    except Exception as exc:
        logger.warning("daily coordinator lock unavailable error=%s", exc)
        return None
    return True if acquired else False


def _market_run_lock_key(market_id: str) -> str:
    return f"{_MARKET_RUN_LOCK_PREFIX}{market_id}"


def _market_run_lock_ttl_seconds() -> int:
    config = get_app_config()
    return max(
        config.PIPELINE_COORDINATOR_LOCK_SECONDS,
        config.PIPELINE_MANUAL_TRIGGER_COOLDOWN_SECONDS,
        60,
    )


def _acquire_market_run_lock(lock_key: str) -> bool:
    client = get_redis_client()
    if client is None:
        return True
    try:
        acquired = client.set(
            lock_key,
            "1",
            nx=True,
            ex=_market_run_lock_ttl_seconds(),
        )
    except Exception as exc:
        logger.warning("pipeline run lock unavailable error=%s", exc)
        return True
    return bool(acquired)


def _release_market_run_lock(lock_key: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        client.delete(lock_key)
    except Exception as exc:
        logger.warning("pipeline run lock release failed error=%s", exc)
