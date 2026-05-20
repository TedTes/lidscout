"""Runtime dependency wiring for API routes."""
from adapters.web import JsonUrlAdapter, StaticUrlAdapter
from api.routes.signals import SignalApiDependencies
from infrastructure.db import (
    PostgresClusterRepository,
    PostgresPostRepository,
    PostgresScoreRepository,
    PostgresSignalRepository,
)
from infrastructure.email import EmailClient, ResendEmailNotifier
from infrastructure.llm import OpenAIEmbeddingClient, OpenAIResponsesClient
from shared.config import AppConfig, get_app_config


def build_signal_api_dependencies(
    config: AppConfig | None = None,
) -> SignalApiDependencies:
    """Build signal API dependencies from runtime configuration."""
    app_config = config or get_app_config()
    database_url = app_config.DATABASE_URL.strip()
    if not _is_postgres_url(database_url):
        raise ValueError("DATABASE_URL must be a Supabase/Postgres URL")

    return SignalApiDependencies(
        post_repository=PostgresPostRepository(database_url),
        signal_repository=PostgresSignalRepository(database_url),
        score_repository=PostgresScoreRepository(database_url),
        cluster_repository=PostgresClusterRepository(database_url),
        source_adapters=[
            JsonUrlAdapter(),
            StaticUrlAdapter(),
        ],
        llm_client=_build_llm_client(app_config),
        embedding_client=_build_embedding_client(app_config),
        email_client=_build_email_client(app_config),
    )


def _is_postgres_url(database_url: str) -> bool:
    return database_url.startswith(("postgresql://", "postgres://"))


def _build_llm_client(config: AppConfig) -> OpenAIResponsesClient | None:
    if config.LLM_API_KEY is None:
        return None
    return OpenAIResponsesClient(
        api_key=config.LLM_API_KEY,
        model=config.OPENAI_RESPONSE_MODEL,
    )


def _build_embedding_client(config: AppConfig) -> OpenAIEmbeddingClient | None:
    if config.LLM_API_KEY is None:
        return None
    return OpenAIEmbeddingClient(
        api_key=config.LLM_API_KEY,
        model=config.OPENAI_EMBEDDING_MODEL,
    )


def _build_email_client(config: AppConfig) -> EmailClient | None:
    if config.RESEND_API_KEY is None or config.RESEND_FROM_EMAIL is None:
        return None
    return EmailClient(
        ResendEmailNotifier(
            api_key=config.RESEND_API_KEY,
            from_email=config.RESEND_FROM_EMAIL,
        )
    )
