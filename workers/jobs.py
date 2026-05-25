"""Background jobs for signal detection workflows."""
from __future__ import annotations

import json
import sys

from api.dependencies import build_signal_api_dependencies
from api.schemas import InteractionExtractionRequest, InteractionExtractionResponse
from api.routes.signals import SignalApiDependencies
from application.factory import ServiceFactory
from shared.config import get_app_config
from workers.run_daily_pipeline import PipelineConfig, PipelineRunResult, run_daily_pipeline


async def extract_public_activity_signals(
    request: InteractionExtractionRequest,
) -> InteractionExtractionResponse:
    """Run the extraction pipeline for supplied public activity sources."""
    extractor = ServiceFactory.get_interaction_extraction_service()
    return await extractor.extract(request)


def run_configured_daily_pipeline(
    recipient: str | None = None,
    market_id: str | None = None,
    dependencies: SignalApiDependencies | None = None,
) -> PipelineRunResult:
    """Run the pipeline from persisted, enabled source locators."""
    app_config = get_app_config()
    resolved_recipient = recipient or app_config.REPORT_RECIPIENT
    if not resolved_recipient:
        raise ValueError("REPORT_RECIPIENT is required for background pipeline runs")

    runtime_dependencies = dependencies or build_signal_api_dependencies(app_config)
    _ensure_background_pipeline_dependencies(runtime_dependencies)

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
            competitor_repository=runtime_dependencies.competitor_repository,
            market_repository=runtime_dependencies.market_repository,
            monitored_source_repository=runtime_dependencies.monitored_source_repository,
            source_health_repository=runtime_dependencies.source_health_repository,
            source_locator_repository=runtime_dependencies.source_locator_repository,
            llm_client=runtime_dependencies.llm_client,
            relevance_llm_client=runtime_dependencies.relevance_llm_client,
            embedding_client=runtime_dependencies.embedding_client,
            email_client=runtime_dependencies.email_client,
            recipient=resolved_recipient,
            source_adapters=runtime_dependencies.source_adapters,
            market_id=market_id,
        )
    )


def check_worker_readiness(
    market_id: str | None = None,
    dependencies: SignalApiDependencies | None = None,
) -> dict[str, object]:
    """Return deploy-time readiness details for the scheduled worker."""
    app_config = get_app_config()
    runtime_dependencies = dependencies or build_signal_api_dependencies(app_config)
    _ensure_background_pipeline_dependencies(runtime_dependencies)

    monitored_sources = (
        runtime_dependencies.monitored_source_repository.list_monitored_sources(
            enabled=True,
            market_id=market_id,
        )
    )
    source_locators = []
    if not monitored_sources:
        source_locators = (
            runtime_dependencies.source_locator_repository.list_source_locators(
                enabled=True,
            )
        )

    source_count = len(monitored_sources) or len(source_locators)
    return {
        "ready": source_count > 0,
        "market_id": market_id,
        "enabled_monitored_source_count": len(monitored_sources),
        "enabled_source_locator_count": len(source_locators),
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
        market_id = args[1] if len(args) > 1 else None
        result = check_worker_readiness(market_id=market_id)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["ready"] else 1

    recipient = args[1] if len(args) > 1 else None
    market_id = args[2] if len(args) > 2 else None
    result = run_configured_daily_pipeline(recipient, market_id)
    print(json.dumps(_pipeline_job_summary(result), sort_keys=True))
    return 0


def _ensure_background_pipeline_dependencies(
    dependencies: SignalApiDependencies,
) -> None:
    missing = []
    if dependencies.llm_client is None:
        missing.append("llm_client")
    if dependencies.embedding_client is None:
        missing.append("embedding_client")
    if dependencies.email_client is None:
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
