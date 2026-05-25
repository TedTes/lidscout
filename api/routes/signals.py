"""API endpoints for market signal workflows."""
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from application.agent import (
    AgentColdStartPlan,
    AgentColdStartService,
    rank_opportunities_with_feedback,
)
from application.ingestion import SourceAdapter
from application.ports import (
    AgentFeedbackRepository,
    AgentPreferencesRepository,
    ClusterRepository,
    CompetitorRepository,
    MarketRepository,
    MonitoredSourceRepository,
    OpportunityRepository,
    PipelineRunMetricsRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceLocatorRepository,
)
from application.reporting import MarketSignalReport, ReportingService
from application.source_suggestions import SourceSuggestion, SourceSuggestionService
from domain.cluster import SignalCluster
from domain.agent import AgentFeedback, AgentPreferences
from domain.competitor import Competitor
from domain.market import Market
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.signal import Signal
from domain.source import MonitoredSource, SourceInput
from infrastructure.db import (
    InMemoryAgentFeedbackRepository,
    InMemoryAgentPreferencesRepository,
    InMemoryClusterRepository,
    InMemoryCompetitorRepository,
    InMemoryMarketRepository,
    InMemoryMonitoredSourceRepository,
    InMemoryOpportunityRepository,
    InMemoryPipelineRunMetricsRepository,
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
    market_id: str | None = None
    default_limit: int = Field(default=25, ge=1)
    similarity_threshold: float = Field(default=0.82, ge=0.0, le=1.0)


class CompetitorRequest(BaseModel):
    """HTTP request body for creating a monitored competitor."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    website: str | None = None
    category: str | None = None
    description: str | None = None
    market_id: str | None = None


class MarketRequest(BaseModel):
    """HTTP request body for creating a watched market."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    target_user: str | None = None
    idea_prompt: str | None = None


class MarketUpdateRequest(BaseModel):
    """HTTP request body for updating a watched market."""

    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    target_user: str | None = None
    idea_prompt: str | None = None


class AgentPreferencesRequest(BaseModel):
    """HTTP request body for updating agent preferences."""

    preferred_source_families: list[str] | None = None
    ignored_themes: list[str] | None = None
    ignored_categories: list[str] | None = None
    muted_source_ids: list[str] | None = None
    extra_instructions: str | None = None


class AgentFeedbackRequest(BaseModel):
    """HTTP request body for recording feedback on a gap."""

    market_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    reason: str | None = None


class MonitoredSourceRequest(BaseModel):
    """HTTP request body for creating a monitored source."""

    locator: str = Field(min_length=1)
    source_type: str = Field(default="web", min_length=1)
    enabled: bool = True
    limit: int | None = Field(default=None, ge=1)
    scan_frequency: str | None = None
    market_id: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class MonitoredSourceUpdateRequest(BaseModel):
    """HTTP request body for updating a monitored source."""

    source_type: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    limit: int | None = Field(default=None, ge=1)
    scan_frequency: str | None = None
    market_id: str | None = None
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
    pipeline_run_metrics_repository: PipelineRunMetricsRepository = field(
        default_factory=InMemoryPipelineRunMetricsRepository
    )
    agent_preferences_repository: AgentPreferencesRepository = field(
        default_factory=InMemoryAgentPreferencesRepository
    )
    agent_feedback_repository: AgentFeedbackRepository = field(
        default_factory=InMemoryAgentFeedbackRepository
    )
    competitor_repository: CompetitorRepository = field(
        default_factory=InMemoryCompetitorRepository
    )
    market_repository: MarketRepository = field(default_factory=InMemoryMarketRepository)
    monitored_source_repository: MonitoredSourceRepository = field(
        default_factory=InMemoryMonitoredSourceRepository
    )
    source_locator_repository: SourceLocatorRepository = field(
        default_factory=InMemorySourceLocatorRepository
    )
    reporting_service: ReportingService = field(default_factory=ReportingService)
    source_adapters: list[SourceAdapter] = field(default_factory=list)
    llm_client: LLMClient | None = None
    relevance_llm_client: LLMClient | None = None
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
    competitor_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Return persisted extracted signals, optionally filtered by scope."""
    signals = dependencies.signal_repository.list_signals()
    if competitor_id is not None:
        signals = [s for s in signals if s.competitor_id == competitor_id]
    if market_id is not None:
        signals = [s for s in signals if s.market_id == market_id]
    return {"signals": [_serialize_signal(s, dependencies) for s in signals]}


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
    competitor_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Return persisted signal clusters, optionally filtered by scope."""
    clusters = dependencies.cluster_repository.list_clusters()
    if competitor_id is not None or market_id is not None:
        scoped_signal_ids = {
            s.id
            for s in dependencies.signal_repository.list_signals()
            if (competitor_id is None or s.competitor_id == competitor_id)
            and (market_id is None or s.market_id == market_id)
        }
        clusters = [
            c for c in clusters
            if any(sid in scoped_signal_ids for sid in c.signal_ids)
        ]
    return {
        "clusters": [
            _serialize_cluster(c, dependencies, market_id=market_id)
            for c in clusters
        ]
    }


@router.get("/opportunities")
async def list_opportunities(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    competitor_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Return synthesized product opportunities, optionally filtered by scope."""
    opportunities = dependencies.opportunity_repository.list_opportunities()
    if competitor_id is not None or market_id is not None:
        scoped_signal_ids = {
            s.id
            for s in dependencies.signal_repository.list_signals()
            if (competitor_id is None or s.competitor_id == competitor_id)
            and (market_id is None or s.market_id == market_id)
        }
        opportunities = [
            o for o in opportunities
            if any(sid in scoped_signal_ids for sid in o.evidence_signal_ids)
        ]
    if market_id is not None:
        opportunities = rank_opportunities_with_feedback(
            opportunities,
            dependencies.agent_feedback_repository.list_agent_feedback(
                market_id=market_id,
            ),
        )
    return {
        "opportunities": [
            _serialize_opportunity(o, dependencies, market_id=market_id)
            for o in opportunities
        ]
    }


@router.get("/markets")
async def list_markets(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return watched markets or niches."""
    return {
        "markets": [
            _serialize_market(market)
            for market in dependencies.market_repository.list_markets()
        ]
    }


@router.post("/markets")
async def create_market(
    request: MarketRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Create a watched market or niche."""
    try:
        market = Market.create(
            id=request.id,
            name=request.name,
            description=request.description,
            target_user=request.target_user,
            idea_prompt=request.idea_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.market_repository.save_markets([market])
    return _serialize_market(market)


@router.get("/markets/{market_id}")
async def get_market(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return one watched market."""
    market = dependencies.market_repository.get_market(market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")
    return _serialize_market(market)


@router.patch("/markets/{market_id}")
async def update_market(
    market_id: str,
    request: MarketUpdateRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Update one watched market."""
    existing = dependencies.market_repository.get_market(market_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Market not found")

    fields_set = _model_fields_set(request)
    try:
        market = Market.create(
            id=existing.id,
            name=request.name if "name" in fields_set else existing.name,
            description=(
                request.description
                if "description" in fields_set
                else existing.description
            ),
            target_user=(
                request.target_user
                if "target_user" in fields_set
                else existing.target_user
            ),
            idea_prompt=(
                request.idea_prompt
                if "idea_prompt" in fields_set
                else existing.idea_prompt
            ),
            created_at=existing.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not dependencies.market_repository.update_market(market):
        raise HTTPException(status_code=404, detail="Market not found")
    return _serialize_market(market)


@router.delete("/markets/{market_id}")
async def delete_market(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Delete one watched market."""
    if dependencies.market_repository.get_market(market_id) is None:
        raise HTTPException(status_code=404, detail="Market not found")
    if not dependencies.market_repository.delete_market(market_id):
        raise HTTPException(status_code=404, detail="Market not found")
    return {
        "id": market_id,
        "deleted": True,
    }


@router.get("/markets/{market_id}/competitors")
async def list_market_competitors(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return competitors linked to one market."""
    _ensure_market_exists(market_id, dependencies)
    competitors = [
        competitor
        for competitor in dependencies.competitor_repository.list_competitors()
        if competitor.market_id == market_id
    ]
    return {"competitors": [_serialize_competitor(c) for c in competitors]}


@router.post("/markets/{market_id}/competitors")
async def create_market_competitor(
    market_id: str,
    request: CompetitorRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Create a monitored competitor scoped to one market."""
    _ensure_market_exists(market_id, dependencies)
    if request.market_id is not None and request.market_id != market_id:
        raise HTTPException(
            status_code=400,
            detail="Request market_id must match route market_id",
        )

    try:
        competitor = Competitor.create(
            id=request.id,
            name=request.name,
            website=request.website,
            category=request.category,
            description=request.description,
            market_id=market_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.competitor_repository.save_competitors([competitor])
    return _serialize_competitor(competitor)


@router.get("/markets/{market_id}/sources")
async def list_market_sources(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored sources linked to one market."""
    _ensure_market_exists(market_id, dependencies)
    sources = dependencies.monitored_source_repository.list_monitored_sources(
        market_id=market_id,
    )
    return {
        "sources": [
            _serialize_monitored_source(source, dependencies)
            for source in sources
        ],
        "summary": _source_coverage_summary(sources),
    }


@router.post("/markets/{market_id}/sources")
async def create_market_source(
    market_id: str,
    request: MonitoredSourceRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Create a monitored source scoped directly to one market."""
    _ensure_market_exists(market_id, dependencies)
    try:
        source = MonitoredSource.create(
            market_id=market_id,
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
    return _serialize_monitored_source(source, dependencies)


@router.get("/reports/latest")
async def get_latest_report(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    competitor_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Generate and return the latest report from persisted clusters."""
    clusters = dependencies.cluster_repository.list_clusters()
    opportunities = dependencies.opportunity_repository.list_opportunities()
    if competitor_id is not None or market_id is not None:
        scoped_signal_ids = _scoped_signal_ids(
            dependencies,
            competitor_id=competitor_id,
            market_id=market_id,
        )
        clusters = [
            cluster
            for cluster in clusters
            if any(signal_id in scoped_signal_ids for signal_id in cluster.signal_ids)
        ]
        opportunities = [
            opportunity
            for opportunity in opportunities
            if any(
                signal_id in scoped_signal_ids
                for signal_id in opportunity.evidence_signal_ids
            )
        ]

    report = dependencies.reporting_service.generate(
        clusters,
        opportunities,
        title=_market_report_title(dependencies, market_id),
    )
    return _serialize_report(report, dependencies, market_id=market_id)


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
            market_id=request.market_id,
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
            _serialize_monitored_source(source, dependencies)
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
    market = (
        dependencies.market_repository.get_market(competitor.market_id)
        if competitor.market_id
        else None
    )
    return {
        "suggestions": [
            _serialize_source_suggestion(suggestion)
            for suggestion in SourceSuggestionService().suggest(
                competitor,
                existing_sources,
                market=market,
            )
        ]
    }


@router.get("/markets/{market_id}/source-suggestions")
async def list_market_source_suggestions(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return opinionated default source candidates for one market."""
    market = dependencies.market_repository.get_market(market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")

    existing_sources = dependencies.monitored_source_repository.list_monitored_sources(
        market_id=market_id,
    )
    competitors = [
        competitor
        for competitor in dependencies.competitor_repository.list_competitors()
        if competitor.market_id == market_id
    ]
    return {
        "suggestions": [
            _serialize_source_suggestion(suggestion)
            for suggestion in SourceSuggestionService().suggest_for_market(
                market,
                existing_sources,
                competitors=competitors,
            )
        ]
    }


@router.get("/markets/{market_id}/agent/cold-start")
async def get_market_agent_cold_start(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return cold-start setup guidance for one niche research agent."""
    market = dependencies.market_repository.get_market(market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="Market not found")

    competitors = [
        competitor
        for competitor in dependencies.competitor_repository.list_competitors()
        if competitor.market_id == market_id
    ]
    sources = dependencies.monitored_source_repository.list_monitored_sources(
        market_id=market_id,
    )
    suggestions = SourceSuggestionService().suggest_for_market(
        market,
        sources,
        competitors=competitors,
    )
    plan = AgentColdStartService().build_plan(
        market=market,
        competitors=competitors,
        monitored_sources=sources,
        source_suggestions=suggestions,
    )
    return _serialize_agent_cold_start_plan(plan)


@router.get("/markets/{market_id}/agent/preferences")
async def get_market_agent_preferences(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return persisted preferences for one niche research agent."""
    _ensure_market_exists(market_id, dependencies)
    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        market_id,
    )
    if preferences is None:
        preferences = AgentPreferences.create(market_id=market_id)
    return _serialize_agent_preferences(preferences)


@router.patch("/markets/{market_id}/agent/preferences")
async def update_market_agent_preferences(
    market_id: str,
    request: AgentPreferencesRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Update persisted preferences for one niche research agent."""
    _ensure_market_exists(market_id, dependencies)
    existing = dependencies.agent_preferences_repository.get_agent_preferences(
        market_id,
    ) or AgentPreferences.create(market_id=market_id)
    fields = _model_fields_set(request)
    try:
        preferences = AgentPreferences.create(
            market_id=market_id,
            preferred_source_families=(
                request.preferred_source_families
                if "preferred_source_families" in fields
                else existing.preferred_source_families
            ),
            ignored_themes=(
                request.ignored_themes
                if "ignored_themes" in fields
                else existing.ignored_themes
            ),
            ignored_categories=(
                request.ignored_categories
                if "ignored_categories" in fields
                else existing.ignored_categories
            ),
            muted_source_ids=(
                request.muted_source_ids
                if "muted_source_ids" in fields
                else existing.muted_source_ids
            ),
            extra_instructions=(
                request.extra_instructions
                if "extra_instructions" in fields
                else existing.extra_instructions
            ),
            created_at=existing.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.agent_preferences_repository.save_agent_preferences(preferences)
    return _serialize_agent_preferences(preferences)


@router.get("/markets/{market_id}/agent/feedback")
async def list_market_agent_feedback(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return feedback events for one niche research agent."""
    _ensure_market_exists(market_id, dependencies)
    feedback = dependencies.agent_feedback_repository.list_agent_feedback(
        market_id=market_id,
    )
    return {"feedback": [_serialize_agent_feedback(item) for item in feedback]}


@router.post("/opportunities/{opportunity_id}/feedback")
async def create_opportunity_feedback(
    opportunity_id: str,
    request: AgentFeedbackRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Record user feedback on one synthesized gap."""
    _ensure_market_exists(request.market_id, dependencies)
    if dependencies.opportunity_repository.get_opportunity(opportunity_id) is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    try:
        feedback = AgentFeedback.create(
            market_id=request.market_id,
            opportunity_id=opportunity_id,
            action=request.action,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.agent_feedback_repository.save_agent_feedback(feedback)
    return _serialize_agent_feedback(feedback)


@router.get("/sources")
async def list_sources(
    competitor_id: str | None = None,
    market_id: str | None = None,
    enabled: bool | None = None,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored sources across competitors."""
    sources = dependencies.monitored_source_repository.list_monitored_sources(
        competitor_id=competitor_id,
        market_id=market_id,
        enabled=enabled,
    )
    return {
        "sources": [
            _serialize_monitored_source(source, dependencies)
            for source in sources
        ],
        "summary": _source_coverage_summary(sources),
    }


@router.post("/competitors/{competitor_id}/sources")
async def create_competitor_source(
    competitor_id: str,
    request: MonitoredSourceRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Create a monitored source for one competitor."""
    competitor = dependencies.competitor_repository.get_competitor(competitor_id)
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competitor not found")

    try:
        source = MonitoredSource.create(
            competitor_id=competitor_id,
            market_id=request.market_id or competitor.market_id,
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
    return _serialize_monitored_source(source, dependencies)


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

    return _serialize_monitored_source(source, dependencies)


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
            pipeline_run_metrics_repository=(
                dependencies.pipeline_run_metrics_repository
            ),
            competitor_repository=dependencies.competitor_repository,
            market_repository=dependencies.market_repository,
            monitored_source_repository=dependencies.monitored_source_repository,
            source_locator_repository=dependencies.source_locator_repository,
            llm_client=dependencies.llm_client,
            relevance_llm_client=dependencies.relevance_llm_client,
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
            market_id=request.market_id,
            default_limit=request.default_limit,
            similarity_threshold=request.similarity_threshold,
        )
    )
    return _serialize_pipeline_result(result)


@router.get("/pipeline/runs")
async def list_pipeline_runs(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    limit: int = 20,
) -> dict[str, Any]:
    """Return recent persisted pipeline worker run metrics."""
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be at least 1")
    metrics = dependencies.pipeline_run_metrics_repository.list_pipeline_run_metrics()
    recent_metrics = sorted(metrics, key=lambda item: item.ran_at, reverse=True)[:limit]
    return {
        "runs": [_serialize_pipeline_run_metrics(run) for run in recent_metrics]
    }


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
        market_id=(
            request.market_id
            if "market_id" in fields
            else source.market_id
        ),
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


def _ensure_market_exists(
    market_id: str,
    dependencies: SignalApiDependencies,
) -> None:
    if dependencies.market_repository.get_market(market_id) is None:
        raise HTTPException(status_code=404, detail="Market not found")


def _scoped_signal_ids(
    dependencies: SignalApiDependencies,
    *,
    competitor_id: str | None = None,
    market_id: str | None = None,
) -> set[str]:
    return {
        signal.id
        for signal in dependencies.signal_repository.list_signals()
        if (competitor_id is None or signal.competitor_id == competitor_id)
        and (market_id is None or signal.market_id == market_id)
    }


def _company_breadth_for_signal_ids(
    dependencies: SignalApiDependencies,
    signal_ids: list[str],
    *,
    market_id: str | None = None,
) -> dict[str, Any]:
    signal_id_set = set(signal_ids)
    signals = [
        signal
        for signal in dependencies.signal_repository.list_signals()
        if signal.id in signal_id_set
    ]
    company_ids = sorted(
        {
            signal.competitor_id
            for signal in signals
            if signal.competitor_id is not None
        }
    )
    competitors_by_id = {
        competitor.id: competitor
        for competitor in dependencies.competitor_repository.list_competitors()
    }
    company_names = [
        competitors_by_id[company_id].name
        for company_id in company_ids
        if company_id in competitors_by_id
    ]
    resolved_market_id = market_id or _single_market_id(signals)
    market_company_count = (
        _market_company_count(dependencies, resolved_market_id)
        if resolved_market_id is not None
        else None
    )

    return {
        "company_ids": company_ids,
        "company_names": company_names,
        "company_count": len(company_ids),
        "market_company_count": market_company_count,
    }


def _single_market_id(signals: list[Signal]) -> str | None:
    market_ids = {
        signal.market_id
        for signal in signals
        if signal.market_id is not None
    }
    if len(market_ids) != 1:
        return None
    return next(iter(market_ids))


def _market_company_count(
    dependencies: SignalApiDependencies,
    market_id: str,
) -> int:
    return sum(
        1
        for competitor in dependencies.competitor_repository.list_competitors()
        if competitor.market_id == market_id
    )


def _market_report_title(
    dependencies: SignalApiDependencies,
    market_id: str | None,
) -> str | None:
    if market_id is None:
        return None
    market = dependencies.market_repository.get_market(market_id)
    if market is None:
        return None
    return f"{market.name} Market Gap Report"


def _serialize_market(market: Market) -> dict[str, Any]:
    return {
        "id": market.id,
        "name": market.name,
        "description": market.description,
        "target_user": market.target_user,
        "idea_prompt": market.idea_prompt,
        "created_at": market.created_at.isoformat() if market.created_at else None,
    }


def _serialize_signal(
    signal: Signal,
    dependencies: SignalApiDependencies | None = None,
) -> dict[str, Any]:
    competitor = (
        dependencies.competitor_repository.get_competitor(signal.competitor_id)
        if dependencies is not None and signal.competitor_id is not None
        else None
    )
    market = (
        dependencies.market_repository.get_market(signal.market_id)
        if dependencies is not None and signal.market_id is not None
        else None
    )
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
        "competitor_name": competitor.name if competitor else None,
        "market_id": signal.market_id,
        "market_name": market.name if market else None,
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
        "market_id": competitor.market_id,
        "created_at": competitor.created_at.isoformat() if competitor.created_at else None,
    }


def _serialize_monitored_source(
    source: MonitoredSource,
    dependencies: SignalApiDependencies | None = None,
) -> dict[str, Any]:
    competitor = (
        dependencies.competitor_repository.get_competitor(source.competitor_id)
        if dependencies is not None and source.competitor_id is not None
        else None
    )
    market = (
        dependencies.market_repository.get_market(source.market_id)
        if dependencies is not None and source.market_id is not None
        else None
    )
    return {
        "id": source.id,
        "competitor_id": source.competitor_id,
        "competitor_name": competitor.name if competitor else None,
        "market_id": source.market_id,
        "market_name": market.name if market else None,
        "locator": source.locator,
        "source_type": source.source_type,
        "source_family": _source_family(source),
        "enabled": source.enabled,
        "limit": source.limit,
        "scan_frequency": source.scan_frequency,
        "last_scanned_at": (
            source.last_scanned_at.isoformat() if source.last_scanned_at else None
        ),
        "last_error": source.last_error,
        "options": source.options,
    }


def _source_coverage_summary(sources: list[MonitoredSource]) -> dict[str, Any]:
    by_family: dict[str, dict[str, Any]] = {}
    company_ids: set[str] = set()
    active_count = 0
    error_count = 0

    for source in sources:
        family = _source_family(source) or "unknown"
        entry = by_family.setdefault(
            family,
            {
                "source_family": family,
                "source_count": 0,
                "active_count": 0,
                "error_count": 0,
                "company_count": 0,
            },
        )
        entry["source_count"] += 1
        if source.enabled:
            active_count += 1
            entry["active_count"] += 1
        if source.last_error:
            error_count += 1
            entry["error_count"] += 1
        if source.competitor_id:
            company_ids.add(source.competitor_id)

    for family, entry in by_family.items():
        entry_company_ids = {
            source.competitor_id
            for source in sources
            if source.competitor_id and (_source_family(source) or "unknown") == family
        }
        entry["company_count"] = len(entry_company_ids)

    return {
        "source_count": len(sources),
        "active_count": active_count,
        "disabled_count": len(sources) - active_count,
        "error_count": error_count,
        "company_count": len(company_ids),
        "by_family": sorted(
            by_family.values(),
            key=lambda item: (-item["source_count"], item["source_family"]),
        ),
    }


def _source_family(source: MonitoredSource) -> str | None:
    family = source.options.get("source_family")
    return family if isinstance(family, str) and family else None


def _serialize_source_suggestion(suggestion: SourceSuggestion) -> dict[str, Any]:
    return {
        "locator": suggestion.locator,
        "source_type": suggestion.source_type,
        "label": suggestion.label,
        "rationale": suggestion.rationale,
        "source_family": suggestion.source_family,
        "competitor_id": suggestion.competitor_id,
        "competitor_name": suggestion.competitor_name,
        "market_id": suggestion.market_id,
        "market_name": suggestion.market_name,
        "limit": suggestion.limit,
        "options": suggestion.options,
        "template_id": suggestion.template_id,
        "already_monitored": suggestion.already_monitored,
        "rank_score": suggestion.rank_score,
        "validation_status": suggestion.validation_status,
        "validation_error": suggestion.validation_error,
    }


def _serialize_agent_cold_start_plan(plan: AgentColdStartPlan) -> dict[str, Any]:
    return {
        "market_id": plan.market_id,
        "status": plan.status,
        "brief": {
            "market_id": plan.brief.market_id,
            "niche_name": plan.brief.niche_name,
            "target_user": plan.brief.target_user,
            "objective": plan.brief.objective,
            "company_count": plan.brief.company_count,
            "source_family_priorities": plan.brief.source_family_priorities,
        },
        "monitored_source_count": plan.monitored_source_count,
        "active_source_count": plan.active_source_count,
        "suggested_source_count": plan.suggested_source_count,
        "next_actions": plan.next_actions,
    }


def _serialize_agent_preferences(preferences: AgentPreferences) -> dict[str, Any]:
    return {
        "market_id": preferences.market_id,
        "preferred_source_families": preferences.preferred_source_families,
        "ignored_themes": preferences.ignored_themes,
        "ignored_categories": preferences.ignored_categories,
        "muted_source_ids": preferences.muted_source_ids,
        "extra_instructions": preferences.extra_instructions,
        "created_at": (
            preferences.created_at.isoformat() if preferences.created_at else None
        ),
        "updated_at": (
            preferences.updated_at.isoformat() if preferences.updated_at else None
        ),
    }


def _serialize_agent_feedback(feedback: AgentFeedback) -> dict[str, Any]:
    return {
        "id": feedback.id,
        "market_id": feedback.market_id,
        "opportunity_id": feedback.opportunity_id,
        "action": feedback.action,
        "reason": feedback.reason,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }


def _serialize_cluster(
    cluster: SignalCluster,
    dependencies: SignalApiDependencies | None = None,
    *,
    market_id: str | None = None,
) -> dict[str, Any]:
    serialized = {
        "id": cluster.id,
        "theme": cluster.theme,
        "summary": cluster.summary,
        "signal_ids": cluster.signal_ids,
        "frequency": cluster.frequency,
        "average_score": cluster.average_score,
        "top_examples": cluster.top_examples,
    }
    if dependencies is not None:
        serialized.update(
            _company_breadth_for_signal_ids(
                dependencies,
                cluster.signal_ids,
                market_id=market_id,
            )
        )
    return serialized


def _serialize_opportunity(
    opportunity: Opportunity,
    dependencies: SignalApiDependencies | None = None,
    *,
    market_id: str | None = None,
) -> dict[str, Any]:
    serialized = {
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
    if dependencies is not None:
        serialized.update(
            _company_breadth_for_signal_ids(
                dependencies,
                opportunity.evidence_signal_ids,
                market_id=market_id,
            )
        )
    return serialized


def _serialize_report(
    report: MarketSignalReport,
    dependencies: SignalApiDependencies | None = None,
    *,
    market_id: str | None = None,
) -> dict[str, Any]:
    return {
        "title": report.title,
        "generated_at": report.generated_at.isoformat(),
        "top_clusters": [
            _serialize_cluster(cluster, dependencies, market_id=market_id)
            for cluster in report.top_clusters
        ],
        "emerging_pains": report.emerging_pains,
        "recommended_opportunities": [
            _serialize_opportunity(opportunity, dependencies, market_id=market_id)
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
        "rule_filtered_count": result.rule_filtered_count,
        "llm_filtered_count": result.llm_filtered_count,
        "relevance_failed_count": result.relevance_failed_count,
        "extraction_attempted_count": result.extraction_attempted_count,
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


def _model_fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is not None:
        return set(fields)
    return set(getattr(model, "__fields_set__", set()))


def _serialize_pipeline_run_metrics(metrics: PipelineRunMetrics) -> dict[str, Any]:
    return {
        "id": metrics.id,
        "ran_at": metrics.ran_at.isoformat(),
        "fetched_count": metrics.fetched_count,
        "fetch_failed_count": metrics.fetch_failed_count,
        "rule_filtered_count": metrics.rule_filtered_count,
        "llm_filtered_count": metrics.llm_filtered_count,
        "relevance_failed_count": metrics.relevance_failed_count,
        "extraction_attempted_count": metrics.extraction_attempted_count,
        "extracted_count": metrics.extracted_count,
        "no_signal_count": metrics.no_signal_count,
        "extraction_failed_count": metrics.extraction_failed_count,
        "signal_inserted_count": metrics.signal_inserted_count,
        "scored_count": metrics.scored_count,
        "scoring_failed_count": metrics.scoring_failed_count,
        "average_score": metrics.average_score,
        "embedding_failed_count": metrics.embedding_failed_count,
        "clustered_count": metrics.clustered_count,
        "cluster_inserted_count": metrics.cluster_inserted_count,
        "opportunity_synthesized_count": metrics.opportunity_synthesized_count,
        "opportunity_inserted_count": metrics.opportunity_inserted_count,
        "opportunity_failed_count": metrics.opportunity_failed_count,
        "email_sent": metrics.email_sent,
        "email_error": metrics.email_error,
    }
