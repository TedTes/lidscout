"""Daily signal detection pipeline worker."""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse

from application.clustering import ClusteringService
from application.extraction import ExtractionService
from application.extraction import LLMRelevanceFilter, RuleBasedRelevanceFilter
from application.ingestion import (
    IngestionResult,
    IngestionService,
    SourceAdapter,
    SourceResolver,
)
from application.opportunity import (
    OpportunitySynthesisResult,
    OpportunitySynthesisService,
)
from application.ports import (
    ClusterRepository,
    CompetitorRepository,
    MonitoredSourceRepository,
    OpportunityRepository,
    PipelineRunMetricsRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceLocatorRepository,
)
from application.reporting import MarketSignalReport, ReportingService
from application.scoring import ScoringResult, ScoringService
from domain.cluster import SignalCluster
from domain.pipeline import PipelineRunMetrics
from domain.post import RawPost
from domain.signal import Signal
from domain.source import MonitoredSource, SourceInput
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
    competitor_repository: CompetitorRepository | None = None
    monitored_source_repository: MonitoredSourceRepository | None = None
    source_locator_repository: SourceLocatorRepository | None = None
    source_adapters: list[SourceAdapter] = field(default_factory=list)
    sources: list[SourceInput] = field(default_factory=list)
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


def run_daily_pipeline(config: PipelineConfig) -> PipelineRunResult:
    """Run the full daily signal detection workflow."""
    posts, fetch_failed_count = _fetch_posts(config)

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
        clusters,
        signals,
    )

    report = ReportingService().generate(
        clusters,
        opportunity_synthesis_result.opportunities,
    )
    email_result = config.email_client.send_report(report, config.recipient)

    result = PipelineRunResult(
        fetched_count=len(posts),
        fetch_failed_count=fetch_failed_count,
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
    clusters: list[SignalCluster],
    signals: list[Signal],
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
        llm_client=config.llm_client,
    ).synthesize(clusters, signals)


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


def _fetch_posts(config: PipelineConfig) -> tuple[list[RawPost], int]:
    posts: list[RawPost] = []
    failed_count = 0
    sources = config.sources or _configured_sources(
        config.monitored_source_repository,
        config.source_locator_repository,
        config.competitor_repository,
    )

    if sources:
        source_result = SourceResolver(config.source_adapters).fetch(
            sources,
            config.default_limit,
        )
        posts.extend(source_result.posts)
        failed_count += source_result.failed_count

    return posts, failed_count


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
    monitored_source_repository: MonitoredSourceRepository | None,
    source_locator_repository: SourceLocatorRepository | None,
    competitor_repository: CompetitorRepository | None,
) -> list[SourceInput]:
    if monitored_source_repository is not None:
        monitored_sources = [
            _monitored_source_input(source, competitor_repository)
            for source in monitored_source_repository.list_monitored_sources(enabled=True)
        ]
        if monitored_sources:
            return monitored_sources
    if source_locator_repository is None:
        return []
    return [
        locator.to_source_input()
        for locator in source_locator_repository.list_source_locators(enabled=True)
    ]


def _monitored_source_input(
    source: MonitoredSource,
    competitor_repository: CompetitorRepository | None,
) -> SourceInput:
    source_input = source.to_source_input()
    options = dict(source_input.options)

    competitor = None
    if competitor_repository is not None:
        competitor = competitor_repository.get_competitor(source.competitor_id)

    if competitor is not None:
        options["competitor_name"] = competitor.name
        if competitor.website:
            options["competitor_website"] = competitor.website
            domain = _domain_from_url(competitor.website)
            if domain:
                options["competitor_domain"] = domain
        if competitor.category:
            options["competitor_category"] = competitor.category

    return SourceInput.create(
        locator=source_input.locator,
        limit=source_input.limit,
        options=options,
    )


def _domain_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc:
        return parsed.netloc.lower()
    return None


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
