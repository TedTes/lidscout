#!/usr/bin/env bash
set -euo pipefail

SERVICE_TYPE="${SERVICE_TYPE:-api}"

if [ "$SERVICE_TYPE" = "worker" ]; then
  # Combined worker + Beat — safe while only one worker instance is running.
  # When scaling to multiple worker instances, run Beat as a separate service
  # (set SERVICE_TYPE=beat) to avoid double-scheduling.
  exec celery -A workers.celery_app worker --beat --loglevel=info --concurrency="${WORKER_CONCURRENCY:-1}"
elif [ "$SERVICE_TYPE" = "beat" ]; then
  exec celery -A workers.celery_app beat --loglevel=info
else
  exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi
