"""Runtime dependency wiring for API routes."""
from adapters.web import JsonUrlAdapter, RedditAdapter, StaticUrlAdapter
from api.routes.signals import SignalApiDependencies
from infrastructure.db import (
    PostgresAgentActivityRepository,
    PostgresAgentFeedbackRepository,
    PostgresAgentPreferencesRepository,
    PostgresFindingRepository,
    PostgresNicheCompanyRepository,
    PostgresNicheRepository,
    PostgresOpportunityRepository,
    PostgresPipelineRunMetricsRepository,
    PostgresPostRepository,
    PostgresSourceRepository,
    PostgresTemplateSourceBindingRepository,
    PostgresThemeRepository,
    PostgresUserNicheRepository,
    PostgresUserSourceRepository,
    PostgresUserSourcePreferenceRepository,
    PostgresUserSourceRunStatsRepository,
    connect_postgres,
)
from infrastructure.email import EmailClient, ResendEmailNotifier
from infrastructure.llm import OpenAIEmbeddingClient, OpenAIResponsesClient
from shared.config import AppConfig, get_app_config


def build_signal_api_dependencies(
    config: AppConfig | None = None,
    connection: object | None = None,
) -> SignalApiDependencies:
    """Build signal API dependencies from runtime configuration."""
    app_config = config or get_app_config()
    database_url = app_config.DATABASE_URL.strip()
    if not _is_postgres_url(database_url):
        raise ValueError("DATABASE_URL must be a Supabase/Postgres URL")

    connection = connection or connect_postgres(database_url)
    return SignalApiDependencies(
        post_repository=PostgresPostRepository(connection=connection),
        opportunity_repository=PostgresOpportunityRepository(connection=connection),
        finding_repository=PostgresFindingRepository(connection=connection),
        theme_repository=PostgresThemeRepository(connection=connection),
        pipeline_run_metrics_repository=PostgresPipelineRunMetricsRepository(
            connection=connection,
        ),
        agent_preferences_repository=PostgresAgentPreferencesRepository(
            connection=connection,
        ),
        agent_feedback_repository=PostgresAgentFeedbackRepository(
            connection=connection,
        ),
        agent_activity_repository=PostgresAgentActivityRepository(
            connection=connection,
        ),
        niche_repository=PostgresNicheRepository(connection=connection),
        niche_company_repository=PostgresNicheCompanyRepository(connection=connection),
        source_repository=PostgresSourceRepository(connection=connection),
        template_source_binding_repository=PostgresTemplateSourceBindingRepository(
            connection=connection,
        ),
        user_source_preference_repository=PostgresUserSourcePreferenceRepository(
            connection=connection,
        ),
        user_source_repository=PostgresUserSourceRepository(connection=connection),
        user_source_run_stats_repository=PostgresUserSourceRunStatsRepository(
            connection=connection,
        ),
        user_niche_repository=PostgresUserNicheRepository(connection=connection),
        source_adapters=[
            *(_reddit_adapter(app_config) or []),
            JsonUrlAdapter(),
            StaticUrlAdapter(),
        ],
        llm_client=_build_llm_client(app_config),
        relevance_llm_client=_build_relevance_llm_client(app_config),
        embedding_client=_build_embedding_client(app_config),
        email_client=_build_email_client(app_config),
    )


def _reddit_adapter(config: AppConfig) -> list[RedditAdapter]:
    if config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET:
        return [RedditAdapter(config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET)]
    return []


def _is_postgres_url(database_url: str) -> bool:
    return database_url.startswith(("postgresql://", "postgres://"))


def _build_llm_client(config: AppConfig) -> OpenAIResponsesClient | None:
    if config.LLM_API_KEY is None:
        return None
    return OpenAIResponsesClient(
        api_key=config.LLM_API_KEY,
        model=config.OPENAI_RESPONSE_MODEL,
    )


def _build_relevance_llm_client(config: AppConfig) -> OpenAIResponsesClient | None:
    if config.LLM_API_KEY is None:
        return None
    return OpenAIResponsesClient(
        api_key=config.LLM_API_KEY,
        model=config.OPENAI_RELEVANCE_MODEL,
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
