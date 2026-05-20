import unittest
from unittest.mock import patch

from adapters.hackernews import HackerNewsActivityAdapter
from adapters.reddit import RedditActivityAdapter
from api.dependencies import build_signal_api_dependencies
from shared.config import AppConfig


class ApiDependencyTests(unittest.TestCase):
    def test_builds_runtime_dependencies_from_postgres_config(self):
        database_url = "postgresql://postgres.example/lidscout"
        config = AppConfig(
            DATABASE_URL=database_url,
            LLM_API_KEY="llm-key",
            REDDIT_CLIENT_ID=None,
            REDDIT_CLIENT_SECRET=None,
            EMAIL_API_KEY=None,
            PIPELINE_SCHEDULE="0 8 * * *",
        )

        with (
            patch("api.dependencies.PostgresPostRepository") as post_repository,
            patch("api.dependencies.PostgresSignalRepository") as signal_repository,
            patch("api.dependencies.PostgresScoreRepository") as score_repository,
            patch("api.dependencies.PostgresClusterRepository") as cluster_repository,
            patch("api.dependencies.OpenAIResponsesClient") as llm_client,
        ):
            dependencies = build_signal_api_dependencies(config)

        post_repository.assert_called_once_with(database_url)
        signal_repository.assert_called_once_with(database_url)
        score_repository.assert_called_once_with(database_url)
        cluster_repository.assert_called_once_with(database_url)
        llm_client.assert_called_once_with(api_key="llm-key")

        self.assertIsInstance(dependencies.reddit_adapter, RedditActivityAdapter)
        self.assertIsInstance(dependencies.hackernews_adapter, HackerNewsActivityAdapter)
        self.assertIs(dependencies.post_repository, post_repository.return_value)
        self.assertIs(dependencies.signal_repository, signal_repository.return_value)
        self.assertIs(dependencies.score_repository, score_repository.return_value)
        self.assertIs(dependencies.cluster_repository, cluster_repository.return_value)
        self.assertIs(dependencies.llm_client, llm_client.return_value)
        self.assertIsNone(dependencies.embedding_client)
        self.assertIsNone(dependencies.email_client)

    def test_leaves_llm_client_empty_without_key(self):
        database_url = "postgresql://postgres.example/lidscout"
        config = AppConfig(
            DATABASE_URL=database_url,
            LLM_API_KEY=None,
            REDDIT_CLIENT_ID=None,
            REDDIT_CLIENT_SECRET=None,
            EMAIL_API_KEY=None,
            PIPELINE_SCHEDULE="0 8 * * *",
        )

        with (
            patch("api.dependencies.PostgresPostRepository"),
            patch("api.dependencies.PostgresSignalRepository"),
            patch("api.dependencies.PostgresScoreRepository"),
            patch("api.dependencies.PostgresClusterRepository"),
        ):
            dependencies = build_signal_api_dependencies(config)

        self.assertIsNone(dependencies.llm_client)

    def test_rejects_non_postgres_database_url(self):
        config = AppConfig(
            DATABASE_URL="sqlite:///lidscout.db",
            LLM_API_KEY=None,
            REDDIT_CLIENT_ID=None,
            REDDIT_CLIENT_SECRET=None,
            EMAIL_API_KEY=None,
            PIPELINE_SCHEDULE="0 8 * * *",
        )

        with self.assertRaises(ValueError):
            build_signal_api_dependencies(config)


if __name__ == "__main__":
    unittest.main()
