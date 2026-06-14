import unittest
from contextlib import ExitStack
from unittest.mock import patch

from api.dependencies import build_signal_api_dependencies
from shared.config import AppConfig


def _app_config(**overrides):
    values = {
        "DATABASE_URL": "postgresql://postgres.example/lidscout",
        "LLM_API_KEY": None,
        "OPENAI_RESPONSE_MODEL": "response-model",
        "OPENAI_RELEVANCE_MODEL": "relevance-model",
        "OPENAI_EMBEDDING_MODEL": "embedding-model",
        "EMAIL_API_KEY": None,
        "RESEND_API_KEY": None,
        "RESEND_FROM_EMAIL": None,
        "REPORT_RECIPIENT": None,
        "PIPELINE_EMAIL_ENABLED": False,
        "PIPELINE_SCHEDULE": "0 8 * * *",
        "PIPELINE_COORDINATOR_LOCK_SECONDS": 900,
        "JWT_SECRET": "test-secret",
        "JWT_EXPIRY_MINUTES": 60,
        "GOOGLE_CLIENT_ID": None,
        "GOOGLE_CLIENT_SECRET": None,
        "API_URL": "http://localhost:8000",
        "FRONTEND_URL": "http://localhost:3000",
        "REDIS_URL": None,
        "REDDIT_CLIENT_ID": None,
        "REDDIT_CLIENT_SECRET": None,
    }
    values.update(overrides)
    return AppConfig(**values)


