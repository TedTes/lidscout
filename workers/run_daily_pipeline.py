"""Daily signal detection pipeline worker."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlparse

from application.clustering import ClusteringService
from application.agent import generate_threshold_alerts
from application.extraction import ExtractionService
from application.extraction import LLMRelevanceFilter, RuleBasedRelevanceFilter
from application.ingestion import (
    IngestionResult,
    IngestionService,
    SourceAdapter,
    SourceFetchDetail,
    SourceResolver,
)
from application.opportunity import (
    OpportunitySynthesisContext,
    OpportunitySynthesisResult,
    OpportunitySynthesisService,
)
from application.ports import (
    AgentActivityRepository,
    AgentAlertRepository,
    AgentPreferencesRepository,
    ClusterRepository,
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
from application.scoring import ScoringResult, ScoringService
from domain.cluster import SignalCluster
from domain.agent import AgentActivity
from domain.opportunity import Opportunity
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.signal import Signal
from domain.niche import NicheSource, UserNiche
from domain.source import SourceInput
from infrastructure.email import EmailClient, EmailSendResult
from infrastructure.llm import EmbeddingClient, LLMClient


@dataclass(frozen=True)
class PipelineConfig:
    """Dependencies and source settings for a daily pipeline run."""

    post_repository: PostRepository
    signal_repository: SignalRepository
    score_repository: ScoreRepository
    cluster_repository: ClusterRepository
    llm_client: LLMClient
    embedding_client: EmbeddingClient
    email_client: EmailClient
    recipient: str
    relevance_llm_client: LLMClient | None = None
    opportunity_repository: OpportunityRepository | None = None
    pipeline_run_metrics_repository: PipelineRunMetricsRepository | None = None
    agent_preferences_repository: AgentPreferencesRepository | None = None
    agent_activity_repository: AgentActivityRepository | None = None
    agent_alert_repository: AgentAlertRepository | None = None
    niche_source_repository: NicheSourceRepository | None = None
    user_niche_repository: UserNicheRepository | None = None
    source_locator_repository: SourceLocatorRepository | None = None
    source_adapters: list[SourceAdapter] = field(default_factory=list)
    sources: list[SourceInput] = field(default_factory=list)
    user_niche_id: str | None = None
    default_limit: int = 25
    similarity_threshold: float = 0.82


@dataclass(frozen=True)
class PipelineRunResult:
    """Summary of one daily pipeline run."""

    fetched_count: int
    fetch_failed_count: int
    ingestion_result: IngestionResult
    rule_filtered_count: int
    llm_filtered_count: int
    relevance_failed_count: int
    extraction_attempted_count: int
    extracted_count: int
    no_signal_count: int
    extraction_failed_count: int
    signal_inserted_count: int
    scoring_result: ScoringResult
    embedding_failed_count: int
    clustered_count: int
    cluster_inserted_count: int
    opportunity_synthesis_result: OpportunitySynthesisResult
    report: MarketSignalReport
    email_result: EmailSendResult


@dataclass(frozen=True)
class PipelineFetchResult:
    """Posts and per-source fetch outcomes from one pipeline fetch stage."""

    posts: list[RawPost]
    failed_count: int
    details: list[SourceFetchDetail]


def run_daily_pipeline(config: PipelineConfig) -> PipelineRunResult:
    """Run the full daily signal detection workflow."""
    _record_agent_activity(
        config.agent_activity_repository,
        user_niche_id=config.user_niche_id,
        event_type="run_started",
        title="Agent scan started",
        detail="The research agent started a scheduled scan.",
    )
    fetch_result = _fetch_posts(config)
    posts = fetch_result.posts

    ingestion_service = IngestionService(config.post_repository)
    ingestion_result = ingestion_service.ingest(posts)

    relevance_result = _filter_relevant_posts(
        posts,
        config.relevance_llm_client,
    )
    signals, no_signal_count, extraction_failed_count = _extract_signals(
        relevance_result.posts,
        config.llm_client,
    )
    signal_inserted_count = config.signal_repository.save_signals(signals)

    scoring_result = ScoringService(config.score_repository).score(signals)

    clustered_signals, embeddings, embedding_failed_count = _embed_signals(
        signals,
        config.embedding_client,
    )
    clusters = ClusteringService(config.similarity_threshold).cluster(
        clustered_signals,
        embeddings,
    )
    cluster_inserted_count = config.cluster_repository.save_clusters(clusters)

    opportunity_synthesis_result = _synthesize_opportunities(
        config.opportunity_repository,
        config.llm_client,
        clusters,
        signals,
        _synthesis_context(config),
    )
    _record_niche_source_health(
        config.niche_source_repository,
        fetch_result.details,
    )

    report = ReportingService().generate(
        clusters,
        opportunity_synthesis_result.opportunities,
        title=_market_report_title(config),
    )
    email_result = config.email_client.send_report(report, config.recipient)

    result = PipelineRunResult(
        fetched_count=len(posts),
        fetch_failed_count=fetch_result.failed_count,
        ingestion_result=ingestion_result,
        rule_filtered_count=relevance_result.rule_filtered_count,
        llm_filtered_count=relevance_result.llm_filtered_count,
        relevance_failed_count=relevance_result.failed_count,
        extraction_attempted_count=len(relevance_result.posts),
        extracted_count=len(signals),
        no_signal_count=no_signal_count,
        extraction_failed_count=extraction_failed_count,
        signal_inserted_count=signal_inserted_count,
        scoring_result=scoring_result,
        embedding_failed_count=embedding_failed_count,
        clustered_count=len(clusters),
        cluster_inserted_count=cluster_inserted_count,
        opportunity_synthesis_result=opportunity_synthesis_result,
        report=report,
        email_result=email_result,
    )
    _save_pipeline_run_metrics(config.pipeline_run_metrics_repository, result)
    _record_threshold_alerts(config, clusters, opportunity_synthesis_result.opportunities)
    _record_pipeline_activity(config, result)
    return result


@dataclass(frozen=True)
class RelevanceFilterResult:
    """Posts that passed relevance gates plus filter counts."""

    posts: list[RawPost]
    rule_filtered_count: int
    llm_filtered_count: int
    failed_count: int


def _synthesize_opportunities(
    opportunity_repository: OpportunityRepository | None,
    llm_client: LLMClient,
    clusters: list[SignalCluster],
    signals: list[Signal],
    context: OpportunitySynthesisContext | None = None,
) -> OpportunitySynthesisResult:
    if opportunity_repository is None:
        return OpportunitySynthesisResult(
            synthesized_count=0,
            inserted_count=0,
            failed_count=0,
            opportunities=[],
        )
    return OpportunitySynthesisService(
        opportunity_repository,
        llm_client=llm_client,
    ).synthesize(clusters, signals, context=context)


def _synthesis_context(
    config: PipelineConfig,
) -> OpportunitySynthesisContext | None:
    if config.user_niche_id is None or config.user_niche_repository is None:
        return None
    user_niche = config.user_niche_repository.get_user_niche(config.user_niche_id)
    if user_niche is None:
        return None
    preferences = (
        config.agent_preferences_repository.get_agent_preferences(config.user_niche_id)
        if config.agent_preferences_repository is not None
        else None
    )
    return OpportunitySynthesisContext(
        niche_name=user_niche.job,
        target_user=user_niche.buyer,
        objective=None,
        extra_instructions=preferences.extra_instructions if preferences else None,
        ignored_themes=preferences.ignored_themes if preferences else [],
        ignored_categories=preferences.ignored_categories if preferences else [],
    )


def _save_pipeline_run_metrics(
    metrics_repository: PipelineRunMetricsRepository | None,
    result: PipelineRunResult,
) -> None:
    if metrics_repository is None:
        return
    metrics_repository.save_pipeline_run_metrics(
        PipelineRunMetrics.create(
            fetched_count=result.fetched_count,
            fetch_failed_count=result.fetch_failed_count,
            rule_filtered_count=result.rule_filtered_count,
            llm_filtered_count=result.llm_filtered_count,
            relevance_failed_count=result.relevance_failed_count,
            extraction_attempted_count=result.extraction_attempted_count,
            extracted_count=result.extracted_count,
            no_signal_count=result.no_signal_count,
            extraction_failed_count=result.extraction_failed_count,
            signal_inserted_count=result.signal_inserted_count,
            scored_count=result.scoring_result.scored_count,
            scoring_failed_count=result.scoring_result.failed_count,
            average_score=result.scoring_result.average_score,
            embedding_failed_count=result.embedding_failed_count,
            clustered_count=result.clustered_count,
            cluster_inserted_count=result.cluster_inserted_count,
            opportunity_synthesized_count=(
                result.opportunity_synthesis_result.synthesized_count
            ),
            opportunity_inserted_count=(
                result.opportunity_synthesis_result.inserted_count
            ),
            opportunity_failed_count=(
                result.opportunity_synthesis_result.failed_count
            ),
            email_sent=result.email_result.sent,
            email_error=result.email_result.error,
        )
    )


def _record_agent_activity(
    activity_repository: AgentActivityRepository | None,
    *,
    user_niche_id: str | None,
    event_type: str,
    title: str,
    detail: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    if activity_repository is None or user_niche_id is None:
        return
    activity_repository.save_agent_activity(
        AgentActivity.create(
            user_niche_id=user_niche_id,
            event_type=event_type,
            title=title,
            detail=detail,
            metadata=metadata,
        )
    )


def _record_pipeline_activity(
    config: PipelineConfig,
    result: PipelineRunResult,
) -> None:
    _record_agent_activity(
        config.agent_activity_repository,
        user_niche_id=config.user_niche_id,
        event_type="run_completed",
        title="Agent scan completed",
        detail=(
            f"Fetched {result.fetched_count} post(s), extracted "
            f"{result.extracted_count} finding(s), and synthesized "
            f"{result.opportunity_synthesis_result.synthesized_count} gap(s)."
        ),
        metadata={
            "fetched_count": result.fetched_count,
            "fetch_failed_count": result.fetch_failed_count,
            "rule_filtered_count": result.rule_filtered_count,
            "llm_filtered_count": result.llm_filtered_count,
            "extracted_count": result.extracted_count,
            "clustered_count": result.clustered_count,
            "opportunity_synthesized_count": (
                result.opportunity_synthesis_result.synthesized_count
            ),
            "email_sent": result.email_result.sent,
            "email_error": result.email_result.error,
        },
    )


def _record_threshold_alerts(
    config: PipelineConfig,
    clusters: list[SignalCluster],
    opportunities: list[Opportunity],
) -> None:
    if config.agent_alert_repository is None or config.user_niche_id is None:
        return
    alerts = generate_threshold_alerts(
        user_niche_id=config.user_niche_id,
        clusters=clusters,
        opportunities=opportunities,
    )
    for alert in alerts:
        inserted = config.agent_alert_repository.save_agent_alert(alert)
        if not inserted:
            continue
        _record_agent_activity(
            config.agent_activity_repository,
            user_niche_id=config.user_niche_id,
            event_type="alert_created",
            title="Threshold alert created",
            detail=alert.title,
            metadata={
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
            },
        )


def _fetch_posts(config: PipelineConfig) -> PipelineFetchResult:
    posts: list[RawPost] = []
    failed_count = 0
    details: list[SourceFetchDetail] = []
    sources = config.sources or _configured_sources(
        config.niche_source_repository,
        config.source_locator_repository,
        config.user_niche_repository,
        config.agent_preferences_repository,
        config.user_niche_id,
    )

    if sources:
        source_result = SourceResolver(config.source_adapters).fetch(
            sources,
            config.default_limit,
        )
        posts.extend(source_result.posts)
        failed_count += source_result.failed_count
        details.extend(source_result.details)
        for detail in source_result.details:
            if detail.error is None:
                continue
            _record_agent_activity(
                config.agent_activity_repository,
                user_niche_id=config.user_niche_id,
                event_type="source_failed",
                title="Source fetch failed",
                detail=detail.error,
                metadata={
                    "locator": detail.source.locator,
                    "source_type": detail.source.options.get("source_type"),
                    "niche_source_id": detail.source.options.get("niche_source_id"),
                    "fetched_count": detail.fetched_count,
                },
            )

    return PipelineFetchResult(
        posts=posts,
        failed_count=failed_count,
        details=details,
    )


def _record_niche_source_health(
    niche_source_repository: NicheSourceRepository | None,
    details: list[SourceFetchDetail],
) -> None:
    if niche_source_repository is None:
        return
    scanned_at = datetime.now(tz=UTC)
    for detail in details:
        source_id = detail.source.options.get("niche_source_id")
        if not isinstance(source_id, str):
            continue
        health_status = "failing" if detail.error else "active"
        niche_source_repository.update_niche_source_health(
            source_id,
            health_status,
            scanned_at,
        )


def _filter_relevant_posts(
    posts: list[RawPost],
    relevance_llm_client: LLMClient | None,
) -> RelevanceFilterResult:
    rule_filter = RuleBasedRelevanceFilter()
    llm_filter = (
        LLMRelevanceFilter(relevance_llm_client)
        if relevance_llm_client is not None
        else None
    )
    relevant_posts: list[RawPost] = []
    rule_filtered_count = 0
    llm_filtered_count = 0
    failed_count = 0

    for post in posts:
        rule_result = rule_filter.evaluate(post)
        if not rule_result.is_relevant:
            rule_filtered_count += 1
            continue

        if llm_filter is None:
            relevant_posts.append(post)
            continue

        try:
            llm_result = llm_filter.evaluate(post)
        except Exception:
            failed_count += 1
            continue

        if not llm_result.is_relevant:
            llm_filtered_count += 1
            continue

        relevant_posts.append(post)

    return RelevanceFilterResult(
        posts=relevant_posts,
        rule_filtered_count=rule_filtered_count,
        llm_filtered_count=llm_filtered_count,
        failed_count=failed_count,
    )


def _configured_sources(
    niche_source_repository: NicheSourceRepository | None,
    source_locator_repository: SourceLocatorRepository | None,
    user_niche_repository: UserNicheRepository | None,
    agent_preferences_repository: AgentPreferencesRepository | None,
    user_niche_id: str | None,
) -> list[SourceInput]:
    if niche_source_repository is not None and user_niche_id is not None:
        niche_id = None
        if user_niche_repository is not None:
            user_niche = user_niche_repository.get_user_niche(user_niche_id)
            if user_niche is not None:
                niche_id = user_niche.template_niche_id
        if niche_id is not None:
            niche_sources = niche_source_repository.list_niche_sources(niche_id)
            if niche_sources:
                filtered = _apply_agent_source_preferences(
                    niche_sources,
                    agent_preferences_repository,
                    user_niche_id,
                )
                user_niche_obj = (
                    user_niche_repository.get_user_niche(user_niche_id)
                    if user_niche_repository is not None
                    else None
                )
                preferences = (
                    agent_preferences_repository.get_agent_preferences(user_niche_id)
                    if agent_preferences_repository is not None
                    else None
                )
                return [
                    _niche_source_input(s, user_niche_obj, preferences)
                    for s in filtered
                ]
    if source_locator_repository is None:
        return []
    return [
        locator.to_source_input()
        for locator in source_locator_repository.list_source_locators(enabled=True)
    ]


def _niche_source_input(
    source: NicheSource,
    user_niche: UserNiche | None,
    preferences: object | None,
) -> SourceInput:
    options: dict = {
        "niche_source_id": source.id,
        "source_type": source.source_type,
        "source_family": source.source_family,
        "niche_id": source.niche_id,
    }
    if source.company_id:
        options["niche_company_id"] = source.company_id
    if user_niche is not None:
        options["niche_name"] = user_niche.job
        options["target_user"] = user_niche.buyer
    if preferences is not None:
        if getattr(preferences, "extra_instructions", None):
            options["agent_extra_instructions"] = preferences.extra_instructions  # type: ignore[union-attr]
        if getattr(preferences, "ignored_themes", None):
            options["agent_ignored_themes"] = ", ".join(preferences.ignored_themes)  # type: ignore[union-attr]
        if getattr(preferences, "ignored_categories", None):
            options["agent_ignored_categories"] = ", ".join(preferences.ignored_categories)  # type: ignore[union-attr]
    return SourceInput.create(locator=source.locator, options=options)


def _apply_agent_source_preferences(
    sources: list[NicheSource],
    agent_preferences_repository: AgentPreferencesRepository | None,
    user_niche_id: str | None,
) -> list[NicheSource]:
    if agent_preferences_repository is None or user_niche_id is None:
        return sources

    preferences = agent_preferences_repository.get_agent_preferences(user_niche_id)
    if preferences is None:
        return sources

    muted_source_ids = set(preferences.muted_source_ids)
    filtered_sources = [
        source for source in sources if source.id not in muted_source_ids
    ]
    if not preferences.preferred_source_families:
        return filtered_sources

    priority = {
        family: index
        for index, family in enumerate(preferences.preferred_source_families)
    }
    return sorted(
        filtered_sources,
        key=lambda source: priority.get(
            source.source_family.strip(),
            len(priority),
        ),
    )


def _domain_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc:
        return parsed.netloc.lower()
    return None


def _market_report_title(config: PipelineConfig) -> str | None:
    if config.user_niche_id is None or config.user_niche_repository is None:
        return None
    user_niche = config.user_niche_repository.get_user_niche(config.user_niche_id)
    if user_niche is None:
        return None
    return f"{user_niche.job} Market Gap Report"


def _extract_signals(
    posts: list[RawPost],
    llm_client: LLMClient,
) -> tuple[list[Signal], int, int]:
    extraction_service = ExtractionService(llm_client)
    signals: list[Signal] = []
    no_signal_count = 0
    failed_count = 0

    for post in posts:
        try:
            result = extraction_service.extract(post)
        except Exception:
            failed_count += 1
            continue

        if result.signal:
            signals.append(result.signal)
        else:
            no_signal_count += 1

    return signals, no_signal_count, failed_count


def _embed_signals(
    signals: list[Signal],
    embedding_client: EmbeddingClient,
) -> tuple[list[Signal], dict[str, list[float]], int]:
    clustered_signals: list[Signal] = []
    embeddings: dict[str, list[float]] = {}
    failed_count = 0

    for signal in signals:
        try:
            embeddings[signal.id] = embedding_client.generate_embedding(_signal_text(signal))
        except Exception:
            failed_count += 1
            continue
        clustered_signals.append(signal)

    return clustered_signals, embeddings, failed_count


def _signal_text(signal: Signal) -> str:
    parts = [
        signal.pain,
        signal.user_type,
        signal.job_to_be_done,
        signal.current_workaround,
        signal.category,
    ]
    return "\n".join(part for part in parts if part)
