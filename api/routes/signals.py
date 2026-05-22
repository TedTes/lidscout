"""API endpoints for market signal workflows."""
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from application.ingestion import SourceAdapter
from application.ports import (
    ClusterRepository,
    CompetitorRepository,
    MonitoredSourceRepository,
    OpportunityRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceLocatorRepository,
)
from application.reporting import MarketSignalReport, ReportingService
from application.source_suggestions import SourceSuggestion, SourceSuggestionService
from domain.cluster import SignalCluster
from domain.competitor import Competitor
from domain.opportunity import Opportunity
from domain.signal import Signal
from domain.source import MonitoredSource, SourceInput
from infrastructure.db import (
    InMemoryClusterRepository,
    InMemoryCompetitorRepository,
    InMemoryMonitoredSourceRepository,
    InMemoryOpportunityRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemorySourceLocatorRepository,
)
from infrastructure.email import EmailClient, EmailSendResult
from infrastructure.llm import EmbeddingClient, LLMClient
from workers.run_daily_pipeline import (
    PipelineConfig,
    PipelineRunResult,
    run_daily_pipeline,
)

router = APIRouter(tags=["signals"])


class PipelineSourceRequest(BaseModel):
    """Generic source request for a pipeline run."""

    locator: str = Field(min_length=1)
    limit: int | None = Field(default=None, ge=1)
    options: dict[str, Any] = Field(default_factory=dict)


class PipelineRunRequest(BaseModel):
    """HTTP request body for running the signal pipeline."""

    recipient: str = Field(min_length=1)
    sources: list[PipelineSourceRequest] = Field(default_factory=list)
    default_limit: int = Field(default=25, ge=1)
    similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)


