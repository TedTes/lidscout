"""API endpoints for market signal workflows."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from api.routes.auth import get_current_user
from pydantic import BaseModel, Field

from application.agent import (
    AgentColdStartPlan,
    AgentColdStartService,
    build_agent_memory_summary,
    rank_opportunities_with_feedback,
)
from application.ingestion import SourceAdapter
from application.ports import (
    AgentActivityRepository,
    AgentAlertRepository,
    AgentFeedbackRepository,
    AgentFollowUpRepository,
    AgentPreferencesRepository,
    ClusterRepository,
    NicheCompanyRepository,
    NicheSourceRepository,
    OpportunityRepository,
    PipelineRunMetricsRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceLocatorRepository,
    UserNicheRepository,
)
from application.reporting import MarketSignalReport, ReportingService
from domain.cluster import SignalCluster
from domain.agent import (
    AgentActivity,
    AgentAlert,
    AgentFeedback,
    AgentFollowUp,
    AgentPreferences,
)
from domain.niche import NicheCompany, NicheSource, UserNiche
from domain.user import User
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.signal import Signal
from domain.source import SourceInput
from infrastructure.db import (
    InMemoryAgentActivityRepository,
    InMemoryAgentAlertRepository,
    InMemoryAgentFeedbackRepository,
    InMemoryAgentFollowUpRepository,
    InMemoryAgentPreferencesRepository,
    InMemoryClusterRepository,
    InMemoryNicheCompanyRepository,
    InMemoryNicheSourceRepository,
    InMemoryOpportunityRepository,
    InMemoryPipelineRunMetricsRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemorySourceLocatorRepository,
    InMemoryUserNicheRepository,
)
from infrastructure.email import EmailClient, EmailSendResult
from infrastructure.llm import EmbeddingClient, LLMClient
from shared.logger import get_logger, log_event
from workers.run_daily_pipeline import (
    PipelineConfig,
    PipelineRunResult,
    run_daily_pipeline,
)

router = APIRouter(tags=["signals"], dependencies=[Depends(get_current_user)])
logger = get_logger(__name__)


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


class NicheCompanyRequest(BaseModel):
    """HTTP request body for adding a company to a niche."""

    id: str | None = Field(default=None)
    name: str = Field(min_length=1)
    website: str | None = None


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


class AgentBriefRequest(BaseModel):
    """HTTP request body for updating the agent research brief."""

    niche_name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    target_user: str | None = None
    objective: str | None = None
    extra_instructions: str | None = None


class AgentFeedbackRequest(BaseModel):
    """HTTP request body for recording feedback on a gap."""

    market_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    reason: str | None = None


class AgentFollowUpRequest(BaseModel):
    """HTTP request body for storing a follow-up research question."""

    question: str = Field(min_length=1)
    opportunity_id: str | None = None
    cluster_id: str | None = None


class NicheSourceRequest(BaseModel):
    """HTTP request body for adding a source to a niche."""

    locator: str = Field(min_length=1)
    source_type: str = Field(default="web", min_length=1)
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


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
    agent_activity_repository: AgentActivityRepository = field(
        default_factory=InMemoryAgentActivityRepository
    )
    agent_alert_repository: AgentAlertRepository = field(
        default_factory=InMemoryAgentAlertRepository
    )
    agent_follow_up_repository: AgentFollowUpRepository = field(
        default_factory=InMemoryAgentFollowUpRepository
    )
    niche_company_repository: NicheCompanyRepository = field(
        default_factory=InMemoryNicheCompanyRepository
    )
    niche_source_repository: NicheSourceRepository = field(
        default_factory=InMemoryNicheSourceRepository
    )
    user_niche_repository: UserNicheRepository = field(
        default_factory=InMemoryUserNicheRepository
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
        signals = [s for s in signals if s.niche_company_id == competitor_id]
    if market_id is not None:
        signals = [s for s in signals if s.niche_id == market_id]
    return {"signals": [_serialize_signal(s) for s in signals]}


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
    all_signals = dependencies.signal_repository.list_signals()
    if competitor_id is not None or market_id is not None:
        scoped_signal_ids = {
            s.id
            for s in all_signals
            if (competitor_id is None or s.niche_company_id == competitor_id)
            and (market_id is None or s.niche_id == market_id)
        }
        clusters = [
            c for c in clusters
            if any(sid in scoped_signal_ids for sid in c.signal_ids)
        ]
    signals_by_id = {s.id: s for s in all_signals}
    return {
        "clusters": [
            _serialize_cluster(c, dependencies, market_id=market_id, _signals_by_id=signals_by_id)
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
    all_signals = dependencies.signal_repository.list_signals()
    if competitor_id is not None or market_id is not None:
        scoped_signal_ids = {
            s.id
            for s in all_signals
            if (competitor_id is None or s.niche_company_id == competitor_id)
            and (market_id is None or s.niche_id == market_id)
        }
        opportunities = [
            o for o in opportunities
            if any(sid in scoped_signal_ids for sid in o.evidence_signal_ids)
        ]
    if market_id is not None:
        opportunities = rank_opportunities_with_feedback(
            opportunities,
            dependencies.agent_feedback_repository.list_agent_feedback(
                user_niche_id=market_id,
            ),
        )
    signals_by_id = {s.id: s for s in all_signals}
    return {
        "opportunities": [
            _serialize_opportunity(o, dependencies, market_id=market_id, _signals_by_id=signals_by_id)
            for o in opportunities
        ]
    }


@router.get("/markets")
async def list_markets(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return watched markets or niches for the current user."""
    user_id = _current_user_id(current_user)
    if user_id is None:
        return {"markets": []}
    return {
        "markets": [
            _serialize_market(un)
            for un in dependencies.user_niche_repository.list_user_niches(user_id)
        ]
    }


