import os
import unittest
from unittest.mock import MagicMock, patch

import redis as redis_lib

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


def _eager_app():
    """Return the Celery app configured for synchronous in-process execution."""
    from workers.celery_app import celery_app
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=False)
    return celery_app


class EnqueuePipelineTests(unittest.TestCase):
    """T7.1 — _enqueue_pipeline wires correctly to Celery and handles Redis being down."""

    def test_enqueues_task_when_redis_available(self):
        mock_task = MagicMock()
        with patch("workers.tasks.run_pipeline_for_market", mock_task):
            from api.routes.signals import _enqueue_pipeline
            _enqueue_pipeline("market-123")
        mock_task.delay.assert_called_once_with("market-123")

    def test_does_not_raise_when_redis_unavailable(self):
        mock_task = MagicMock()
        mock_task.delay.side_effect = redis_lib.exceptions.ConnectionError("refused")
        with patch("workers.tasks.run_pipeline_for_market", mock_task):
            from api.routes.signals import _enqueue_pipeline
            _enqueue_pipeline("market-123")  # must not raise


class RunPipelineForMarketTaskTests(unittest.TestCase):
    """T7.1 / T7.3 — task executes pipeline and retries on transient failures."""

    def setUp(self):
        _eager_app()

    def test_returns_pipeline_summary_on_success(self):
        mock_result = MagicMock()
        mock_summary = {"extracted_count": 5, "email_sent": True}
        with (
            patch("workers.jobs.run_configured_daily_pipeline", return_value=mock_result),
            patch("workers.jobs._pipeline_job_summary", return_value=mock_summary),
        ):
            from workers.tasks import run_pipeline_for_market
            result = run_pipeline_for_market.apply(args=["market-abc"]).get()
        self.assertEqual(result, mock_summary)

    def test_does_not_retry_on_value_error(self):
        """Config errors (missing REPORT_RECIPIENT) should not consume retry budget."""
        with patch(
            "workers.jobs.run_configured_daily_pipeline",
            side_effect=ValueError("REPORT_RECIPIENT is required"),
        ):
            from workers.tasks import run_pipeline_for_market
            result = run_pipeline_for_market.apply(args=["market-abc"])
        self.assertTrue(result.failed())
        self.assertIsInstance(result.result, ValueError)

    def test_retries_on_transient_exception(self):
        call_count = {"n": 0}

        def flaky(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise RuntimeError("temporary network error")
            return MagicMock()

        with (
            patch("workers.jobs.run_configured_daily_pipeline", side_effect=flaky),
            patch("workers.jobs._pipeline_job_summary", return_value={}),
        ):
            from workers.tasks import run_pipeline_for_market
            result = run_pipeline_for_market.apply(args=["market-abc"])
        self.assertEqual(call_count["n"], 2)
        self.assertTrue(result.successful())


class RunDailyPipelineAllTests(unittest.TestCase):
    """T7.2 — coordinator fans out one task per active market."""

    def setUp(self):
        _eager_app()

    def _make_market(self, market_id: str) -> MagicMock:
        m = MagicMock()
        m.id = market_id
        m.name = f"Market {market_id}"
        return m

    def test_enqueues_task_for_each_active_market(self):
        markets = [self._make_market("m1"), self._make_market("m2"), self._make_market("m3")]

        def has_sources(market_id, enabled):
            return [MagicMock()] if market_id in ("m1", "m3") else []

        mock_deps = MagicMock()
        mock_deps.market_repository.list_markets.return_value = markets
        mock_deps.monitored_source_repository.list_monitored_sources.side_effect = (
            lambda market_id, enabled: has_sources(market_id, enabled)
        )

        enqueued = []
        mock_task = MagicMock()
        mock_task.delay.side_effect = lambda mid: enqueued.append(mid)

        with (
            patch("api.dependencies.build_signal_api_dependencies", return_value=mock_deps),
            patch("workers.tasks.run_pipeline_for_market", mock_task),
        ):
            from workers.tasks import run_daily_pipeline_all
            result = run_daily_pipeline_all.apply().get()

        self.assertEqual(sorted(enqueued), ["m1", "m3"])
        self.assertEqual(result["enqueued"], 2)
        self.assertEqual(result["total_markets"], 3)

    def test_returns_zero_when_no_active_markets(self):
        mock_deps = MagicMock()
        mock_deps.market_repository.list_markets.return_value = []

        with patch("api.dependencies.build_signal_api_dependencies", return_value=mock_deps):
            from workers.tasks import run_daily_pipeline_all
            result = run_daily_pipeline_all.apply().get()

        self.assertEqual(result["enqueued"], 0)
        self.assertEqual(result["total_markets"], 0)


class BeatScheduleTests(unittest.TestCase):
    """T3.1 — Beat schedule parses PIPELINE_SCHEDULE cron string correctly."""

    def test_default_schedule_is_08_00_utc(self):
        from workers.celery_app import celery_app
        entry = celery_app.conf.beat_schedule["run-daily-pipeline"]
        self.assertEqual(entry["task"], "workers.tasks.run_daily_pipeline_all")
        schedule = entry["schedule"]
        self.assertEqual(str(schedule._orig_minute), "0")
        self.assertEqual(str(schedule._orig_hour), "8")

    def test_custom_schedule_is_parsed(self):
        from workers.celery_app import _beat_schedule
        entry = _beat_schedule("30 6 * * *")["run-daily-pipeline"]
        schedule = entry["schedule"]
        self.assertEqual(str(schedule._orig_minute), "30")
        self.assertEqual(str(schedule._orig_hour), "6")

    def test_invalid_schedule_raises(self):
        from workers.celery_app import _beat_schedule
        with self.assertRaises(ValueError):
            _beat_schedule("bad")


if __name__ == "__main__":
    unittest.main()
