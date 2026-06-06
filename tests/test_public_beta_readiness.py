from workers.check_public_beta_readiness import build_public_beta_readiness_report


def test_public_beta_readiness_fails_without_runtime_dependencies() -> None:
    report = build_public_beta_readiness_report(
        {
            "ready": False,
            "redis_configured": False,
            "missing_dependencies": ["llm_client", "source_adapters"],
            "enabled_niche_source_count": 0,
            "email_enabled": False,
            "coordinator_lock_seconds": 3600,
            "pipeline_schedule": "0 8 * * *",
        },
        service_type=None,
        worker_concurrency=None,
    )

    assert report["status"] == "fail"
    keys = {check["key"] for check in report["checks"]}
    assert "redis" in keys
    assert "dependency:llm_client" in keys
    assert "dependency:source_adapters" in keys
    assert "sources" in keys


def test_public_beta_readiness_warns_for_combined_worker_beat() -> None:
    report = build_public_beta_readiness_report(
        {
            "ready": True,
            "redis_configured": True,
            "missing_dependencies": [],
            "enabled_niche_source_count": 4,
            "email_enabled": False,
            "coordinator_lock_seconds": 3600,
            "pipeline_schedule": "0 8 * * *",
        },
        service_type="worker",
        worker_concurrency="1",
    )

    assert report["status"] == "warn"
    assert any(check["key"] == "beat" for check in report["checks"])


def test_public_beta_readiness_passes_split_beat_configuration() -> None:
    report = build_public_beta_readiness_report(
        {
            "ready": True,
            "redis_configured": True,
            "missing_dependencies": [],
            "enabled_niche_source_count": 4,
            "email_enabled": False,
            "coordinator_lock_seconds": 3600,
            "pipeline_schedule": "0 8 * * *",
        },
        service_type="beat",
        worker_concurrency="1",
    )

    assert report["status"] == "pass"
