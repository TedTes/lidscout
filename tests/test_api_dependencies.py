import unittest
from contextlib import ExitStack
from unittest.mock import patch

from api.dependencies import build_signal_api_dependencies
from shared.config import AppConfig


class ApiDependencyTests(unittest.TestCase):
    def test_builds_runtime_dependencies_from_postgres_config(self):
        database_url = "postgresql://postgres.example/lidscout"
        config = AppConfig(
            DATABASE_URL=database_url,
            LLM_API_KEY="llm-key",
            OPENAI_RESPONSE_MODEL="response-model",
            OPENAI_RELEVANCE_MODEL="relevance-model",
            OPENAI_EMBEDDING_MODEL="embedding-model",
            EMAIL_API_KEY=None,
            RESEND_API_KEY="resend-key",
            RESEND_FROM_EMAIL="LidScout <alerts@example.com>",
            REPORT_RECIPIENT="founder@example.com",
            PIPELINE_SCHEDULE="0 8 * * *",
        )

        with ExitStack() as stack:
            post_repository = stack.enter_context(
                patch("api.dependencies.PostgresPostRepository")
            )
            signal_repository = stack.enter_context(
                patch("api.dependencies.PostgresSignalRepository")
            )
            score_repository = stack.enter_context(
                patch("api.dependencies.PostgresScoreRepository")
            )
            cluster_repository = stack.enter_context(
                patch("api.dependencies.PostgresClusterRepository")
            )
            opportunity_repository = stack.enter_context(
                patch("api.dependencies.PostgresOpportunityRepository")
            )
            metrics_repository = stack.enter_context(
                patch("api.dependencies.PostgresPipelineRunMetricsRepository")
            )
            agent_preferences_repository = stack.enter_context(
                patch("api.dependencies.PostgresAgentPreferencesRepository")
            )
            agent_feedback_repository = stack.enter_context(
                patch("api.dependencies.PostgresAgentFeedbackRepository")
            )
            agent_activity_repository = stack.enter_context(
                patch("api.dependencies.PostgresAgentActivityRepository")
            )
            competitor_repository = stack.enter_context(
                patch("api.dependencies.PostgresCompetitorRepository")
            )
            market_repository = stack.enter_context(
                patch("api.dependencies.PostgresMarketRepository")
            )
            monitored_source_repository = stack.enter_context(
                patch("api.dependencies.PostgresMonitoredSourceRepository")
            )
            source_health_repository = stack.enter_context(
                patch("api.dependencies.PostgresSourceHealthRepository")
            )
            source_locator_repository = stack.enter_context(
                patch("api.dependencies.PostgresSourceLocatorRepository")
            )
            json_adapter = stack.enter_context(
                patch("api.dependencies.JsonUrlAdapter")
            )
            static_adapter = stack.enter_context(
                patch("api.dependencies.StaticUrlAdapter")
            )
            llm_client = stack.enter_context(
                patch("api.dependencies.OpenAIResponsesClient")
            )
            embedding_client = stack.enter_context(
                patch("api.dependencies.OpenAIEmbeddingClient")
            )
            email_notifier = stack.enter_context(
                patch("api.dependencies.ResendEmailNotifier")
            )
            email_client = stack.enter_context(patch("api.dependencies.EmailClient"))
            connect_postgres = stack.enter_context(
                patch("api.dependencies.connect_postgres")
            )
            dependencies = build_signal_api_dependencies(config)

        connect_postgres.assert_called_once_with(database_url)
        connection = connect_postgres.return_value
        post_repository.assert_called_once_with(connection=connection)
        signal_repository.assert_called_once_with(connection=connection)
        score_repository.assert_called_once_with(connection=connection)
        cluster_repository.assert_called_once_with(connection=connection)
        opportunity_repository.assert_called_once_with(connection=connection)
        metrics_repository.assert_called_once_with(connection=connection)
        agent_preferences_repository.assert_called_once_with(connection=connection)
        agent_feedback_repository.assert_called_once_with(connection=connection)
        agent_activity_repository.assert_called_once_with(connection=connection)
        competitor_repository.assert_called_once_with(connection=connection)
        market_repository.assert_called_once_with(connection=connection)
        monitored_source_repository.assert_called_once_with(connection=connection)
        source_health_repository.assert_called_once_with(connection=connection)
        source_locator_repository.assert_called_once_with(connection=connection)
        self.assertEqual(llm_client.call_count, 2)
        llm_client.assert_any_call(api_key="llm-key", model="response-model")
        llm_client.assert_any_call(api_key="llm-key", model="relevance-model")
        embedding_client.assert_called_once_with(
            api_key="llm-key",
            model="embedding-model",
        )
        email_notifier.assert_called_once_with(
            api_key="resend-key",
            from_email="LidScout <alerts@example.com>",
        )
        email_client.assert_called_once_with(email_notifier.return_value)

        self.assertEqual(
            dependencies.source_adapters,
            [
                json_adapter.return_value,
                static_adapter.return_value,
            ],
        )
        self.assertIs(dependencies.post_repository, post_repository.return_value)
        self.assertIs(dependencies.signal_repository, signal_repository.return_value)
        self.assertIs(dependencies.score_repository, score_repository.return_value)
        self.assertIs(dependencies.cluster_repository, cluster_repository.return_value)
        self.assertIs(
            dependencies.opportunity_repository,
            opportunity_repository.return_value,
        )
        self.assertIs(
            dependencies.pipeline_run_metrics_repository,
            metrics_repository.return_value,
        )
        self.assertIs(
            dependencies.agent_preferences_repository,
            agent_preferences_repository.return_value,
        )
        self.assertIs(
            dependencies.agent_feedback_repository,
            agent_feedback_repository.return_value,
        )
        self.assertIs(
            dependencies.agent_activity_repository,
            agent_activity_repository.return_value,
        )
        self.assertIs(dependencies.competitor_repository, competitor_repository.return_value)
        self.assertIs(dependencies.market_repository, market_repository.return_value)
        self.assertIs(
            dependencies.monitored_source_repository,
            monitored_source_repository.return_value,
        )
        self.assertIs(
            dependencies.source_health_repository,
            source_health_repository.return_value,
        )
        self.assertIs(
            dependencies.source_locator_repository,
            source_locator_repository.return_value,
        )
        self.assertIs(dependencies.llm_client, llm_client.return_value)
        self.assertIs(dependencies.relevance_llm_client, llm_client.return_value)
        self.assertIs(dependencies.embedding_client, embedding_client.return_value)
        self.assertIs(dependencies.email_client, email_client.return_value)

    def test_leaves_llm_client_empty_without_key(self):
        database_url = "postgresql://postgres.example/lidscout"
        config = AppConfig(
            DATABASE_URL=database_url,
            LLM_API_KEY=None,
            OPENAI_RESPONSE_MODEL="response-model",
            OPENAI_RELEVANCE_MODEL="relevance-model",
            OPENAI_EMBEDDING_MODEL="embedding-model",
            EMAIL_API_KEY=None,
            RESEND_API_KEY=None,
            RESEND_FROM_EMAIL=None,
            REPORT_RECIPIENT=None,
            PIPELINE_SCHEDULE="0 8 * * *",
        )

        with ExitStack() as stack:
            for target in [
                "api.dependencies.PostgresPostRepository",
                "api.dependencies.PostgresSignalRepository",
                "api.dependencies.PostgresScoreRepository",
                "api.dependencies.PostgresClusterRepository",
                "api.dependencies.PostgresOpportunityRepository",
                "api.dependencies.PostgresPipelineRunMetricsRepository",
                "api.dependencies.PostgresAgentPreferencesRepository",
                "api.dependencies.PostgresAgentFeedbackRepository",
                "api.dependencies.PostgresAgentActivityRepository",
                "api.dependencies.PostgresCompetitorRepository",
                "api.dependencies.PostgresMarketRepository",
                "api.dependencies.PostgresMonitoredSourceRepository",
                "api.dependencies.PostgresSourceHealthRepository",
                "api.dependencies.PostgresSourceLocatorRepository",
                "api.dependencies.JsonUrlAdapter",
                "api.dependencies.StaticUrlAdapter",
                "api.dependencies.connect_postgres",
            ]:
                stack.enter_context(patch(target))
            llm_client = stack.enter_context(
                patch("api.dependencies.OpenAIResponsesClient")
            )
            embedding_client = stack.enter_context(
                patch("api.dependencies.OpenAIEmbeddingClient")
            )
            email_notifier = stack.enter_context(
                patch("api.dependencies.ResendEmailNotifier")
            )
            email_client = stack.enter_context(patch("api.dependencies.EmailClient"))
            dependencies = build_signal_api_dependencies(config)

        llm_client.assert_not_called()
        embedding_client.assert_not_called()
        email_notifier.assert_not_called()
        email_client.assert_not_called()
        self.assertIsNone(dependencies.llm_client)
        self.assertIsNone(dependencies.relevance_llm_client)
        self.assertIsNone(dependencies.embedding_client)
        self.assertIsNone(dependencies.email_client)

    def test_rejects_non_postgres_database_url(self):
        config = AppConfig(
            DATABASE_URL="sqlite:///lidscout.db",
            LLM_API_KEY=None,
            OPENAI_RESPONSE_MODEL="response-model",
            OPENAI_RELEVANCE_MODEL="relevance-model",
            OPENAI_EMBEDDING_MODEL="embedding-model",
            EMAIL_API_KEY=None,
            RESEND_API_KEY=None,
            RESEND_FROM_EMAIL=None,
            REPORT_RECIPIENT=None,
            PIPELINE_SCHEDULE="0 8 * * *",
        )

        with self.assertRaises(ValueError):
            build_signal_api_dependencies(config)


if __name__ == "__main__":
    unittest.main()
