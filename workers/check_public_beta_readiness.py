"""Public beta readiness checks for the scheduled research agent."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

from workers.jobs import check_worker_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether the worker/API runtime is safe for public beta.",
    )
    parser.add_argument(
        "--market-id",
        default=None,
        help="Optional user niche/market id to scope source readiness checks.",
    )
    args = parser.parse_args(argv)

    readiness = check_worker_readiness(user_niche_id=args.market_id)
    report = build_public_beta_readiness_report(
        readiness,
        service_type=os.getenv("SERVICE_TYPE"),
        worker_concurrency=os.getenv("WORKER_CONCURRENCY"),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["status"] == "fail" else 0


def build_public_beta_readiness_report(
    readiness: dict[str, Any],
    *,
    service_type: str | None = None,
    worker_concurrency: str | None = None,
) -> dict[str, Any]:
    """Convert runtime diagnostics into beta release safety checks."""
    checks: list[dict[str, str]] = []

    def add(level: str, key: str, message: str) -> None:
        checks.append({"level": level, "key": key, "message": message})

    if not readiness.get("redis_configured"):
        add("fail", "redis", "REDIS_URL must be configured for Celery scheduling.")
    else:
        add("pass", "redis", "Redis is configured.")

    missing = set(readiness.get("missing_dependencies") or [])
    for dependency in sorted(missing):
        add("fail", f"dependency:{dependency}", f"Missing {dependency}.")
    if not missing:
        add("pass", "dependencies", "Pipeline dependencies are configured.")

    if int(readiness.get("enabled_niche_source_count") or 0) < 1:
        add("fail", "sources", "At least one enabled niche source is required.")
    else:
        add("pass", "sources", "Enabled niche sources are available.")

    if readiness.get("email_enabled"):
        add(
            "warn",
            "email",
            "PIPELINE_EMAIL_ENABLED is true; confirm beta users should receive digests.",
        )
    else:
        add("pass", "email", "Pipeline email sending is disabled by default.")

    lock_seconds = int(readiness.get("coordinator_lock_seconds") or 0)
    if lock_seconds < 1800:
        add(
            "warn",
            "coordinator_lock",
            "Coordinator lock is under 30 minutes; long scans may double-run.",
        )
    else:
        add("pass", "coordinator_lock", "Coordinator lock is long enough for MVP scans.")

    normalized_service_type = (service_type or "").strip().lower()
    if normalized_service_type == "worker":
        add(
            "warn",
            "beat",
            "SERVICE_TYPE=worker runs Beat inside the worker; keep one replica or split Beat.",
        )
    elif normalized_service_type == "beat":
        add("pass", "beat", "Beat is split into its own service.")
    else:
        add(
            "warn",
            "service_type",
            "SERVICE_TYPE is not set; confirm API, worker, and Beat services explicitly.",
        )

    if worker_concurrency and worker_concurrency.strip() != "1":
        add(
            "warn",
            "worker_concurrency",
            "Worker concurrency is above 1; confirm database pool capacity first.",
        )

    status = "pass"
    if any(check["level"] == "fail" for check in checks):
        status = "fail"
    elif any(check["level"] == "warn" for check in checks):
        status = "warn"

    return {
        "status": status,
        "ready": readiness.get("ready", False),
        "pipeline_schedule": readiness.get("pipeline_schedule"),
        "checks": checks,
    }


if __name__ == "__main__":
    raise SystemExit(main())
