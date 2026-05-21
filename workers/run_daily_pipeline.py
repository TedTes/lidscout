"""Daily signal detection pipeline worker."""
from __future__ import annotations

from dataclasses import dataclass, field

from application.clustering import ClusteringService
from application.extraction import ExtractionService
from application.ingestion import (
    IngestionResult,
    IngestionService,
    SourceAdapter,
    SourceResolver,
)
from application.ports import (
    ClusterRepository,
    PostRepository,
    ScoreRepository,
    SignalRepository,
    SourceLocatorRepository,
)
from application.reporting import MarketSignalReport, ReportingService
from application.scoring import ScoringResult, ScoringService
from domain.post import RawPost
from domain.signal import Signal
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
    extracted_count: int
    no_signal_count: int
    extraction_failed_count: int
    signal_inserted_count: int
    scoring_result: ScoringResult
    embedding_failed_count: int
    clustered_count: int
    cluster_inserted_count: int
    report: MarketSignalReport
    email_result: EmailSendResult


def run_daily_pipeline(config: PipelineConfig) -> PipelineRunResult:
    """Run the full daily signal detection workflow."""
    posts, fetch_failed_count = _fetch_posts(config)

    ingestion_service = IngestionService(config.post_repository)
    ingestion_result = ingestion_service.ingest(posts)

    signals, no_signal_count, extraction_failed_count = _extract_signals(
        posts,
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

    report = ReportingService().generate(clusters)
    email_result = config.email_client.send_report(report, config.recipient)

    return PipelineRunResult(
        fetched_count=len(posts),
        fetch_failed_count=fetch_failed_count,
        ingestion_result=ingestion_result,
        extracted_count=len(signals),
        no_signal_count=no_signal_count,
        extraction_failed_count=extraction_failed_count,
        signal_inserted_count=signal_inserted_count,
        scoring_result=scoring_result,
        embedding_failed_count=embedding_failed_count,
        clustered_count=len(clusters),
        cluster_inserted_count=cluster_inserted_count,
        report=report,
        email_result=email_result,
    )


def _fetch_posts(config: PipelineConfig) -> tuple[list[RawPost], int]:
    posts: list[RawPost] = []
    failed_count = 0
    sources = config.sources or _configured_sources(config.source_locator_repository)

    if sources:
        source_result = SourceResolver(config.source_adapters).fetch(
            sources,
            config.default_limit,
        )
        posts.extend(source_result.posts)
        failed_count += source_result.failed_count

    return posts, failed_count


def _configured_sources(
    repository: SourceLocatorRepository | None,
) -> list[SourceInput]:
    if repository is None:
        return []
    return [
        locator.to_source_input()
        for locator in repository.list_source_locators(enabled=True)
    ]


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