class CompetitorRequest(BaseModel):
    """HTTP request body for creating a monitored competitor."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    website: str | None = None
    category: str | None = None
    description: str | None = None


class MonitoredSourceRequest(BaseModel):
    """HTTP request body for creating a monitored source."""

    locator: str = Field(min_length=1)
    source_type: str = Field(default="web", min_length=1)
    enabled: bool = True
    limit: int | None = Field(default=None, ge=1)
    scan_frequency: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class MonitoredSourceUpdateRequest(BaseModel):
    """HTTP request body for updating a monitored source."""

    source_type: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    limit: int | None = Field(default=None, ge=1)
    scan_frequency: str | None = None
    options: dict[str, Any] | None = None


@dataclass
class SignalApiDependencies:
    """Runtime dependencies for signal API routes."""

    post_repository: PostRepository = field(default_factory=InMemoryPostRepository)
    signal_repository: SignalRepository = field(default_factory=InMemorySignalRepository)
    score_repository: ScoreRepository = field(default_factory=InMemoryScoreRepository)
    cluster_repository: ClusterRepository = field(default_factory=InMemoryClusterRepository)
    opportunity_repository: OpportunityRepository = field(
        default_factory=InMemoryOpportunityRepository
    )
    competitor_repository: CompetitorRepository = field(
        default_factory=InMemoryCompetitorRepository
    )
    monitored_source_repository: MonitoredSourceRepository = field(
        default_factory=InMemoryMonitoredSourceRepository
    )
    source_locator_repository: SourceLocatorRepository = field(
        default_factory=InMemorySourceLocatorRepository
    )
    reporting_service: ReportingService = field(default_factory=ReportingService)
    source_adapters: list[SourceAdapter] = field(default_factory=list)
    llm_client: LLMClient | None = None
    embedding_client: EmbeddingClient | None = None
    email_client: EmailClient | None = None


_dependencies = SignalApiDependencies()


def configure_signal_api_dependencies(dependencies: SignalApiDependencies) -> None:
    """Replace signal API dependencies for the running process."""
    global _dependencies
    _dependencies = dependencies


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


@router.delete("/signals/{signal_id}")
async def delete_signal(
    signal_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Delete one signal plus its score/evidence records."""
    if dependencies.signal_repository.get_signal(signal_id) is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    dependencies.score_repository.delete_score(signal_id)
    dependencies.signal_repository.delete_signal(signal_id)
    return {
        "id": signal_id,
        "deleted": True,
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


@router.get("/opportunities")
async def list_opportunities(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return synthesized product opportunities."""
    return {
        "opportunities": [
            _serialize_opportunity(opportunity)
            for opportunity in dependencies.opportunity_repository.list_opportunities()
        ]
    }


@router.get("/reports/latest")
async def get_latest_report(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Generate and return the latest report from persisted clusters."""
    report = dependencies.reporting_service.generate(
        dependencies.cluster_repository.list_clusters(),
        dependencies.opportunity_repository.list_opportunities(),
    )
    return _serialize_report(report)


@router.get("/competitors")
async def list_competitors(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored competitors."""
    return {
        "competitors": [
            _serialize_competitor(competitor)
            for competitor in dependencies.competitor_repository.list_competitors()
        ]
    }


@router.post("/competitors")
async def create_competitor(
    request: CompetitorRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Create a monitored competitor."""
    try:
        competitor = Competitor.create(
            id=request.id,
            name=request.name,
            website=request.website,
            category=request.category,
            description=request.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.competitor_repository.save_competitors([competitor])
    return _serialize_competitor(competitor)


@router.get("/competitors/{competitor_id}/sources")
async def list_competitor_sources(
    competitor_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored sources for one competitor."""
    return {
        "sources": [
            _serialize_monitored_source(source)
            for source in dependencies.monitored_source_repository.list_monitored_sources(
                competitor_id=competitor_id,
            )
        ]
    }


@router.get("/competitors/{competitor_id}/source-suggestions")
async def list_competitor_source_suggestions(
    competitor_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return opinionated default source candidates for one competitor."""
    competitor = dependencies.competitor_repository.get_competitor(competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")

    existing_sources = dependencies.monitored_source_repository.list_monitored_sources(
        competitor_id=competitor_id,
    )
    return {
        "suggestions": [
            _serialize_source_suggestion(suggestion)
            for suggestion in SourceSuggestionService().suggest(
                competitor,
                existing_sources,
            )
        ]
    }


@router.get("/sources")
async def list_sources(
    competitor_id: str | None = None,
    enabled: bool | None = None,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored sources across competitors."""
    return {
        "sources": [
            _serialize_monitored_source(source)
            for source in dependencies.monitored_source_repository.list_monitored_sources(
                competitor_id=competitor_id,
                enabled=enabled,
            )
        ]
    }


@router.post("/competitors/{competitor_id}/sources")
async def create_competitor_source(
    competitor_id: str,
    request: MonitoredSourceRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Create a monitored source for one competitor."""
    if dependencies.competitor_repository.get_competitor(competitor_id) is None:
        raise HTTPException(status_code=404, detail="Competitor not found")

    try:
        source = MonitoredSource.create(
            competitor_id=competitor_id,
            locator=request.locator,
            source_type=request.source_type,
            enabled=request.enabled,
            limit=request.limit,
            scan_frequency=request.scan_frequency,
            options=request.options,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.monitored_source_repository.save_monitored_sources([source])
    return _serialize_monitored_source(source)


@router.patch("/sources/{source_id}")
async def update_source(
    source_id: str,
    request: MonitoredSourceUpdateRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Update one monitored source."""
    existing = dependencies.monitored_source_repository.get_monitored_source(source_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        source = _apply_source_update(existing, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not dependencies.monitored_source_repository.update_monitored_source(source):
        raise HTTPException(status_code=404, detail="Source not found")

    return _serialize_monitored_source(source)


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
            opportunity_repository=dependencies.opportunity_repository,
            competitor_repository=dependencies.competitor_repository,
            monitored_source_repository=dependencies.monitored_source_repository,
            source_locator_repository=dependencies.source_locator_repository,
            llm_client=dependencies.llm_client,
            embedding_client=dependencies.embedding_client,
            email_client=dependencies.email_client,
            recipient=request.recipient,
            source_adapters=dependencies.source_adapters,
            sources=[
                SourceInput.create(
                    locator=source.locator,
                    limit=source.limit,
                    options=source.options,
                )
                for source in request.sources
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
    if not dependencies.source_adapters:
        missing.append("source_adapters")

    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline dependencies are not configured: {', '.join(missing)}",
        )


def _apply_source_update(
    source: MonitoredSource,
    request: MonitoredSourceUpdateRequest,
) -> MonitoredSource:
    fields = request.model_fields_set
    options = request.options if "options" in fields else source.options
    return MonitoredSource.create(
        id=source.id,
        competitor_id=source.competitor_id,
        locator=source.locator,
        source_type=(
            request.source_type if "source_type" in fields else source.source_type
        ),
        enabled=request.enabled if "enabled" in fields else source.enabled,
        limit=request.limit if "limit" in fields else source.limit,
        scan_frequency=(
            request.scan_frequency
            if "scan_frequency" in fields
            else source.scan_frequency
        ),
        last_scanned_at=source.last_scanned_at,
        last_error=source.last_error,
        options=options or {},
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
        "competitor_id": signal.competitor_id,
        "evidence_url": signal.evidence_url,
        "evidence_text": signal.evidence_text,
        "detected_at": signal.detected_at.isoformat() if signal.detected_at else None,
    }


def _serialize_competitor(competitor: Competitor) -> dict[str, Any]:
    return {
        "id": competitor.id,
        "name": competitor.name,
        "website": competitor.website,
        "category": competitor.category,
        "description": competitor.description,
        "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
    }


def _serialize_monitored_source(source: MonitoredSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "competitor_id": source.competitor_id,
        "locator": source.locator,
        "source_type": source.source_type,
        "enabled": source.enabled,
        "limit": source.limit,
        "scan_frequency": source.scan_frequency,
        "last_scanned_at": (
            source.last_scanned_at.isoformat() if source.last_scanned_at else None
        ),
        "last_error": source.last_error,
        "options": source.options,
    }


def _serialize_source_suggestion(suggestion: SourceSuggestion) -> dict[str, Any]:
    return {
        "locator": suggestion.locator,
        "source_type": suggestion.source_type,
        "label": suggestion.label,
        "rationale": suggestion.rationale,
        "limit": suggestion.limit,
        "options": suggestion.options,
        "already_monitored": suggestion.already_monitored,
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


def _serialize_opportunity(opportunity: Opportunity) -> dict[str, Any]:
    return {
        "id": opportunity.id,
        "cluster_id": opportunity.cluster_id,
        "title": opportunity.title,
        "target_user": opportunity.target_user,
        "pain_summary": opportunity.pain_summary,
        "why_it_matters": opportunity.why_it_matters,
        "suggested_wedge": opportunity.suggested_wedge,
        "evidence_count": opportunity.evidence_count,
        "confidence": opportunity.confidence,
        "evidence_signal_ids": opportunity.evidence_signal_ids,
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
        "recommended_opportunities": [
            _serialize_opportunity(opportunity)
            for opportunity in report.recommended_opportunities
        ],
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
        "opportunity_synthesis": {
            "synthesized_count": (
                result.opportunity_synthesis_result.synthesized_count
            ),
            "inserted_count": result.opportunity_synthesis_result.inserted_count,
            "failed_count": result.opportunity_synthesis_result.failed_count,
        },
        "report": _serialize_report(result.report),
        "email": _serialize_email_result(result.email_result),
    }