class ApiDependencyTests(unittest.TestCase):
    def test_builds_runtime_dependencies_from_postgres_config(self):
        database_url = "postgresql://postgres.example/lidscout"
        config = _app_config(
            DATABASE_URL=database_url,
            LLM_API_KEY="llm-key",
            RESEND_API_KEY="resend-key",
            RESEND_FROM_EMAIL="LidScout <alerts@example.com>",
            REPORT_RECIPIENT="founder@example.com",
        )

        with ExitStack() as stack:
            opportunity_repository = stack.enter_context(
                patch("api.dependencies.PostgresOpportunityRepository")
            )
            finding_repository = stack.enter_context(
                patch("api.dependencies.PostgresFindingRepository")
            )
            theme_repository = stack.enter_context(
                patch("api.dependencies.PostgresThemeRepository")
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
            agent_alert_repository = stack.enter_context(
                patch("api.dependencies.PostgresAgentAlertRepository")
            )
            agent_follow_up_repository = stack.enter_context(
                patch("api.dependencies.PostgresAgentFollowUpRepository")
            )
            agent_action_repository = stack.enter_context(
                patch("api.dependencies.PostgresAgentActionRepository")
            )
            niche_repository = stack.enter_context(
                patch("api.dependencies.PostgresNicheRepository")
            )
            niche_company_repository = stack.enter_context(
                patch("api.dependencies.PostgresNicheCompanyRepository")
            )
            niche_source_repository = stack.enter_context(
                patch("api.dependencies.PostgresNicheSourceRepository")
            )
            source_repository = stack.enter_context(
                patch("api.dependencies.PostgresSourceRepository")
            )
            template_source_binding_repository = stack.enter_context(
                patch("api.dependencies.PostgresTemplateSourceBindingRepository")
            )
            user_source_preference_repository = stack.enter_context(
                patch("api.dependencies.PostgresUserSourcePreferenceRepository")
            )
            user_source_repository = stack.enter_context(
                patch("api.dependencies.PostgresUserSourceRepository")
            )
            user_source_run_stats_repository = stack.enter_context(
                patch("api.dependencies.PostgresUserSourceRunStatsRepository")
            )
            user_niche_repository = stack.enter_context(
                patch("api.dependencies.PostgresUserNicheRepository")
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
        opportunity_repository.assert_called_once_with(connection=connection)
        finding_repository.assert_called_once_with(connection=connection)
        theme_repository.assert_called_once_with(connection=connection)
        metrics_repository.assert_called_once_with(connection=connection)
        agent_preferences_repository.assert_called_once_with(connection=connection)
        agent_feedback_repository.assert_called_once_with(connection=connection)
        agent_activity_repository.assert_called_once_with(connection=connection)
        agent_alert_repository.assert_called_once_with(connection=connection)
        agent_follow_up_repository.assert_called_once_with(connection=connection)
        agent_action_repository.assert_called_once_with(connection=connection)
        niche_repository.assert_called_once_with(connection=connection)
        niche_company_repository.assert_called_once_with(connection=connection)
        niche_source_repository.assert_called_once_with(connection=connection)
        source_repository.assert_called_once_with(connection=connection)
        template_source_binding_repository.assert_called_once_with(
            connection=connection,
        )
        user_source_preference_repository.assert_called_once_with(connection=connection)
        user_source_repository.assert_called_once_with(connection=connection)
        user_source_run_stats_repository.assert_called_once_with(connection=connection)
        user_niche_repository.assert_called_once_with(connection=connection)
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

        self.assertIn(json_adapter.return_value, dependencies.source_adapters)
        self.assertIn(static_adapter.return_value, dependencies.source_adapters)
        self.assertIs(
            dependencies.opportunity_repository,
            opportunity_repository.return_value,
        )
        self.assertIs(dependencies.finding_repository, finding_repository.return_value)
        self.assertIs(dependencies.theme_repository, theme_repository.return_value)
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
        self.assertIs(
            dependencies.agent_alert_repository,
            agent_alert_repository.return_value,
        )
        self.assertIs(
            dependencies.agent_follow_up_repository,
            agent_follow_up_repository.return_value,
        )
        self.assertIs(
            dependencies.niche_company_repository,
            niche_company_repository.return_value,
        )
        self.assertIs(
            dependencies.user_niche_repository,
            user_niche_repository.return_value,
        )
        self.assertIs(
            dependencies.niche_source_repository,
            niche_source_repository.return_value,
        )
        self.assertIs(dependencies.source_repository, source_repository.return_value)
        self.assertIs(
            dependencies.template_source_binding_repository,
            template_source_binding_repository.return_value,
        )
        self.assertIs(
            dependencies.user_source_preference_repository,
            user_source_preference_repository.return_value,
        )
        self.assertIs(
            dependencies.user_source_repository,
            user_source_repository.return_value,
        )
        self.assertIs(
            dependencies.user_source_run_stats_repository,
            user_source_run_stats_repository.return_value,
        )
        self.assertIs(dependencies.llm_client, llm_client.return_value)
        self.assertIs(dependencies.relevance_llm_client, llm_client.return_value)
        self.assertIs(dependencies.embedding_client, embedding_client.return_value)
        self.assertIs(dependencies.email_client, email_client.return_value)

    def test_builds_runtime_dependencies_with_supplied_connection(self):
        config = _app_config()
        supplied_connection = object()

        with patch("api.dependencies.connect_postgres") as connect_postgres:
            dependencies = build_signal_api_dependencies(
                config,
                connection=supplied_connection,
            )

        connect_postgres.assert_not_called()
        self.assertIs(
            dependencies.niche_source_repository.connection,
            supplied_connection,
        )
        self.assertIs(dependencies.source_repository.connection, supplied_connection)
        self.assertIs(
            dependencies.template_source_binding_repository.connection,
            supplied_connection,
        )
        self.assertIs(
            dependencies.user_source_preference_repository.connection,
            supplied_connection,
        )
        self.assertIs(
            dependencies.user_source_repository.connection,
            supplied_connection,
        )
        self.assertIs(
            dependencies.user_source_run_stats_repository.connection,
            supplied_connection,
        )
        self.assertIs(dependencies.finding_repository.connection, supplied_connection)
        self.assertIs(dependencies.theme_repository.connection, supplied_connection)

    def test_leaves_llm_client_empty_without_key(self):
        database_url = "postgresql://postgres.example/lidscout"
        config = _app_config(
            DATABASE_URL=database_url,
        )

        with ExitStack() as stack:
            for target in [
                "api.dependencies.PostgresOpportunityRepository",
                "api.dependencies.PostgresFindingRepository",
                "api.dependencies.PostgresThemeRepository",
                "api.dependencies.PostgresPipelineRunMetricsRepository",
                "api.dependencies.PostgresAgentPreferencesRepository",
                "api.dependencies.PostgresAgentFeedbackRepository",
                "api.dependencies.PostgresAgentActivityRepository",
                "api.dependencies.PostgresAgentAlertRepository",
                "api.dependencies.PostgresAgentFollowUpRepository",
                "api.dependencies.PostgresAgentActionRepository",
                "api.dependencies.PostgresNicheRepository",
                "api.dependencies.PostgresNicheCompanyRepository",
                "api.dependencies.PostgresNicheSourceRepository",
                "api.dependencies.PostgresSourceRepository",
                "api.dependencies.PostgresTemplateSourceBindingRepository",
                "api.dependencies.PostgresUserSourceRepository",
                "api.dependencies.PostgresUserSourcePreferenceRepository",
                "api.dependencies.PostgresUserNicheRepository",
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
        config = _app_config(
            DATABASE_URL="sqlite:///lidscout.db",
        )

        with self.assertRaises(ValueError):
            build_signal_api_dependencies(config)


if __name__ == "__main__":
    unittest.main()
