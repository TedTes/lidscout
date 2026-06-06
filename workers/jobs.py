"""Background jobs for signal detection workflows.

Scheduled pipeline execution is handled by Celery Beat via workers/tasks.py.
This module is kept as a manual CLI escape hatch only:

    python -m workers.jobs run-daily-pipeline [recipient] [market_id]
    python -m workers.jobs check [market_id]

Do NOT schedule this via Railway Cron — that role belongs to Beat.
"""
from __future__ import annotations

import json
import sys

from shared.config import get_app_config
from workers.run_daily_pipeline import PipelineConfig, PipelineRunResult, run_daily_pipeline


async def extract_public_activity_signals(request: object) -> object:
    """Run the extraction pipeline for supplied public activity sources."""
    from api.schemas import InteractionExtractionRequest, InteractionExtractionResponse  # noqa: F401
    from application.factory import ServiceFactory
    extractor = ServiceFactory.get_interaction_extraction_service()
    return await extractor.extract(request)  # type: ignore[arg-type]


def run_configured_daily_pipeline(
    recipient: str | None = None,
    market_id: str | None = None,
    dependencies: object | None = None,
) -> PipelineRunResult:
    """Run the pipeline from persisted, enabled source locators."""
    app_config = get_app_config()
    resolved_recipient = recipient or app_config.REPORT_RECIPIENT
    if app_config.PIPELINE_EMAIL_ENABLED and not resolved_recipient:
        raise ValueError("REPORT_RECIPIENT is required for background pipeline runs")
    resolved_recipient = resolved_recipient or ""

    from api.dependencies import build_signal_api_dependencies
    runtime_dependencies = dependencies or build_signal_api_dependencies(app_config)
    _ensure_background_pipeline_dependencies(
        runtime_dependencies,
        require_email=app_config.PIPELINE_EMAIL_ENABLED,
    )

    return run_daily_pipeline(
        PipelineConfig(
            post_repository=runtime_dependencies.post_repository,
            signal_repository=runtime_dependencies.signal_repository,
            score_repository=runtime_dependencies.score_repository,
            cluster_repository=runtime_dependencies.cluster_repository,
            opportunity_repository=runtime_dependencies.opportunity_repository,
            pipeline_run_metrics_repository=(
                runtime_dependencies.pipeline_run_metrics_repository
            ),
            agent_preferences_repository=(
                runtime_dependencies.agent_preferences_repository
            ),
            agent_activity_repository=runtime_dependencies.agent_activity_repository,
            agent_alert_repository=runtime_dependencies.agent_alert_repository,
            agent_follow_up_repository=runtime_dependencies.agent_follow_up_repository,
            agent_action_repository=runtime_dependencies.agent_action_repository,
            niche_source_repository=runtime_dependencies.niche_source_repository,
            user_niche_repository=runtime_dependencies.user_niche_repository,
            source_locator_repository=runtime_dependencies.source_locator_repository,
            llm_client=runtime_dependencies.llm_client,
            relevance_llm_client=runtime_dependencies.relevance_llm_client,
            embedding_client=runtime_dependencies.embedding_client,
            email_client=runtime_dependencies.email_client,
            recipient=resolved_recipient,
            send_email=app_config.PIPELINE_EMAIL_ENABLED,
            allow_auth_sources=bool(
                app_config.REDDIT_CLIENT_ID and app_config.REDDIT_CLIENT_SECRET
            ),
            source_adapters=runtime_dependencies.source_adapters,
            user_niche_id=market_id,
        )
    )


def check_worker_readiness(
    user_niche_id: str | None = None,
    dependencies: object | None = None,
) -> dict[str, object]:
    """Return deploy-time readiness details for the scheduled worker."""
    from api.dependencies import build_signal_api_dependencies
    app_config = get_app_config()
    runtime_dependencies = dependencies or build_signal_api_dependencies(app_config)
    _ensure_background_pipeline_dependencies(runtime_dependencies)

    niche_source_count = 0
    if user_niche_id is not None:
        user_niche = runtime_dependencies.user_niche_repository.get_user_niche(user_niche_id)
        if user_niche and user_niche.template_niche_id:
            niche_source_count = len(
                runtime_dependencies.niche_source_repository.list_niche_sources(
                    user_niche.template_niche_id,
                    enabled=True,
                )
            )
    else:
        all_niches = runtime_dependencies.user_niche_repository.list_all_user_niches()
        niche_source_count = sum(
            len(
                runtime_dependencies.niche_source_repository.list_niche_sources(
                    un.template_niche_id,
                    enabled=True,
                )
            )
            for un in all_niches
            if un.template_niche_id
        )

    return {
        "ready": niche_source_count > 0,
        "user_niche_id": user_niche_id,
        "enabled_niche_source_count": niche_source_count,
        "source_adapter_count": len(runtime_dependencies.source_adapters),
        "has_llm_client": runtime_dependencies.llm_client is not None,
        "has_relevance_llm_client": (
            runtime_dependencies.relevance_llm_client is not None
        ),
        "has_embedding_client": runtime_dependencies.embedding_client is not None,
        "has_email_client": runtime_dependencies.email_client is not None,
    }


def main(argv: list[str] | None = None) -> int:
    """Run worker jobs from the command line."""
    args = argv if argv is not None else sys.argv[1:]
    command = args[0] if args else "run-daily-pipeline"
    if command not in {"run-daily-pipeline", "check"}:
        raise ValueError(f"Unknown worker job: {command}")

    if command == "check":
        user_niche_id = args[1] if len(args) > 1 else None
        result = check_worker_readiness(user_niche_id=user_niche_id)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["ready"] else 1

    recipient = args[1] if len(args) > 1 else None
    market_id = args[2] if len(args) > 2 else None
    result = run_configured_daily_pipeline(recipient, market_id)
    print(json.dumps(_pipeline_job_summary(result), sort_keys=True))
    return 0


def _ensure_background_pipeline_dependencies(
    dependencies: SignalApiDependencies,
    *,
    require_email: bool = True,
) -> None:
    missing = []
    if dependencies.llm_client is None:
        missing.append("llm_client")
    if dependencies.embedding_client is None:
        missing.append("embedding_client")
    if require_email and dependencies.email_client is None:
        missing.append("email_client")
    if not dependencies.source_adapters:
        missing.append("source_adapters")

    if missing:
        raise RuntimeError(
            f"Background pipeline dependencies are not configured: {', '.join(missing)}"
        )


def _pipeline_job_summary(result: PipelineRunResult) -> dict[str, object]:
    return {
        "fetched_count": result.fetched_count,
        "fetch_failed_count": result.fetch_failed_count,
        "rule_filtered_count": result.rule_filtered_count,
        "llm_filtered_count": result.llm_filtered_count,
        "relevance_failed_count": result.relevance_failed_count,
        "extraction_attempted_count": result.extraction_attempted_count,
        "extracted_count": result.extracted_count,
        "clustered_count": result.clustered_count,
        "opportunity_synthesized_count": (
            result.opportunity_synthesis_result.synthesized_count
        ),
        "email_sent": result.email_result.sent,
        "email_error": result.email_result.error,
    }


if __name__ == "__main__":
    raise SystemExit(main())
