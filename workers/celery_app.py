"""Celery application instance and configuration."""
from __future__ import annotations

import logging

from celery import Celery

from shared.config import get_app_config

logger = logging.getLogger(__name__)


def _broker_url() -> str:
    url = get_app_config().REDIS_URL
    if not url:
        raise RuntimeError("REDIS_URL must be set to start the Celery worker")
    return url


def create_celery_app() -> Celery:
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
    )
    return app


celery_app = create_celery_app()
