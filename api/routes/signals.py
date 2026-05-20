"""API endpoints for market signal workflows."""
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from application.ports import (
    ClusterRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
)
from application.reporting import MarketSignalReport, ReportingService
from domain.cluster import SignalCluster
from domain.signal import Signal
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
)
from infrastructure.email import EmailClient, EmailSendResult
from infrastructure.llm import EmbeddingClient, LLMClient
from workers.run_daily_pipeline import (
    HackerNewsPostAdapter,
    HackerNewsSourceConfig,
    PipelineConfig,
    PipelineRunResult,
    RedditPostAdapter,
    RedditSourceConfig,
    run_daily_pipeline,
)

router = APIRouter(tags=["signals"])


class PipelineRedditSourceRequest(BaseModel):
    """Reddit source request for a pipeline run."""

    subreddit: str
    limit: int | None = Field(default=None, ge=1)


class PipelineHackerNewsSourceRequest(BaseModel):
    """Hacker News source request for a pipeline run."""

    config: str = "top"
    limit: int | None = Field(default=None, ge=1)


class PipelineRunRequest(BaseModel):
    """HTTP request body for running the signal pipeline."""

    recipient: str = Field(min_length=1)
    reddit_sources: list[PipelineRedditSourceRequest] = Field(default_factory=list)
    hackernews_sources: list[PipelineHackerNewsSourceRequest] = Field(default_factory=list)
    default_limit: int = Field(default=25, ge=1)
    similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)


@dataclass
class SignalApiDependencies:
    """Runtime dependencies for signal API routes."""

    post_repository: PostRepository = field(default_factory=InMemoryPostRepository)
    signal_repository: SignalRepository = field(default_factory=InMemorySignalRepository)
    score_repository: ScoreRepository = field(default_factory=InMemoryScoreRepository)
    cluster_repository: ClusterRepository = field(default_factory=InMemoryClusterRepository)
    reporting_service: ReportingService = field(default_factory=ReportingService)
    reddit_adapter: RedditPostAdapter | None = None
    hackernews_adapter: HackerNewsPostAdapter | None = None
    llm_client: LLMClient | None = None
    embedding_client: EmbeddingClient | None = None
    email_client: EmailClient | None = None


_dependencies = SignalApiDependencies()


def get_signal_api_dependencies() -> SignalApiDependencies:
    """Return configured signal API dependencies."""
    return _dependencies


@router.get("/signals")
async def list_signals(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return persisted extracted signals."""
    return {
        "signals": [
            _serialize_signal(signal)
            for signal in dependencies.signal_repository.list_signals()
        ]
    }


@router.get("/clusters")
async def list_clusters(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return persisted signal clusters."""
    return {
        "clusters": [
            _serialize_cluster(cluster)
            for cluster in dependencies.cluster_repository.list_clusters()
        ]
    }


@router.get("/reports/latest")
async def get_latest_report(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Generate and return the latest report from persisted clusters."""
    report = dependencies.reporting_service.generate(
        dependencies.cluster_repository.list_clusters()
    )
    return _serialize_report(report)


@router.post("/pipeline/run")
async def run_pipeline(
    request: PipelineRunRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Run the daily pipeline from configured dependencies and requested sources."""
    _ensure_pipeline_dependencies(dependencies, request)
    result = run_daily_pipeline(
        PipelineConfig(
            post_repository=dependencies.post_repository,
            signal_repository=dependencies.signal_repository,
            score_repository=dependencies.score_repository,
            cluster_repository=dependencies.cluster_repository,
            llm_client=dependencies.llm_client,
            embedding_client=dependencies.embedding_client,
            email_client=dependencies.email_client,
            recipient=request.recipient,
            reddit_adapter=dependencies.reddit_adapter,
            hackernews_adapter=dependencies.hackernews_adapter,
            reddit_sources=[
                RedditSourceConfig(source.subreddit, source.limit)
                for source in request.reddit_sources
            ],
            hackernews_sources=[
                HackerNewsSourceConfig(source.config, source.limit)
                for source in request.hackernews_sources
            ],
            default_limit=request.default_limit,
            similarity_threshold=request.similarity_threshold,
        )
    )
    return _serialize_pipeline_result(result)


def _ensure_pipeline_dependencies(
    dependencies: SignalApiDependencies,
    request: PipelineRunRequest,
) -> None:
    missing = []
    if dependencies.llm_client is None:
        missing.append("llm_client")
    if dependencies.embedding_client is None:
        missing.append("embedding_client")
    if dependencies.email_client is None:
        missing.append("email_client")
    if request.reddit_sources and dependencies.reddit_adapter is None:
        missing.append("reddit_adapter")
    if request.hackernews_sources and dependencies.hackernews_adapter is None:
        missing.append("hackernews_adapter")

    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline dependencies are not configured: {', '.join(missing)}",
        )


def _serialize_signal(signal: Signal) -> dict[str, Any]:
    return {
        "id": signal.id,
        "post_id": signal.post_id,
        "pain": signal.pain,
        "user_type": signal.user_type,
        "job_to_be_done": signal.job_to_be_done,
        "current_workaround": signal.current_workaround,
        "urgency": signal.urgency,
        "severity": signal.severity,
        "willingness_to_pay": signal.willingness_to_pay,
        "category": signal.category,
        "confidence": signal.confidence,
    }


def _serialize_cluster(cluster: SignalCluster) -> dict[str, Any]:
    return {
        "id": cluster.id,
        "theme": cluster.theme,
        "summary": cluster.summary,
        "signal_ids": cluster.signal_ids,
        "frequency": cluster.frequency,
        "average_score": cluster.average_score,
        "top_examples": cluster.top_examples,
    }


def _serialize_report(report: MarketSignalReport) -> dict[str, Any]:
    return {
        "title": report.title,
        "generated_at": report.generated_at.isoformat(),
        "top_clusters": [
            _serialize_cluster(cluster)
            for cluster in report.top_clusters
        ],
        "emerging_pains": report.emerging_pains,
        "recommended_opportunities": report.recommended_opportunities,
    }


def _serialize_email_result(result: EmailSendResult) -> dict[str, Any]:
    return {
        "recipient": result.recipient,
        "subject": result.subject,
        "sent": result.sent,
        "error": result.error,
    }


def _serialize_pipeline_result(result: PipelineRunResult) -> dict[str, Any]:
    return {
        "fetched_count": result.fetched_count,
        "fetch_failed_count": result.fetch_failed_count,
        "ingestion": {
            "received_count": result.ingestion_result.received_count,
            "inserted_count": result.ingestion_result.inserted_count,
            "duplicate_count": result.ingestion_result.duplicate_count,
            "failed_count": result.ingestion_result.failed_count,
        },
        "extracted_count": result.extracted_count,
        "no_signal_count": result.no_signal_count,
        "extraction_failed_count": result.extraction_failed_count,
        "signal_inserted_count": result.signal_inserted_count,
        "scoring": {
            "scored_count": result.scoring_result.scored_count,
            "failed_count": result.scoring_result.failed_count,
            "average_score": result.scoring_result.average_score,
        },
        "embedding_failed_count": result.embedding_failed_count,
        "clustered_count": result.clustered_count,
        "cluster_inserted_count": result.cluster_inserted_count,
        "report": _serialize_report(result.report),
        "email": _serialize_email_result(result.email_result),
    }
