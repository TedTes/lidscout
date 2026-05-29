"""Celery task definitions."""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="workers.tasks.run_pipeline_for_market",
    max_retries=3,
    default_retry_delay=60,
)
def run_pipeline_for_market(self, market_id: str) -> dict:
    """Run the full research pipeline for one market."""
    from workers.jobs import run_configured_daily_pipeline, _pipeline_job_summary

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


@shared_task(
    name="workers.tasks.run_daily_pipeline_all",
)
def run_daily_pipeline_all() -> dict:
    """Coordinator task: enqueue one pipeline run per user_niche that has sources."""
    from api.dependencies import build_signal_api_dependencies

    deps = build_signal_api_dependencies()
    all_niches = deps.user_niche_repository.list_all_user_niches()
    active = [
        un for un in all_niches
        if un.template_niche_id is not None
        and deps.niche_source_repository.list_niche_sources(un.template_niche_id)
    ]

    for user_niche in active:
        run_pipeline_for_market.delay(user_niche.id)
        logger.info("enqueued pipeline user_niche_id=%s job=%s", user_niche.id, user_niche.job)

    logger.info("daily coordinator enqueued %d/%d user_niches", len(active), len(all_niches))
    return {"enqueued": len(active), "total_user_niches": len(all_niches)}
