# Public Beta Readiness

Use this checklist before inviting external users.

## Automated Checks

Run:

```bash
python -m workers.check_public_beta_readiness
python -m workers.jobs check
python -m pytest tests/test_source_api_quality.py tests/test_opportunity_quality_evaluation.py tests/test_celery_tasks.py
cd web_client && npm run build
```

The beta readiness command should not return `status: "fail"`.

## Deployment Safety

- Confirm `REDIS_URL` is configured for worker services.
- Confirm `PIPELINE_EMAIL_ENABLED=false` unless beta email digests are intentional.
- Confirm only one Beat scheduler is active. If `SERVICE_TYPE=worker`, keep one worker replica. If scaling workers, run a separate `SERVICE_TYPE=beat` service.
- Keep `WORKER_CONCURRENCY=1` until database pool headroom is verified.
- Keep `PIPELINE_COORDINATOR_LOCK_SECONDS` long enough for a full scan.

## Source Quality

- Monitored sources should appear before suggested sources.
- Blocked, disabled, or proxy-required sources should be visible and removable.
- Default enabled sources should be gate-free or previously verified.
- A first scan should explain what is being scanned and when results should appear.

## Opportunity Quality

- Avoid promoting one-post, one-source themes into opportunities.
- Check rejected theme reasons in agent activity after a scan.
- Run `workers.evaluate_opportunity_quality` against any manually curated QA fixture before relaxing thresholds.

## Product Copy

Position LidScout as:

> An AI research agent that monitors public market signals and surfaces product opportunities.

Avoid presenting it as a generic analytics dashboard.
