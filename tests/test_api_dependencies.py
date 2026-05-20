import unittest

from adapters.hackernews import HackerNewsActivityAdapter
from adapters.reddit import RedditActivityAdapter
from api.dependencies import build_signal_api_dependencies


class ApiDependencyTests(unittest.TestCase):
    def test_builds_available_runtime_dependencies(self):
        dependencies = build_signal_api_dependencies()

        self.assertIsInstance(dependencies.reddit_adapter, RedditActivityAdapter)
        self.assertIsInstance(dependencies.hackernews_adapter, HackerNewsActivityAdapter)
        self.assertIsNone(dependencies.llm_client)
        self.assertIsNone(dependencies.embedding_client)
        self.assertIsNone(dependencies.email_client)


if __name__ == "__main__":
    unittest.main()
