"""API endpoints for market signal workflows."""
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from api.routes.auth import get_current_user
from pydantic import BaseModel, Field

from application.agent import (
    AgentColdStartPlan,
    AgentColdStartService,
    AgentActionExecutor,
    AgentPlannerInput,
    AgentPlannerService,
    build_agent_memory_summary,
    rank_opportunities_with_feedback,
)
from application.agent.action_keys import agent_action_dedupe_key
from application.opportunity import (
    OpportunitySynthesisContext,
    merge_near_duplicate_opportunities,
    qualify_cluster_for_opportunity,
)
from application.ingestion import SourceAdapter
from application.ports import (
    AgentActionRepository,
    AgentActivityRepository,
    AgentAlertRepository,
    AgentFeedbackRepository,
    AgentFollowUpRepository,
    AgentPreferencesRepository,
    ClusterRepository,
    NicheCompanyRepository,
    NicheRepository,
    NicheSourceRepository,
    OpportunityRepository,
    PipelineRunMetricsRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    UserNicheRepository,
)
from application.reporting import MarketSignalReport, ReportingService
from application.source_quality import source_quality_status, source_scan_eligibility
from application.source_suggestions import SourceReplacementSuggestionService
from domain.cluster import SignalCluster
from domain.agent import (
    AgentAction,
    AgentActivity,
    AgentAlert,
    AgentFeedback,
    AgentFollowUp,
    AgentPreferences,
)
from domain.niche import (
    Niche,
    NicheCompany,
    NicheSource,
    NicheSourceRunStats,
    UserNiche,
)
from domain.user import User
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.signal import Signal
from domain.source import SourceCandidate, SourceInput, SourceReplacementSuggestion
from infrastructure.db import (
    InMemoryAgentActionRepository,
    InMemoryAgentActivityRepository,
    InMemoryAgentAlertRepository,
    InMemoryAgentFeedbackRepository,
    InMemoryAgentFollowUpRepository,
    InMemoryAgentPreferencesRepository,
    InMemoryClusterRepository,
    InMemoryNicheCompanyRepository,
    InMemoryNicheRepository,
    InMemoryNicheSourceRepository,
    InMemoryOpportunityRepository,
    InMemoryPipelineRunMetricsRepository,
    InMemoryPostRepository,
    InMemoryScoreRepository,
    InMemorySignalRepository,
    InMemoryUserNicheRepository,
)
from infrastructure.email import EmailClient, EmailSendResult
from infrastructure.llm import EmbeddingClient, LLMClient
from shared.config import get_app_config
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

    id: str | None = None
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


class AgentFollowUpAnswerRequest(BaseModel):
    """HTTP request body for answering a follow-up question."""

    response: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NicheSourceRequest(BaseModel):
    """HTTP request body for adding a source to a niche."""

    locator: str = Field(min_length=1)
    source_type: str = Field(default="web", min_length=1)
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)


