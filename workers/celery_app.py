"""Celery application instance and configuration."""
from __future__ import annotations

import logging

from celery import Celery
from celery.schedules import crontab

from shared.config import get_app_config

logger = logging.getLogger(__name__)


def _broker_url() -> str:
    url = get_app_config().REDIS_URL
    if not url:
        raise RuntimeError("REDIS_URL must be set to start the Celery worker")
    return url


def _beat_schedule(pipeline_schedule: str) -> dict:
    """Build Beat schedule from a 'minute hour * * *' cron string."""
    parts = pipeline_schedule.split()
    if len(parts) < 2:
        raise ValueError(f"Invalid PIPELINE_SCHEDULE: {pipeline_schedule!r}")
    minute, hour = parts[0], parts[1]
    return {
        "run-daily-pipeline": {
            "task": "workers.tasks.run_daily_pipeline_all",
            "schedule": crontab(minute=minute, hour=hour),
        }
    }


def create_celery_app() -> Celery:
    config = get_app_config()
    broker = _broker_url()
    app = Celery(
        "lidscout",
        broker=broker,
        backend=broker,
        include=["workers.tasks"],
    )
    app.conf.update(
        # Serialization
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # Reliability
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        # Memory management — recycle subprocesses after N tasks to prevent leak
        worker_max_tasks_per_child=50,
        # Time
        timezone="UTC",
        enable_utc=True,
        # Result expiry — keep task results in Redis for 24 hours
        result_expires=86400,
        # Beat schedule — derived from PIPELINE_SCHEDULE env var
        beat_schedule=_beat_schedule(config.PIPELINE_SCHEDULE),
    )
    return app


celery_app = create_celery_app()
