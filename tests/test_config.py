import os
from unittest.mock import patch
import unittest

from shared.config import get_app_config


class AppConfigTests(unittest.TestCase):
    def tearDown(self):
        get_app_config.cache_clear()

    def test_loads_app_config_from_environment(self):
        get_app_config.cache_clear()
        env = {
            "DATABASE_URL": "sqlite:///tmp/lidscout.db",
            "LLM_API_KEY": "llm-key",
            "REDDIT_CLIENT_ID": "reddit-id",
            "REDDIT_CLIENT_SECRET": "reddit-secret",
            "EMAIL_API_KEY": "email-key",
            "PIPELINE_SCHEDULE": "0 6 * * *",
        }

        with patch.dict(os.environ, env, clear=False):
            config = get_app_config()

        self.assertEqual(config.DATABASE_URL, "sqlite:///tmp/lidscout.db")
        self.assertEqual(config.LLM_API_KEY, "llm-key")
        self.assertEqual(config.REDDIT_CLIENT_ID, "reddit-id")
        self.assertEqual(config.REDDIT_CLIENT_SECRET, "reddit-secret")
        self.assertEqual(config.EMAIL_API_KEY, "email-key")
        self.assertEqual(config.PIPELINE_SCHEDULE, "0 6 * * *")

    def test_uses_defaults_and_normalizes_blank_secrets(self):
        get_app_config.cache_clear()
        env = {
            "LLM_API_KEY": " ",
            "REDDIT_CLIENT_ID": "",
            "REDDIT_CLIENT_SECRET": " ",
            "EMAIL_API_KEY": "",
        }

        with patch.dict(os.environ, env, clear=True):
            config = get_app_config()

        self.assertEqual(config.DATABASE_URL, "sqlite:///lidscout.db")
        self.assertIsNone(config.LLM_API_KEY)
        self.assertIsNone(config.REDDIT_CLIENT_ID)
        self.assertIsNone(config.REDDIT_CLIENT_SECRET)
        self.assertIsNone(config.EMAIL_API_KEY)
        self.assertEqual(config.PIPELINE_SCHEDULE, "0 8 * * *")


if __name__ == "__main__":
    unittest.main()