class NicheSourceUpdateRequest(BaseModel):
    """HTTP request body for updating a monitored source."""

    source_type: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None
    limit: int | None = None
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
    agent_action_repository: AgentActionRepository = field(
        default_factory=InMemoryAgentActionRepository
    )
    niche_repository: NicheRepository = field(
        default_factory=InMemoryNicheRepository
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
    company_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Return persisted extracted signals, optionally filtered by scope."""
    signals = dependencies.signal_repository.list_signals()
    if company_id is not None:
        signals = [s for s in signals if s.niche_company_id == company_id]
    if market_id is not None:
        niche_id = _template_niche_id(market_id, dependencies)
        signals = [s for s in signals if s.niche_id == niche_id]
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
    company_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Return persisted signal clusters, optionally filtered by scope."""
    clusters = dependencies.cluster_repository.list_clusters()
    all_signals = dependencies.signal_repository.list_signals()
    if company_id is not None or market_id is not None:
        niche_id = _template_niche_id(market_id, dependencies)
        scoped_signal_ids = {
            s.id
            for s in all_signals
            if (company_id is None or s.niche_company_id == company_id)
            and (niche_id is None or s.niche_id == niche_id)
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
    company_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Return synthesized product opportunities, optionally filtered by scope."""
    opportunities = dependencies.opportunity_repository.list_opportunities()
    all_signals = dependencies.signal_repository.list_signals()
    if company_id is not None or market_id is not None:
        niche_id = _template_niche_id(market_id, dependencies)
        scoped_signal_ids = {
            s.id
            for s in all_signals
            if (company_id is None or s.niche_company_id == company_id)
            and (niche_id is None or s.niche_id == niche_id)
        }
        opportunities = [
            o for o in opportunities
            if any(sid in scoped_signal_ids for sid in o.evidence_signal_ids)
        ]
    opportunities = merge_near_duplicate_opportunities(opportunities)
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


@router.get("/templates")
async def list_templates(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return operator-curated niche templates from the catalog."""
    niches = dependencies.niche_repository.list_niches()
    templates = []
    for niche in niches:
        companies = dependencies.niche_company_repository.list_niche_companies(niche.id)
        sources = dependencies.niche_source_repository.list_niche_sources(niche.id)
        source_families = sorted({s.source_family for s in sources})
        templates.append(
            _serialize_niche_template(niche, companies, source_families)
        )
    return {"templates": templates}


@router.post("/templates/{template_id}/apply")
async def apply_template(
    template_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a user_niche from a catalog template and return it as a market."""
    niche = dependencies.niche_repository.get_niche(template_id)
    if niche is None:
        raise HTTPException(status_code=404, detail="Template not found")

    user_id = _current_user_id(current_user) or "anonymous"
    existing = _find_user_niche_for_template(dependencies, user_id, niche.id)
    if existing is not None:
        return _serialize_market(existing)

    user_niche = UserNiche.create(
        user_id=user_id,
        job=niche.job,
        buyer=niche.buyer,
        category=niche.category,
        template_niche_id=niche.id,
    )
    dependencies.user_niche_repository.save_user_niche(user_niche)
    _enqueue_pipeline(user_niche.id)
    return _serialize_market(user_niche)


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
            for un in _dedupe_user_niches_for_display(
                dependencies.user_niche_repository.list_user_niches(user_id)
            )
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
    buyer = request.target_user or "general"
    category = request.description or "general"
    existing = _find_user_niche_for_definition(
        dependencies,
        user_id,
        job=request.name,
        buyer=buyer,
        category=category,
    )
    if existing is not None:
        return _serialize_market(existing)

    try:
        user_niche = UserNiche.create(
            user_id=user_id,
            job=request.name,
            buyer=buyer,
            category=category,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.user_niche_repository.save_user_niche(user_niche)
    _enqueue_pipeline(user_niche.id)
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


@router.get("/markets/{market_id}/companies")
async def list_market_companies(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return companies linked to one niche."""
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    niche_id = user_niche.template_niche_id
    if niche_id is None:
        return {"companies": []}
    companies = dependencies.niche_company_repository.list_niche_companies(niche_id)
    return {"companies": [_serialize_niche_company(c) for c in companies]}


@router.post("/markets/{market_id}/companies")
async def create_market_company(
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
    stats_by_source = _niche_source_stats_by_source_id(
        dependencies.niche_source_repository,
        sources,
    )
    app_config = get_app_config()
    allow_auth_sources = bool(app_config.REDDIT_CLIENT_ID and app_config.REDDIT_CLIENT_SECRET)
    replacement_service = SourceReplacementSuggestionService()
    return {
        "sources": [
            _serialize_niche_source(
                s,
                stats_by_source.get(s.id),
                allow_auth_sources=allow_auth_sources,
                replacement_suggestions=replacement_service.suggest_for_source(
                    s,
                    niche=user_niche,
                    stats=stats_by_source.get(s.id),
                    existing_sources=sources,
                ),
            )
            for s in sources
        ],
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
            enabled=request.enabled,
            limit=_option_int(request.options, "limit"),
            scan_frequency=_option_str(request.options, "scan_frequency"),
            last_error=_option_str(request.options, "last_error"),
            options=request.options,
            tier=_option_int(request.options, "tier"),
            signal_quality_score=_option_float(request.options, "signal_quality_score"),
            access_mode=str(request.options.get("access_mode") or "unknown"),
            requires_proxy=bool(request.options.get("requires_proxy", False)),
            requires_auth=bool(request.options.get("requires_auth", False)),
            recommended_cadence=_option_str(request.options, "recommended_cadence"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dependencies.niche_source_repository.save_niche_sources([source])
    return _serialize_niche_source(source)


@router.patch("/sources/{source_id}")
async def update_source(
    source_id: str,
    request: NicheSourceUpdateRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update a monitored source owned by the current user."""
    source, _user_niche = _get_owned_niche_source(
        source_id,
        dependencies,
        current_user,
    )
    fields = _model_fields_set(request)
    merged_options = dict(source.options)
    if request.options is not None:
        merged_options.update(request.options)

    try:
        updated_source = replace(
            source,
            source_type=(
                request.source_type
                if "source_type" in fields and request.source_type is not None
                else source.source_type
            ),
            enabled=(
                request.enabled
                if "enabled" in fields and request.enabled is not None
                else source.enabled
            ),
            limit=(
                request.limit
                if "limit" in fields and request.limit is not None
                else source.limit
            ),
            scan_frequency=(
                request.scan_frequency
                if "scan_frequency" in fields
                else source.scan_frequency
            ),
            options=merged_options,
            source_family=str(
                merged_options.get("source_family")
                or source.source_family
                or request.source_type
                or "web"
            ),
            updated_at=datetime.now(tz=UTC),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not dependencies.niche_source_repository.update_niche_source(updated_source):
        raise HTTPException(status_code=404, detail="Source not found")
    return _serialize_niche_source(
        updated_source,
        dependencies.niche_source_repository.get_niche_source_run_stats(source_id),
    )


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a monitored source owned by the current user."""
    _get_owned_niche_source(source_id, dependencies, current_user)
    deleted = dependencies.niche_source_repository.delete_niche_source(source_id)
    return {"id": source_id, "deleted": deleted}


@router.get("/reports/latest")
async def get_latest_report(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    company_id: str | None = None,
    market_id: str | None = None,
) -> dict[str, Any]:
    """Generate and return the latest report from persisted clusters."""
    clusters = dependencies.cluster_repository.list_clusters()
    opportunities = dependencies.opportunity_repository.list_opportunities()
    if company_id is not None or market_id is not None:
        scoped_signal_ids = _scoped_signal_ids(
            dependencies,
            company_id=company_id,
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


@router.get("/companies")
async def list_companies(
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored companies (placeholder — use /markets/{id}/companies)."""
    return {"companies": []}


@router.get("/companies/{company_id}/sources")
async def list_company_sources(
    company_id: str,
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


@router.get("/markets/{market_id}/agent/plan")
async def get_market_agent_plan(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the agent's current proposed next actions for one niche."""
    planner_input = _agent_planner_input(market_id, dependencies, current_user)
    actions = AgentPlannerService().plan_actions(planner_input)
    return {"actions": [_serialize_agent_action(action) for action in actions]}


@router.post("/markets/{market_id}/agent/actions/plan")
async def propose_market_agent_actions(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Persist the agent's current proposed next actions for one niche."""
    planner_input = _agent_planner_input(market_id, dependencies, current_user)
    planned_actions = AgentPlannerService().plan_actions(planner_input)
    existing_keys = {
        agent_action_dedupe_key(action)
        for action in dependencies.agent_action_repository.list_agent_actions(
            user_niche_id=market_id,
            limit=100,
        )
    }
    saved_actions: list[AgentAction] = []
    for action in planned_actions:
        key = agent_action_dedupe_key(action)
        if key in existing_keys:
            continue
        dependencies.agent_action_repository.save_agent_action(action)
        existing_keys.add(key)
        saved_actions.append(action)
    return {"actions": [_serialize_agent_action(action) for action in saved_actions]}


@router.get("/markets/{market_id}/agent/actions")
async def list_market_agent_actions(
    market_id: str,
    status: str | None = None,
    action_type: str | None = None,
    limit: int | None = None,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List stored agent actions for one niche."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    actions = dependencies.agent_action_repository.list_agent_actions(
        user_niche_id=market_id,
        status=status,
        action_type=action_type,
        limit=limit,
    )
    return {"actions": [_serialize_agent_action(action) for action in actions]}


@router.post("/markets/{market_id}/agent/actions/{action_id}/approve")
async def approve_market_agent_action(
    market_id: str,
    action_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Approve a proposed agent action for one niche."""
    return _update_market_agent_action_status(
        market_id,
        action_id,
        "approved",
        dependencies,
        current_user,
    )


@router.post("/markets/{market_id}/agent/actions/{action_id}/dismiss")
async def dismiss_market_agent_action(
    market_id: str,
    action_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Dismiss a proposed agent action for one niche."""
    return _update_market_agent_action_status(
        market_id,
        action_id,
        "dismissed",
        dependencies,
        current_user,
    )


@router.post("/markets/{market_id}/agent/actions/execute")
async def execute_market_agent_actions(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute approved agent actions for one niche."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    result = AgentActionExecutor(
        dependencies.agent_action_repository,
        dependencies.niche_source_repository,
        dependencies.agent_follow_up_repository,
        dependencies.agent_alert_repository,
    ).execute_approved_actions(market_id)
    return {
        "executed_count": result.executed_count,
        "failed_count": result.failed_count,
        "skipped_count": result.skipped_count,
    }


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
    opportunity = dependencies.opportunity_repository.get_opportunity(opportunity_id)
    if opportunity is None:
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
    _apply_feedback_to_agent_preferences(
        dependencies,
        market_id=request.market_id,
        opportunity=opportunity,
        action=feedback.action,
    )
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
    include_diagnostics: bool = False,
) -> dict[str, Any]:
    """Return recent user-visible activity for one niche research agent."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    bounded_limit = min(max(limit, 1), 100)
    activity = dependencies.agent_activity_repository.list_agent_activity(
        user_niche_id=market_id,
        event_type=event_type,
        limit=bounded_limit if event_type or include_diagnostics else 100,
    )
    if not include_diagnostics and event_type is None:
        activity = _user_visible_agent_activity(activity)[:bounded_limit]
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


@router.post("/markets/{market_id}/agent/follow-ups/{follow_up_id}/answer")
async def answer_market_agent_follow_up(
    market_id: str,
    follow_up_id: str,
    request: AgentFollowUpAnswerRequest,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Store an answer for one follow-up question."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    if _find_market_follow_up(dependencies, market_id, follow_up_id) is None:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    updated = dependencies.agent_follow_up_repository.update_agent_follow_up(
        follow_up_id,
        status="answered",
        response=request.response,
        metadata=request.metadata,
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="Follow-up could not be answered")
    _record_agent_activity(
        dependencies,
        user_niche_id=market_id,
        event_type="follow_up_answered",
        title="Follow-up answered",
        detail=updated.question,
        metadata={"follow_up_id": updated.id},
    )
    return _serialize_agent_follow_up(updated)


@router.post("/markets/{market_id}/agent/follow-ups/{follow_up_id}/dismiss")
async def dismiss_market_agent_follow_up(
    market_id: str,
    follow_up_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Dismiss one follow-up question."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    if _find_market_follow_up(dependencies, market_id, follow_up_id) is None:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    updated = dependencies.agent_follow_up_repository.update_agent_follow_up(
        follow_up_id,
        status="dismissed",
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="Follow-up could not be dismissed")
    _record_agent_activity(
        dependencies,
        user_niche_id=market_id,
        event_type="follow_up_dismissed",
        title="Follow-up dismissed",
        detail=updated.question,
        metadata={"follow_up_id": updated.id},
    )
    return _serialize_agent_follow_up(updated)


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
    company_id: str | None = None,
    market_id: str | None = None,
    enabled: bool | None = None,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
) -> dict[str, Any]:
    """Return monitored sources (placeholder — use /markets/{id}/sources)."""
    return {
        "sources": [],
        "summary": _source_coverage_summary([]),
    }


@router.post("/companies/{company_id}/sources")
async def create_company_source(
    company_id: str,
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
    app_config = get_app_config()
    _ensure_pipeline_dependencies(
        dependencies,
        request,
        require_email=app_config.PIPELINE_EMAIL_ENABLED,
    )
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
            llm_client=dependencies.llm_client,
            relevance_llm_client=dependencies.relevance_llm_client,
            embedding_client=dependencies.embedding_client,
            email_client=dependencies.email_client,
            recipient=request.recipient,
            send_email=app_config.PIPELINE_EMAIL_ENABLED,
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
    cron = get_app_config().PIPELINE_SCHEDULE
    next_run_at = _next_cron_run(cron)
    return {
        "cron": cron,
        "next_run_at": next_run_at.isoformat() if next_run_at else None,
    }


@router.get("/pipeline/diagnostics")
async def get_pipeline_diagnostics(
    market_id: str | None = None,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User | Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Return sanitized runtime diagnostics for the scheduled agent worker."""
    if market_id is not None:
        _get_owned_user_niche(market_id, dependencies, current_user)

    from workers.jobs import check_worker_readiness

    readiness = check_worker_readiness(
        user_niche_id=market_id,
        dependencies=dependencies,
    )
    cron = str(readiness["pipeline_schedule"])
    next_run_at = _next_cron_run(cron)
    return {
        **readiness,
        "next_run_at": next_run_at.isoformat() if next_run_at else None,
        "diagnostics": _pipeline_diagnostic_messages(readiness),
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


@router.get("/markets/{market_id}/pipeline/status")
async def get_market_pipeline_status(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the pipeline run status for one market derived from activity events."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    events = dependencies.agent_activity_repository.list_agent_activity(
        user_niche_id=market_id, limit=20
    )
    events_sorted = sorted(
        events,
        key=lambda e: _activity_created_at(e) or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    last_event = events_sorted[0] if events_sorted else None

    latest_run_start = next((e for e in events_sorted if e.event_type == "run_started"), None)

    if latest_run_start is None:
        status = "pending"
    else:
        # Only consider events from the most recent run onwards
        start_time = _activity_created_at(latest_run_start)
        current_run = [
            e for e in events_sorted
            if start_time is None
            or (
                (event_time := _activity_created_at(e)) is not None
                and event_time >= start_time
            )
        ]
        has_completed = any(e.event_type == "run_completed" for e in current_run)
        if has_completed:
            status = "done"
        elif start_time is not None:
            age_seconds = (datetime.now(UTC) - start_time).total_seconds()
            status = "failed" if age_seconds > 900 else "running"
        else:
            status = "running"

    last_event_at = _activity_created_at(last_event) if last_event else None
    return {
        "status": status,
        "last_event_type": last_event.event_type if last_event else None,
        "last_event_at": last_event_at.isoformat() if last_event_at else None,
    }


@router.get("/markets/{market_id}/pipeline/live-feed")
async def get_market_pipeline_live_feed(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Return live per-item visibility for an active pipeline run."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    all_activity = dependencies.agent_activity_repository.list_agent_activity(
        user_niche_id=market_id, limit=200
    )
    # Scope to current run: slice from newest down to the most recent run_started
    run_start_idx = next(
        (i for i, a in enumerate(all_activity) if a.event_type == "run_started"),
        len(all_activity),
    )
    current_run = all_activity[: run_start_idx + 1]

    live_event_types = {
        "post_evaluating",
        "post_accepted",
        "post_filtered",
        "posts_filtered",
        "signals_extracted",
        "clusters_formed",
        "gaps_synthesized",
        "theme_promoted",
        "theme_rejected",
        "run_completed",
    }
    latest_live_event = next(
        (a for a in current_run if a.event_type in live_event_types), None
    )
    current_item = (
        latest_live_event
        if latest_live_event is not None
        and latest_live_event.event_type == "post_evaluating"
        else None
    )
    recent_decisions = [
        a for a in current_run
        if a.event_type in ("post_accepted", "post_filtered")
    ][:5]

    return {
        "current_item": _serialize_agent_activity(current_item) if current_item else None,
        "recent_decisions": [_serialize_agent_activity(a) for a in recent_decisions],
    }


@router.post("/markets/{market_id}/pipeline/trigger")
async def trigger_market_pipeline(
    market_id: str,
    dependencies: SignalApiDependencies = Depends(get_signal_api_dependencies),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Enqueue a background pipeline run for one owned niche."""
    _get_owned_user_niche(market_id, dependencies, current_user)
    _enqueue_pipeline(market_id)
    return {"status": "queued"}


def _enqueue_pipeline(market_id: str) -> None:
    """Push a pipeline task onto the Celery queue via the configured broker.

    Uses celery_app.send_task (by name) so the API process doesn't need a
    bound task instance — avoiding the @shared_task / no-current-app trap.
    Logs a warning and continues if Redis is unavailable.
    """
    try:
        from workers.celery_app import celery_app
        celery_app.send_task(
            "workers.tasks.run_pipeline_for_market",
            args=[market_id],
        )
        log_event(logger, "pipeline_enqueued", market_id=market_id)
    except Exception as exc:
        level = logging.WARNING if "connect" in str(exc).lower() else logging.ERROR
        log_event(
            logger,
            "pipeline_enqueue_failed",
            level=level,
            market_id=market_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )


def _activity_created_at(activity: AgentActivity | None) -> datetime | None:
    if activity is None or activity.created_at is None:
        return None
    value = activity.created_at
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _ensure_pipeline_dependencies(
    dependencies: SignalApiDependencies,
    request: PipelineRunRequest,
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
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline dependencies are not configured: {', '.join(missing)}",
        )


def _pipeline_diagnostic_messages(readiness: dict[str, object]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if not readiness.get("redis_configured"):
        messages.append(
            {
                "level": "warning",
                "message": "REDIS_URL is not configured; Celery Beat and workers cannot run.",
            }
        )
    if int(readiness.get("enabled_niche_source_count") or 0) < 1:
        messages.append(
            {
                "level": "warning",
                "message": "No enabled niche sources are available for scheduled scans.",
            }
        )
    if int(readiness.get("source_adapter_count") or 0) < 1:
        messages.append(
            {
                "level": "error",
                "message": "No source adapters are configured.",
            }
        )
    if not readiness.get("has_llm_client"):
        messages.append(
            {
                "level": "error",
                "message": "LLM client is not configured; filtering and synthesis will fail.",
            }
        )
    if not readiness.get("has_embedding_client"):
        messages.append(
            {
                "level": "error",
                "message": "Embedding client is not configured; clustering will fail.",
            }
        )
    if readiness.get("email_enabled") and not readiness.get("has_email_client"):
        messages.append(
            {
                "level": "error",
                "message": "Pipeline email is enabled but no email client is configured.",
            }
        )
    if readiness.get("email_enabled") and not readiness.get("report_recipient_configured"):
        messages.append(
            {
                "level": "error",
                "message": "Pipeline email is enabled but REPORT_RECIPIENT is missing.",
            }
        )
    if not messages:
        messages.append(
            {
                "level": "ok",
                "message": "Scheduled pipeline diagnostics look ready.",
            }
        )
    return messages


def _current_user_id(current_user: User | Any) -> str | None:
    return current_user.id if isinstance(current_user, User) else None


def _find_user_niche_for_template(
    dependencies: SignalApiDependencies,
    user_id: str,
    template_niche_id: str,
) -> UserNiche | None:
    for user_niche in dependencies.user_niche_repository.list_user_niches(user_id):
        if user_niche.template_niche_id == template_niche_id:
            return user_niche
    return None


def _find_user_niche_for_definition(
    dependencies: SignalApiDependencies,
    user_id: str,
    *,
    job: str,
    buyer: str,
    category: str,
) -> UserNiche | None:
    definition_key = _user_niche_definition_key(job, buyer, category)
    for user_niche in dependencies.user_niche_repository.list_user_niches(user_id):
        if _user_niche_display_keys(user_niche)[1] == definition_key:
            return user_niche
    return None


def _dedupe_user_niches_for_display(user_niches: list[UserNiche]) -> list[UserNiche]:
    deduped: list[UserNiche] = []
    seen_keys: set[tuple[str, str] | tuple[str, str, str, str]] = set()
    for user_niche in user_niches:
        template_key, definition_key = _user_niche_display_keys(user_niche)
        if template_key is not None and template_key in seen_keys:
            continue
        if definition_key in seen_keys:
            continue
        if template_key is not None:
            seen_keys.add(template_key)
        seen_keys.add(definition_key)
        deduped.append(user_niche)
    return deduped


def _user_niche_display_keys(
    user_niche: UserNiche,
) -> tuple[tuple[str, str] | None, tuple[str, str, str, str]]:
    template_key = (
        ("template", user_niche.template_niche_id)
        if user_niche.template_niche_id is not None
        else None
    )
    return (
        template_key,
        _user_niche_definition_key(
            user_niche.job,
            user_niche.buyer,
            user_niche.category,
        ),
    )


def _user_niche_definition_key(
    job: str,
    buyer: str,
    category: str,
) -> tuple[str, str, str, str]:
    return (
        "definition",
        _normalize_user_niche_key_part(job),
        _normalize_user_niche_key_part(buyer),
        _normalize_user_niche_key_part(category),
    )


def _normalize_user_niche_key_part(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def _template_niche_id(market_id: str | None, dependencies: SignalApiDependencies) -> str | None:
    """Resolve a user_niche_id (market_id) to its template_niche_id for signal filtering."""
    if market_id is None:
        return None
    user_niche = dependencies.user_niche_repository.get_user_niche(market_id)
    if user_niche is None:
        return market_id
    return str(user_niche.template_niche_id) if user_niche.template_niche_id else market_id


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


def _get_owned_niche_source(
    source_id: str,
    dependencies: SignalApiDependencies,
    current_user: User | Any,
) -> tuple[NicheSource, UserNiche]:
    user_id = _current_user_id(current_user)
    user_niches = (
        dependencies.user_niche_repository.list_user_niches(user_id)
        if user_id is not None
        else dependencies.user_niche_repository.list_all_user_niches()
    )
    for user_niche in user_niches:
        if user_niche.template_niche_id is None:
            continue
        for source in dependencies.niche_source_repository.list_niche_sources(
            user_niche.template_niche_id,
        ):
            if source.id == source_id:
                return source, user_niche
    raise HTTPException(status_code=404, detail="Source not found")


def _agent_planner_input(
    market_id: str,
    dependencies: SignalApiDependencies,
    current_user: User | Any,
) -> AgentPlannerInput:
    user_niche = _get_owned_user_niche(market_id, dependencies, current_user)
    niche_id = user_niche.template_niche_id
    sources = (
        dependencies.niche_source_repository.list_niche_sources(niche_id)
        if niche_id is not None
        else []
    )
    return AgentPlannerInput(
        user_niche=user_niche,
        preferences=dependencies.agent_preferences_repository.get_agent_preferences(
            market_id,
        ),
        sources=sources,
        recent_activity=dependencies.agent_activity_repository.list_agent_activity(
            user_niche_id=market_id,
            limit=25,
        ),
        alerts=dependencies.agent_alert_repository.list_agent_alerts(
            user_niche_id=market_id,
            limit=25,
        ),
        follow_ups=dependencies.agent_follow_up_repository.list_agent_follow_ups(
            user_niche_id=market_id,
            limit=25,
        ),
        opportunities=dependencies.opportunity_repository.list_opportunities(),
    )


def _update_market_agent_action_status(
    market_id: str,
    action_id: str,
    status: str,
    dependencies: SignalApiDependencies,
    current_user: User | Any,
) -> dict[str, Any]:
    _get_owned_user_niche(market_id, dependencies, current_user)
    matching_actions = [
        action
        for action in dependencies.agent_action_repository.list_agent_actions(
            user_niche_id=market_id,
            limit=100,
        )
        if action.id == action_id
    ]
    if not matching_actions:
        raise HTTPException(status_code=404, detail="Agent action not found")
    updated_action = dependencies.agent_action_repository.update_agent_action_status(
        action_id,
        status,
    )
    if updated_action is None:
        raise HTTPException(status_code=404, detail="Agent action not found")
    return {"action": _serialize_agent_action(updated_action)}


def _scoped_signal_ids(
    dependencies: SignalApiDependencies,
    *,
    company_id: str | None = None,
    market_id: str | None = None,
) -> set[str]:
    niche_id = _template_niche_id(market_id, dependencies)
    return {
        signal.id
        for signal in dependencies.signal_repository.list_signals()
        if (company_id is None or signal.niche_company_id == company_id)
        and (niche_id is None or signal.niche_id == niche_id)
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
    company_names = _company_names_for_ids(
        dependencies,
        company_ids,
        resolved_market_id,
        signals,
    )
    market_company_count = (
        _market_company_count(dependencies, resolved_market_id)
        if resolved_market_id is not None
        else None
    )
    source_keys = {
        _signal_source_key(signal)
        for signal in signals
        if _signal_source_key(signal) is not None
    }
    source_count = len(source_keys)
    if source_count == 0 and signals:
        source_count = 1
    return {
        "company_ids": company_ids,
        "company_names": company_names,
        "company_count": len(company_ids),
        "market_company_count": market_company_count,
        "evidence_source_count": source_count,
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


def _company_names_for_ids(
    dependencies: SignalApiDependencies,
    company_ids: list[str],
    market_id: str | None,
    signals: list[Signal],
) -> list[str]:
    if not company_ids:
        return []
    niche_id = _template_niche_id(market_id, dependencies) if market_id else None
    if niche_id is None:
        niche_id = _single_niche_id(signals)
    if niche_id is None:
        return []
    companies = dependencies.niche_company_repository.list_niche_companies(niche_id)
    name_by_id = {company.id: company.name for company in companies}
    return [name_by_id[company_id] for company_id in company_ids if company_id in name_by_id]


def _signal_source_key(signal: Signal) -> str | None:
    if signal.evidence_url:
        from urllib.parse import urlparse

        parsed = urlparse(signal.evidence_url)
        if parsed.netloc:
            return parsed.netloc.lower()
    if ":" in signal.post_id:
        return signal.post_id.split(":", 1)[0].lower()
    return None


def _source_label_for_signal(signal: Signal) -> str | None:
    source_key = _signal_source_key(signal)
    if source_key is None:
        return None
    labels = {
        "hn.algolia.com": "Hacker News",
        "news.ycombinator.com": "Hacker News",
        "api.github.com": "GitHub Issues",
        "github.com": "GitHub",
        "api.stackexchange.com": "Stack Overflow",
        "stackoverflow.com": "Stack Overflow",
        "reddit.com": "Reddit",
        "www.reddit.com": "Reddit",
        "g2.com": "G2",
        "www.g2.com": "G2",
        "capterra.com": "Capterra",
        "www.capterra.com": "Capterra",
    }
    return labels.get(source_key) or source_key


def _source_type_for_signal(signal: Signal) -> str | None:
    source_text = _source_text_for_signal(signal)
    if not source_text:
        return None
    if "github" in source_text:
        return "github_issues"
    if "stackoverflow" in source_text or "stackexchange" in source_text:
        return "stackoverflow"
    if "hn.algolia.com" in source_text or "news.ycombinator.com" in source_text:
        return "hackernews"
    if "reddit" in source_text:
        return "reddit"
    if "g2.com" in source_text:
        return "g2_reviews"
    if "capterra" in source_text:
        return "capterra_reviews"
    return None


def _source_family_breakdown(signals: list[Signal]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for signal in signals:
        family = _source_family_for_signal(signal) or "unknown"
        counts[family] = counts.get(family, 0) + 1
    return [
        {"source_family": family, "count": count}
        for family, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _serialize_evidence_item(
    signal: Signal,
    dependencies: SignalApiDependencies | None = None,
    *,
    market_id: str | None = None,
) -> dict[str, Any]:
    company_name = None
    if dependencies is not None and signal.niche_company_id is not None:
        names = _company_names_for_ids(
            dependencies,
            [signal.niche_company_id],
            market_id,
            [signal],
        )
        company_name = names[0] if names else None
    return {
        "id": signal.id,
        "signal_id": signal.id,
        "post_id": signal.post_id,
        "quote": signal.evidence_text or signal.pain,
        "pain": signal.pain,
        "url": signal.evidence_url,
        "source_label": _source_label_for_signal(signal),
        "source_family": _source_family_for_signal(signal),
        "source_type": _source_type_for_signal(signal),
        "company_id": signal.niche_company_id,
        "company_name": company_name,
        "category": signal.category,
        "urgency": signal.urgency,
        "severity": signal.severity,
        "confidence": signal.confidence,
        "detected_at": signal.detected_at.isoformat() if signal.detected_at else None,
    }


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


def _serialize_niche_template(
    niche: Niche,
    companies: list[NicheCompany],
    source_families: list[str],
) -> dict[str, Any]:
    return {
        "id": niche.id,
        "name": niche.job,
        "description": niche.description or niche.category,
        "company_count": len(companies),
        "company_names": [c.name for c in companies],
        "source_families": source_families,
    }


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
        "company_id": signal.niche_company_id,
        "company_name": None,
        "market_id": signal.niche_id,
        "market_name": None,
        "evidence_url": signal.evidence_url,
        "evidence_text": signal.evidence_text,
        "source_label": _source_label_for_signal(signal),
        "source_family": _source_family_for_signal(signal),
        "source_type": _source_type_for_signal(signal),
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


def _niche_source_stats_by_source_id(
    repository: NicheSourceRepository,
    sources: list[NicheSource],
) -> dict[str, NicheSourceRunStats]:
    if not sources:
        return {}
    stats = repository.list_niche_source_run_stats([source.id for source in sources])
    return {item.niche_source_id: item for item in stats}


def _serialize_niche_source(
    source: NicheSource,
    stats: NicheSourceRunStats | None = None,
    *,
    allow_proxy_sources: bool = False,
    allow_auth_sources: bool = False,
    replacement_suggestions: list[SourceReplacementSuggestion] | None = None,
) -> dict[str, Any]:
    lifecycle = _source_lifecycle(source)
    quality = source_quality_status(source, stats)
    scan_eligibility = source_scan_eligibility(
        source,
        stats,
        allow_proxy_sources=allow_proxy_sources,
        allow_auth_sources=allow_auth_sources,
    )
    return {
        "id": source.id,
        "company_id": source.company_id,
        "company_name": None,
        "market_id": source.niche_id,
        "market_name": None,
        "locator": source.locator,
        "source_type": source.source_type,
        "source_family": source.source_family,
        "enabled": source.enabled,
        "limit": source.limit,
        "scan_frequency": source.scan_frequency,
        "last_scanned_at": (
            source.last_scanned_at.isoformat() if source.last_scanned_at else None
        ),
        "last_error": source.last_error,
        "health": _serialize_niche_source_health(stats),
        "lifecycle": lifecycle["label"],
        "lifecycle_reason": lifecycle["reason"],
        "quality_status": quality.label,
        "quality_reason": quality.reason,
        "scan_eligible": scan_eligibility.eligible,
        "scan_ineligible_reason": (
            None if scan_eligibility.eligible else scan_eligibility.reason
        ),
        "management": _source_management_hint(source, quality.label, scan_eligibility),
        "is_gate_free": source.is_gate_free,
        "buyer_voice_verified": source.buyer_voice_verified,
        "tier": source.tier,
        "signal_quality_score": source.signal_quality_score,
        "access_mode": source.access_mode,
        "requires_proxy": source.requires_proxy,
        "requires_auth": source.requires_auth,
        "recommended_cadence": source.recommended_cadence,
        "replacement_suggestions": [
            _serialize_source_replacement_suggestion(suggestion)
            for suggestion in replacement_suggestions or []
        ],
        "options": source.options,
    }


def _source_management_hint(
    source: NicheSource,
    quality_label: str,
    scan_eligibility: Any,
) -> dict[str, Any]:
    if not source.enabled:
        recommended_action = "enable_or_remove"
    elif not scan_eligibility.eligible or quality_label in {"blocked", "noisy"}:
        recommended_action = "fix_or_replace"
    elif quality_label == "productive":
        recommended_action = "keep_monitoring"
    else:
        recommended_action = "monitor_next_scan"
    return {
        "can_enable": not source.enabled,
        "can_disable": source.enabled,
        "can_delete": True,
        "recommended_action": recommended_action,
    }


def _serialize_source_replacement_suggestion(
    suggestion: SourceReplacementSuggestion,
) -> dict[str, Any]:
    return {
        "candidate": _serialize_source_candidate(suggestion.candidate),
        "trigger": suggestion.trigger,
        "reason": suggestion.reason,
        "replaces_source_id": suggestion.replaces_source_id,
    }


def _serialize_source_candidate(candidate: SourceCandidate) -> dict[str, Any]:
    return {
        "locator": candidate.locator,
        "source_type": candidate.source_type,
        "label": candidate.label,
        "rationale": candidate.rationale,
        "source_family": candidate.source_family,
        "company_id": candidate.competitor_id,
        "company_name": candidate.competitor_name,
        "market_id": candidate.market_id,
        "market_name": candidate.market_name,
        "limit": candidate.limit,
        "options": candidate.options,
        "template_id": candidate.template_id,
        "already_monitored": candidate.already_monitored,
        "rank_score": candidate.rank_score,
        "validation_status": candidate.validation_status,
        "validation_error": candidate.validation_error,
    }


def _serialize_niche_source_health(
    stats: NicheSourceRunStats | None,
) -> dict[str, Any] | None:
    if stats is None:
        return None
    fetch_success_rate = (
        stats.success_count / stats.total_runs
        if stats.total_runs > 0
        else 0.0
    )
    relevance_yield_rate = (
        stats.relevant_posts_count / stats.posts_fetched_count
        if stats.posts_fetched_count > 0
        else 0.0
    )
    signal_yield_rate = (
        stats.extracted_signals_count / stats.relevant_posts_count
        if stats.relevant_posts_count > 0
        else 0.0
    )
    return {
        "total_runs": stats.total_runs,
        "success_count": stats.success_count,
        "failure_count": stats.failure_count,
        "consecutive_failures": stats.consecutive_failures,
        "posts_fetched_count": stats.posts_fetched_count,
        "relevant_posts_count": stats.relevant_posts_count,
        "extracted_signals_count": stats.extracted_signals_count,
        "opportunity_count": stats.gap_count,
        "last_status": stats.last_status,
        "last_error": stats.last_error,
        "last_fetched_count": stats.last_fetched_count,
        "last_relevant_count": stats.last_relevant_count,
        "last_extracted_count": stats.last_extracted_count,
        "last_opportunity_count": stats.last_gap_count,
        "fetch_success_rate": round(fetch_success_rate, 3),
        "relevance_yield_rate": round(relevance_yield_rate, 3),
        "signal_yield_rate": round(signal_yield_rate, 3),
        "last_scanned_at": (
            stats.last_scanned_at.isoformat() if stats.last_scanned_at else None
        ),
        "updated_at": stats.updated_at.isoformat() if stats.updated_at else None,
    }


def _source_lifecycle(source: NicheSource) -> dict[str, str]:
    if not source.enabled:
        if source.requires_proxy:
            return {
                "label": "needs_proxy",
                "reason": "Source is disabled until proxy access is configured.",
            }
        if source.requires_auth:
            return {
                "label": "needs_auth",
                "reason": "Source is disabled until authenticated access is configured.",
            }
        return {
            "label": "disabled",
            "reason": "Source is disabled and will not be scanned.",
        }
    if source.health_status == "failing" or source.last_error:
        return {
            "label": "failing",
            "reason": source.last_error or "Recent scans failed.",
        }
    if source.buyer_voice_verified:
        return {
            "label": "verified",
            "reason": "Source has produced buyer-side evidence.",
        }
    if source.last_scanned_at:
        return {
            "label": "warming_up",
            "reason": "Source is active but has not produced enough buyer evidence yet.",
        }
    return {
        "label": "candidate",
        "reason": "Source is queued for its first scan.",
    }


def _option_str(options: dict[str, Any], key: str) -> str | None:
    value = options.get(key)
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _option_int(options: dict[str, Any], key: str) -> int | None:
    value = options.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{key} must be an integer") from exc


def _option_float(options: dict[str, Any], key: str) -> float | None:
    value = options.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{key} must be a number") from exc


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
        if source.enabled:
            active_count += 1
            entry["active_count"] += 1
        if source.last_error or source.health_status == "failing":
            entry["error_count"] += 1
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
        "error_count": sum(
            1 for source in sources if source.last_error or source.health_status == "failing"
        ),
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
        "source_explanations": plan.source_explanations,
        "expected_result_window": plan.expected_result_window,
        "no_result_guidance": plan.no_result_guidance,
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


def _apply_feedback_to_agent_preferences(
    dependencies: SignalApiDependencies,
    *,
    market_id: str,
    opportunity: Opportunity,
    action: str,
) -> None:
    if action not in {"save", "dismiss", "more_like_this", "less_like_this"}:
        return
    cluster = dependencies.cluster_repository.get_cluster(opportunity.cluster_id)
    theme = cluster.theme if cluster is not None else None
    category = opportunity.unmet_need_type
    source_families = _source_families_for_opportunity(dependencies, opportunity)
    if theme is None and category is None and not source_families:
        return

    preferences = (
        dependencies.agent_preferences_repository.get_agent_preferences(market_id)
        or AgentPreferences.create(user_niche_id=market_id)
    )
    preferred_source_families = set(preferences.preferred_source_families)
    ignored_themes = set(preferences.ignored_themes)
    ignored_categories = set(preferences.ignored_categories)

    if action in {"dismiss", "less_like_this"}:
        if theme:
            ignored_themes.add(theme)
        if category:
            ignored_categories.add(category)
    else:
        preferred_source_families.update(source_families)
        if theme:
            ignored_themes.discard(theme)
        if category:
            ignored_categories.discard(category)

    updated_preferences = AgentPreferences.create(
        user_niche_id=market_id,
        preferred_source_families=sorted(preferred_source_families),
        ignored_themes=sorted(ignored_themes),
        ignored_categories=sorted(ignored_categories),
        muted_source_ids=preferences.muted_source_ids,
        extra_instructions=preferences.extra_instructions,
        created_at=preferences.created_at,
    )
    dependencies.agent_preferences_repository.save_agent_preferences(
        updated_preferences,
    )


def _source_families_for_opportunity(
    dependencies: SignalApiDependencies,
    opportunity: Opportunity,
) -> set[str]:
    signal_index = {
        signal.id: signal
        for signal in dependencies.signal_repository.list_signals()
        if signal.id in opportunity.evidence_signal_ids
    }
    return {
        family
        for signal_id in opportunity.evidence_signal_ids
        if (family := _source_family_for_signal(signal_index.get(signal_id)))
    }


def _source_family_for_signal(signal: Signal | None) -> str | None:
    if signal is None:
        return None
    source_text = _source_text_for_signal(signal)
    if not source_text:
        return None
    if any(
        token in source_text
        for token in {
            "github",
            "stackoverflow",
            "stackexchange",
            "news.ycombinator.com",
            "hn.algolia.com",
            "discourse",
            "forum",
        }
    ):
        return "technical_forum"
    if "reddit" in source_text:
        return "social"
    if any(
        token in source_text
        for token in {"g2.com", "capterra", "trustradius", "trustpilot"}
    ):
        return "reviews"
    if "producthunt" in source_text:
        return "launch"
    return None


def _source_text_for_signal(signal: Signal) -> str:
    if signal.evidence_url:
        from urllib.parse import urlparse

        parsed = urlparse(signal.evidence_url)
        if parsed.netloc:
            return parsed.netloc.lower()
    return signal.post_id.split(":", 1)[0].lower() if ":" in signal.post_id else ""


def _find_market_follow_up(
    dependencies: SignalApiDependencies,
    market_id: str,
    follow_up_id: str,
) -> AgentFollowUp | None:
    matching = [
        item
        for item in dependencies.agent_follow_up_repository.list_agent_follow_ups(
            user_niche_id=market_id,
            limit=100,
        )
        if item.id == follow_up_id
    ]
    return matching[0] if matching else None


def _serialize_agent_action(action: AgentAction) -> dict[str, Any]:
    return {
        "id": action.id,
        "market_id": action.user_niche_id,
        "action_type": action.action_type,
        "status": action.status,
        "reason": action.reason,
        "metadata": action.metadata,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "completed_at": (
            action.completed_at.isoformat() if action.completed_at else None
        ),
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


_DIAGNOSTIC_AGENT_ACTIVITY_TYPES = {
    "post_evaluating",
    "post_accepted",
    "post_filtered",
}


def _user_visible_agent_activity(activity: list[AgentActivity]) -> list[AgentActivity]:
    return [
        item
        for item in activity
        if item.event_type not in _DIAGNOSTIC_AGENT_ACTIVITY_TYPES
    ]


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
        signal_index = _signals_by_id or {
            signal.id: signal for signal in dependencies.signal_repository.list_signals()
        }
        cluster_signals = [
            signal_index[signal_id]
            for signal_id in cluster.signal_ids
            if signal_id in signal_index
        ]
        serialized["source_family_breakdown"] = _source_family_breakdown(cluster_signals)
        qualification = qualify_cluster_for_opportunity(
            cluster,
            cluster_signals,
            _opportunity_context_for_market(dependencies, market_id),
        )
        serialized["qualification_status"] = (
            "qualified" if qualification.qualified else "not_promoted"
        )
        serialized["qualification_rejection_reason"] = qualification.reason
        serialized["qualification"] = {
            "finding_count": qualification.finding_count,
            "source_count": qualification.source_count,
            "company_count": qualification.company_count,
            "general_finding_count": qualification.general_finding_count,
            "high_signal_source_count": qualification.high_signal_source_count,
            "buyer_context_signal_count": qualification.buyer_context_signal_count,
            "strong_pain_signal_count": qualification.strong_pain_signal_count,
            "average_signal_confidence": qualification.average_signal_confidence,
        }
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
        "unmet_need_type": opportunity.unmet_need_type,
    }
    if dependencies is not None:
        signal_index = _signals_by_id or {
            signal.id: signal for signal in dependencies.signal_repository.list_signals()
        }
        opportunity_signals = [
            signal_index[signal_id]
            for signal_id in opportunity.evidence_signal_ids
            if signal_id in signal_index
        ]
        serialized.update(
            _company_breadth_for_signal_ids(
                dependencies,
                opportunity.evidence_signal_ids,
                market_id=market_id,
                _signals_by_id=_signals_by_id,
            )
        )
        serialized["source_family_breakdown"] = _source_family_breakdown(opportunity_signals)
        serialized["evidence_items"] = [
            _serialize_evidence_item(signal, dependencies, market_id=market_id)
            for signal in opportunity_signals
        ]
    serialized["evidence_strength"] = _opportunity_evidence_strength(serialized)
    return serialized


def _opportunity_evidence_strength(serialized: dict[str, Any]) -> str:
    evidence_count = int(serialized.get("evidence_count") or 0)
    company_count = int(serialized.get("company_count") or 0)
    source_count = int(serialized.get("evidence_source_count") or 0)
    if evidence_count >= 5 and source_count >= 3 and company_count >= 2:
        return "strong"
    if evidence_count >= 3 and source_count >= 2 and company_count >= 1:
        return "moderate"
    return "early"


def _opportunity_context_for_market(
    dependencies: SignalApiDependencies,
    market_id: str | None,
) -> OpportunitySynthesisContext | None:
    if market_id is None:
        return None
    user_niche = dependencies.user_niche_repository.get_user_niche(market_id)
    if user_niche is None:
        return None
    preferences = dependencies.agent_preferences_repository.get_agent_preferences(market_id)
    return OpportunitySynthesisContext(
        niche_name=user_niche.job,
        target_user=user_niche.buyer,
        objective=None,
        extra_instructions=preferences.extra_instructions if preferences else None,
        ignored_themes=preferences.ignored_themes if preferences else [],
        ignored_categories=preferences.ignored_categories if preferences else [],
    )


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