@router.post("/markets")
async def create_market(
    request: MarketRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a watched market or niche."""
    user_id = _current_user_id(current_user) or "anonymous"
    try:
        user_niche = UserNiche.create(
            id=request.id,
            user_id=user_id,
            job=request.name,
            buyer=request.target_user or "general",
            category=request.description or "general",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.user_niche_repository.save_user_niche(user_niche)
    return _serialize_market(user_niche)


@router.get("/markets/{market_id}")
async def get_market(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return one watched market."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    return _serialize_market(user_niche)


@router.patch("/markets/{market_id}")
async def update_market(
    market_id: str,
    request: MarketUpdateRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update one watched market."""
    existing = _get_owned_user_niche(market_id, dependencies, current_user)

    fields_set = _model_fields_set(request)
    try:
        user_niche = UserNiche.create(
            id=existing.id,
            user_id=existing.user_id,
            job=request.name if "name" in fields_set else existing.job,
            buyer=(
                request.target_user
                if "target_user" in fields_set
                else existing.buyer
            ) or existing.buyer,
            category=(
                request.description
                if "description" in fields_set
                else existing.category
            ) or existing.category,
            status=existing.status,
            template_niche_id=existing.template_niche_id,
            created_at=existing.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not dependencies.user_niche_repository.update_user_niche(user_niche):
        raise HTTPException(status_code=404, detail="Market not found")
    return _serialize_market(user_niche)


@router.delete("/markets/{market_id}")
async def delete_market(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete one watched market."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    if not dependencies.user_niche_repository.delete_user_niche(market_id):
        raise HTTPException(status_code=404, detail="Market not found")
    return {
        "id": market_id,
        "deleted": True,
    }


@router.get("/markets/{market_id}/competitors")
async def list_market_competitors(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return companies linked to one niche."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    niche_id = user_niche.template_niche_id
    if niche_id is None:
        return {"competitors": []}
    companies = dependencies.niche_company_repository.list_niche_companies(niche_id)
    return {"competitors": [_serialize_niche_company(c) for c in companies]}


@router.post("/markets/{market_id}/competitors")
async def create_market_competitor(
    market_id: str,
    request: NicheCompanyRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Add a company to a niche."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    niche_id = user_niche.template_niche_id
    if niche_id is None:
        raise HTTPException(
            status_code=422,
            detail="Cannot add companies to a custom market without a template",
        )

    try:
        company = NicheCompany.create(
            id=request.id,
            niche_id=niche_id,
            name=request.name,
            website=request.website,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.niche_company_repository.save_niche_companies([company])
    return _serialize_niche_company(company)


@router.get("/markets/{market_id}/sources")
async def list_market_sources(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return monitoring sources linked to one niche."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    niche_id = user_niche.template_niche_id
    if niche_id is None:
        return {"sources": [], "summary": _source_coverage_summary([])}
    sources = dependencies.niche_source_repository.list_niche_sources(niche_id)
    return {
        "sources": [_serialize_niche_source(s) for s in sources],
        "summary": _source_coverage_summary(sources),
    }


@router.post("/markets/{market_id}/sources")
async def create_market_source(
    market_id: str,
    request: NicheSourceRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Add a monitoring source to a niche."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    niche_id = user_niche.template_niche_id
    if niche_id is None:
        raise HTTPException(
            status_code=422,
            detail="Cannot add sources to a custom market without a template",
        )
    source_family = str(request.options.get("source_family") or request.source_type or "web")
    is_gate_free = bool(request.options.get("is_gate_free", True))
    try:
        source = NicheSource.create(
            niche_id=niche_id,
            locator=request.locator,
            source_type=request.source_type,
            source_family=source_family,
            is_gate_free=is_gate_free,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.niche_source_repository.save_niche_sources([source])
    return _serialize_niche_source(source)


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
    return _serialize_report(report, market_id=market_id)


@router.get("/competitors")
async def list_competitors(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored competitors (placeholder — use /markets/{id}/competitors)."""
    return {"competitors": []}


@router.get("/competitors/{competitor_id}/sources")
async def list_competitor_sources(
    competitor_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return sources for one company (placeholder)."""
    return {"sources": []}


@router.get("/markets/{market_id}/source-suggestions")
async def list_market_source_suggestions(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return source candidates for one market (placeholder)."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    return {"suggestions": []}


@router.get("/markets/{market_id}/agent/cold-start")
async def get_market_agent_cold_start(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return cold-start setup guidance for one niche research agent."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    niche_id = user_niche.template_niche_id

    companies = (
        dependencies.niche_company_repository.list_niche_companies(niche_id)
        if niche_id is not None
        else []
    )
    sources = (
        dependencies.niche_source_repository.list_niche_sources(niche_id)
        if niche_id is not None
        else []
    )
    plan = AgentColdStartService().build_plan(
        user_niche=user_niche,
        companies=companies,
        sources=sources,
        source_suggestions=[],
    )
    return _serialize_agent_cold_start_plan(plan)


@router.get("/markets/{market_id}/agent/brief")
async def get_market_agent_brief(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the editable research brief for one niche agent."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    preferences = (
        dependencies.agent_preferences_repository.get_agent_preferences(market_id)
        or AgentPreferences.create(user_niche_id=market_id)
    )
    return _serialize_agent_brief(user_niche, preferences)


@router.patch("/markets/{market_id}/agent/brief")
async def update_market_agent_brief(
    market_id: str,
    request: AgentBriefRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update the niche research brief used by future agent runs."""
    existing = _get_owned_user_niche(market_id, dependencies, current_user)

    fields = _model_fields_set(request)
    try:
        user_niche = UserNiche.create(
            id=existing.id,
            user_id=existing.user_id,
            job=(
                request.niche_name
                if "niche_name" in fields
                else existing.job
            ) or existing.job,
            buyer=(
                request.target_user
                if "target_user" in fields
                else existing.buyer
            ) or existing.buyer,
            category=(
                request.description
                if "description" in fields
                else existing.category
            ) or existing.category,
            status=existing.status,
            template_niche_id=existing.template_niche_id,
            created_at=existing.created_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    preferences = (
        dependencies.agent_preferences_repository.get_agent_preferences(market_id)
        or AgentPreferences.create(user_niche_id=market_id)
    )
    if "extra_instructions" in fields:
        preferences = AgentPreferences.create(
            user_niche_id=market_id,
            preferred_source_families=preferences.preferred_source_families,
            ignored_themes=preferences.ignored_themes,
            ignored_categories=preferences.ignored_categories,
            muted_source_ids=preferences.muted_source_ids,
            extra_instructions=request.extra_instructions,
            created_at=preferences.created_at,
        )
        dependencies.agent_preferences_repository.save_agent_preferences(preferences)

    dependencies.user_niche_repository.update_user_niche(user_niche)
    _record_agent_activity(
        dependencies,
        user_niche_id=market_id,
        event_type="brief_updated",
        title="Research brief updated",
        detail="The agent research brief was updated for future runs.",
        metadata={
            "niche_name": user_niche.job,
            "target_user": user_niche.buyer,
            "has_extra_instructions": bool(preferences.extra_instructions),
        },
    )
    return _serialize_agent_brief(user_niche, preferences)


@router.get("/markets/{market_id}/agent/preferences")
async def get_market_agent_preferences(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return persisted preferences for one niche research agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    preferences = (
        dependencies.agent_preferences_repository.get_agent_preferences(market_id)
        or AgentPreferences.create(user_niche_id=market_id)
    )
    return _serialize_agent_preferences(preferences)


@router.patch("/markets/{market_id}/agent/preferences")
async def update_market_agent_preferences(
    market_id: str,
    request: AgentPreferencesRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update persisted preferences for one niche research agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    existing = (
        dependencies.agent_preferences_repository.get_agent_preferences(market_id)
        or AgentPreferences.create(user_niche_id=market_id)
    )
    fields = _model_fields_set(request)
    try:
        preferences = AgentPreferences.create(
            user_niche_id=market_id,
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
    _record_agent_activity(
        dependencies,
        user_niche_id=market_id,
        event_type="preferences_updated",
        title="Agent preferences updated",
        detail="Research preferences were updated for this niche.",
        metadata={
            "preferred_source_families": preferences.preferred_source_families,
            "ignored_themes": preferences.ignored_themes,
            "ignored_categories": preferences.ignored_categories,
            "muted_source_count": len(preferences.muted_source_ids),
        },
    )
    return _serialize_agent_preferences(preferences)


@router.get("/markets/{market_id}/agent/feedback")
async def list_market_agent_feedback(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return feedback events for one niche research agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    feedback = dependencies.agent_feedback_repository.list_agent_feedback(
        user_niche_id=market_id,
    )
    return {"feedback": [_serialize_agent_feedback(item) for item in feedback]}


@router.post("/opportunities/{opportunity_id}/feedback")
async def create_opportunity_feedback(
    opportunity_id: str,
    request: AgentFeedbackRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Record user feedback on one synthesized gap."""
    _get_owned_user_niche(request.market_id, dependencies, current_user)
    if dependencies.opportunity_repository.get_opportunity(opportunity_id) is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    try:
        feedback = AgentFeedback.create(
            user_niche_id=request.market_id,
            opportunity_id=opportunity_id,
            action=request.action,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.agent_feedback_repository.save_agent_feedback(feedback)
    _record_agent_activity(
        dependencies,
        user_niche_id=request.market_id,
        event_type="feedback_recorded",
        title="Gap feedback recorded",
        detail=f"Feedback marked this gap as {feedback.action}.",
        metadata={
            "opportunity_id": opportunity_id,
            "action": feedback.action,
            "reason": feedback.reason,
        },
    )
    return _serialize_agent_feedback(feedback)


@router.get("/markets/{market_id}/agent/activity")
async def list_market_agent_activity(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
    limit: int = 25,
    event_type: str | None = None,
) -> dict[str, Any]:
    """Return recent user-visible activity for one niche research agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    bounded_limit = min(max(limit, 1), 100)
    activity = dependencies.agent_activity_repository.list_agent_activity(
        user_niche_id=market_id,
        event_type=event_type,
        limit=bounded_limit,
    )
    return {"activity": [_serialize_agent_activity(item) for item in activity]}


@router.get("/markets/{market_id}/agent/runs")
async def list_market_agent_runs(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
    limit: int = 10,
) -> dict[str, Any]:
    """Return recent run-memory events for one niche agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    bounded_limit = min(max(limit, 1), 50)
    activity = dependencies.agent_activity_repository.list_agent_activity(
        user_niche_id=market_id,
        limit=100,
    )
    runs = [
        item
        for item in activity
        if item.event_type in {"run_started", "run_completed"}
    ][:bounded_limit]
    return {"runs": [_serialize_agent_activity(item) for item in runs]}


@router.get("/markets/{market_id}/agent/alerts")
async def list_market_agent_alerts(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
    status: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Return proactive threshold alerts for one niche agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    bounded_limit = min(max(limit, 1), 100)
    alerts = dependencies.agent_alert_repository.list_agent_alerts(
        user_niche_id=market_id,
        status=status,
        limit=bounded_limit,
    )
    return {"alerts": [_serialize_agent_alert(item) for item in alerts]}


@router.patch("/markets/{market_id}/agent/alerts/{alert_id}/acknowledge")
async def acknowledge_market_agent_alert(
    market_id: str,
    alert_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Mark one proactive alert as acknowledged."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    alert = dependencies.agent_alert_repository.get_agent_alert(alert_id)
    if alert is None or alert.user_niche_id != market_id:
        raise HTTPException(status_code=404, detail="Alert not found")
    acknowledged = dependencies.agent_alert_repository.acknowledge_agent_alert(
        alert_id,
    )
    if acknowledged is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _serialize_agent_alert(acknowledged)


@router.get("/markets/{market_id}/agent/follow-ups")
async def list_market_agent_follow_ups(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
    status: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Return stored follow-up questions for one niche agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    bounded_limit = min(max(limit, 1), 100)
    follow_ups = dependencies.agent_follow_up_repository.list_agent_follow_ups(
        user_niche_id=market_id,
        status=status,
        limit=bounded_limit,
    )
    return {"follow_ups": [_serialize_agent_follow_up(item) for item in follow_ups]}


@router.post("/markets/{market_id}/agent/follow-ups")
async def create_market_agent_follow_up(
    market_id: str,
    request: AgentFollowUpRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Store a follow-up question or instruction for future agent work."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    if (
        request.opportunity_id is not None
        and dependencies.opportunity_repository.get_opportunity(request.opportunity_id)
        is None
    ):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if (
        request.cluster_id is not None
        and dependencies.cluster_repository.get_cluster(request.cluster_id) is None
    ):
        raise HTTPException(status_code=404, detail="Cluster not found")

    try:
        follow_up = AgentFollowUp.create(
            user_niche_id=market_id,
            question=request.question,
            opportunity_id=request.opportunity_id,
            cluster_id=request.cluster_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.agent_follow_up_repository.save_agent_follow_up(follow_up)
    _record_agent_activity(
        dependencies,
        user_niche_id=market_id,
        event_type="follow_up_recorded",
        title="Follow-up recorded",
        detail=follow_up.question,
        metadata={
            "follow_up_id": follow_up.id,
            "opportunity_id": follow_up.opportunity_id,
            "cluster_id": follow_up.cluster_id,
        },
    )
    return _serialize_agent_follow_up(follow_up)


@router.get("/markets/{market_id}/agent/memory")
async def get_market_agent_memory(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return a compact summary of persisted agent memory for one niche."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    preferences = dependencies.agent_preferences_repository.get_agent_preferences(
        market_id,
    ) or AgentPreferences.create(user_niche_id=market_id)
    feedback = dependencies.agent_feedback_repository.list_agent_feedback(
        user_niche_id=market_id,
    )
    niche_id = user_niche.template_niche_id
    sources = (
        dependencies.niche_source_repository.list_niche_sources(niche_id)
        if niche_id is not None
        else []
    )
    summary = build_agent_memory_summary(
        user_niche=user_niche,
        preferences=preferences,
        feedback=feedback,
        sources=sources,
    )
    return {
        "market_id": summary.market_id,
        "headline": summary.headline,
        "learned_preferences": summary.learned_preferences,
        "source_notes": summary.source_notes,
        "feedback_notes": summary.feedback_notes,
    }


@router.get("/sources")
async def list_sources(
    competitor_id: str | None = None,
    market_id: str | None = None,
    enabled: bool | None = None,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored sources (placeholder — use /markets/{id}/sources)."""
    return {
        "sources": [],
        "summary": _source_coverage_summary([]),
    }


@router.post("/competitors/{competitor_id}/sources")
async def create_competitor_source(
    competitor_id: str,
    request: NicheSourceRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Create a source for one company (use /markets/{market_id}/sources instead)."""
    raise HTTPException(
        status_code=422,
        detail="Use POST /markets/{market_id}/sources instead",
    )


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
            agent_preferences_repository=dependencies.agent_preferences_repository,
            agent_activity_repository=dependencies.agent_activity_repository,
            agent_alert_repository=dependencies.agent_alert_repository,
            niche_source_repository=dependencies.niche_source_repository,
            user_niche_repository=dependencies.user_niche_repository,
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
            user_niche_id=request.market_id,
            default_limit=request.default_limit,
            similarity_threshold=request.similarity_threshold,
        )
    )
    return _serialize_pipeline_result(result)


@router.get("/pipeline/schedule")
async def get_pipeline_schedule() -> dict[str, Any]:
    """Return the pipeline cron schedule and computed next run time."""
    from shared.config import get_app_config
    cron = get_app_config().PIPELINE_SCHEDULE
    next_run_at = _next_cron_run(cron)
    return {
        "cron": cron,
        "next_run_at": next_run_at.isoformat() if next_run_at else None,
    }


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


def _enqueue_pipeline(market_id: str) -> None:
    """Push a pipeline task onto the Celery queue.

    Logs a warning and continues if Redis is unavailable — the daily
    Beat schedule will pick up the market on its next run.
    """
    try:
        from workers.tasks import run_pipeline_for_market
        import redis as redis_lib
        run_pipeline_for_market.delay(market_id)
        log_event(logger, "pipeline_enqueued", market_id=market_id)
    except redis_lib.exceptions.ConnectionError as exc:
        log_event(
            logger,
            "pipeline_enqueue_skipped",
            level=logging.WARNING,
            market_id=market_id,
            reason="Redis unavailable",
            error=str(exc),
        )
    except Exception as exc:
        log_event(
            logger,
            "pipeline_enqueue_failed",
            level=logging.ERROR,
            market_id=market_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )


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


def _current_user_id(current_user: User | Any) -> str | None:
    return current_user.id if isinstance(current_user, User) else None


def _get_owned_user_niche(
    market_id: str,
    dependencies: SignalApiDependencies,
    current_user: User | Any,
) -> UserNiche:
    user_niche = dependencies.user_niche_repository.get_user_niche(market_id)
    user_id = _current_user_id(current_user)
    if user_niche is None or (
        user_id is not None
        and user_niche.user_id is not None
        and str(user_niche.user_id) != str(user_id)
    ):
        raise HTTPException(status_code=404, detail="Market not found")
    return user_niche


def _scoped_signal_ids(
    dependencies: SignalApiDependencies,
    *,
    competitor_id: str | None = None,
    market_id: str | None = None,
) -> set[str]:
    return {
        signal.id
        for signal in dependencies.signal_repository.list_signals()
        if (competitor_id is None or signal.niche_company_id == competitor_id)
        and (market_id is None or signal.niche_id == market_id)
    }


def _company_breadth_for_signal_ids(
    dependencies: SignalApiDependencies,
    signal_ids: list[str],
    *,
    market_id: str | None = None,
    _signals_by_id: dict | None = None,
) -> dict[str, Any]:
    signal_id_set = set(signal_ids)
    if _signals_by_id is not None:
        signals = [_signals_by_id[sid] for sid in signal_id_set if sid in _signals_by_id]
    else:
        signals = [s for s in dependencies.signal_repository.list_signals() if s.id in signal_id_set]
    company_ids = sorted(
        {signal.niche_company_id for signal in signals if signal.niche_company_id is not None}
    )
    resolved_market_id = market_id or _single_niche_id(signals)
    market_company_count = (
        _market_company_count(dependencies, resolved_market_id)
        if resolved_market_id is not None
        else None
    )
    return {
        "company_ids": company_ids,
        "company_names": [],
        "company_count": len(company_ids),
        "market_company_count": market_company_count,
    }


def _single_niche_id(signals: list[Signal]) -> str | None:
    niche_ids = {signal.niche_id for signal in signals if signal.niche_id is not None}
    if len(niche_ids) != 1:
        return None
    return next(iter(niche_ids))


def _market_company_count(
    dependencies: SignalApiDependencies,
    user_niche_id: str,
) -> int:
    user_niche = dependencies.user_niche_repository.get_user_niche(user_niche_id)
    if user_niche is None or user_niche.template_niche_id is None:
        return 0
    return len(
        dependencies.niche_company_repository.list_niche_companies(
            user_niche.template_niche_id
        )
    )


def _market_report_title(
    dependencies: SignalApiDependencies,
    market_id: str | None,
) -> str | None:
    if market_id is None:
        return None
    user_niche = dependencies.user_niche_repository.get_user_niche(market_id)
    if user_niche is None:
        return None
    return f"{user_niche.job} Market Gap Report"


def _serialize_market(user_niche: UserNiche) -> dict[str, Any]:
    return {
        "id": user_niche.id,
        "name": user_niche.job,
        "description": user_niche.category,
        "target_user": user_niche.buyer,
        "idea_prompt": None,
        "created_at": user_niche.created_at.isoformat() if user_niche.created_at else None,
    }


def _serialize_signal(
    signal: Signal,
    dependencies: SignalApiDependencies | None = None,
    *,
    _signals_by_id: dict | None = None,
) -> dict[str, Any]:
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
        "competitor_id": signal.niche_company_id,
        "competitor_name": None,
        "market_id": signal.niche_id,
        "market_name": None,
        "evidence_url": signal.evidence_url,
        "evidence_text": signal.evidence_text,
        "detected_at": signal.detected_at.isoformat() if signal.detected_at else None,
    }


def _serialize_niche_company(company: NicheCompany) -> dict[str, Any]:
    return {
        "id": company.id,
        "name": company.name,
        "website": company.website,
        "category": None,
        "description": None,
        "market_id": company.niche_id,
        "created_at": company.created_at.isoformat() if company.created_at else None,
    }


def _serialize_niche_source(source: NicheSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "competitor_id": source.company_id,
        "competitor_name": None,
        "market_id": source.niche_id,
        "market_name": None,
        "locator": source.locator,
        "source_type": source.source_type,
        "source_family": source.source_family,
        "enabled": source.health_status != "paused",
        "limit": None,
        "scan_frequency": None,
        "last_scanned_at": (
            source.last_scanned_at.isoformat() if source.last_scanned_at else None
        ),
        "last_error": None,
        "health": None,
        "options": {},
    }


def _source_coverage_summary(sources: list[NicheSource]) -> dict[str, Any]:
    by_family: dict[str, dict[str, Any]] = {}
    company_ids: set[str] = set()
    active_count = 0

    for source in sources:
        family = source.source_family or "unknown"
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
        if source.health_status != "paused":
            active_count += 1
            entry["active_count"] += 1
        if source.company_id:
            company_ids.add(source.company_id)

    for family, entry in by_family.items():
        entry_company_ids = {
            source.company_id
            for source in sources
            if source.company_id and (source.source_family or "unknown") == family
        }
        entry["company_count"] = len(entry_company_ids)

    return {
        "source_count": len(sources),
        "active_count": active_count,
        "disabled_count": len(sources) - active_count,
        "error_count": 0,
        "company_count": len(company_ids),
        "by_family": sorted(
            by_family.values(),
            key=lambda item: (-item["source_count"], item["source_family"]),
        ),
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
        "market_id": preferences.user_niche_id,
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
        "market_id": feedback.user_niche_id,
        "opportunity_id": feedback.opportunity_id,
        "action": feedback.action,
        "reason": feedback.reason,
        "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
    }


def _serialize_agent_activity(activity: AgentActivity) -> dict[str, Any]:
    return {
        "id": activity.id,
        "market_id": activity.user_niche_id,
        "event_type": activity.event_type,
        "title": activity.title,
        "detail": activity.detail,
        "metadata": activity.metadata,
        "created_at": (
            activity.created_at.isoformat() if activity.created_at else None
        ),
    }


def _serialize_agent_alert(alert: AgentAlert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "market_id": alert.user_niche_id,
        "alert_type": alert.alert_type,
        "title": alert.title,
        "severity": alert.severity,
        "status": alert.status,
        "detail": alert.detail,
        "metadata": alert.metadata,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "acknowledged_at": (
            alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        ),
    }


def _serialize_agent_follow_up(follow_up: AgentFollowUp) -> dict[str, Any]:
    return {
        "id": follow_up.id,
        "market_id": follow_up.user_niche_id,
        "question": follow_up.question,
        "opportunity_id": follow_up.opportunity_id,
        "cluster_id": follow_up.cluster_id,
        "status": follow_up.status,
        "response": follow_up.response,
        "metadata": follow_up.metadata,
        "created_at": (
            follow_up.created_at.isoformat() if follow_up.created_at else None
        ),
        "updated_at": (
            follow_up.updated_at.isoformat() if follow_up.updated_at else None
        ),
    }


def _serialize_agent_brief(
    user_niche: UserNiche,
    preferences: AgentPreferences,
) -> dict[str, Any]:
    return {
        "market_id": user_niche.id,
        "niche_name": user_niche.job,
        "description": user_niche.category,
        "target_user": user_niche.buyer,
        "objective": None,
        "extra_instructions": preferences.extra_instructions,
    }


def _record_agent_activity(
    dependencies: SignalApiDependencies,
    *,
    user_niche_id: str,
    event_type: str,
    title: str,
    detail: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    dependencies.agent_activity_repository.save_agent_activity(
        AgentActivity.create(
            user_niche_id=user_niche_id,
            event_type=event_type,
            title=title,
            detail=detail,
            metadata=metadata,
        )
    )


def _serialize_cluster(
    cluster: SignalCluster,
    dependencies: SignalApiDependencies | None = None,
    *,
    market_id: str | None = None,
    _signals_by_id: dict | None = None,
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
                _signals_by_id=_signals_by_id,
            )
        )
    return serialized


def _serialize_opportunity(
    opportunity: Opportunity,
    dependencies: SignalApiDependencies | None = None,
    *,
    market_id: str | None = None,
    _signals_by_id: dict | None = None,
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
                _signals_by_id=_signals_by_id,
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


def _next_cron_run(cron: str) -> datetime | None:
    """Return the next UTC datetime for a simple daily cron expression.

    Handles the common 5-field form `minute hour * * *`.
    Returns None if the expression can't be parsed.
    """
    from datetime import timedelta
    parts = cron.strip().split()
    if len(parts) != 5:
        return None
    try:
        minute = int(parts[0])
        hour = int(parts[1])
    except ValueError:
        return None

    now = datetime.now(UTC)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


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
