import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from shared.config import get_app_config, get_settings, load_environment


class AppConfigTests(unittest.TestCase):
    def tearDown(self):
        get_app_config.cache_clear()
        get_settings.cache_clear()

    def test_loads_app_config_from_environment(self):
        get_app_config.cache_clear()
        env = {
            "DATABASE_URL": "sqlite:///tmp/lidscout.db",
            "LLM_API_KEY": "llm-key",
            "OPENAI_RESPONSE_MODEL": "response-model",
            "OPENAI_EMBEDDING_MODEL": "embedding-model",
            "EMAIL_API_KEY": "email-key",
            "RESEND_API_KEY": "resend-key",
            "RESEND_FROM_EMAIL": "LidScout <alerts@example.com>",
            "PIPELINE_SCHEDULE": "0 6 * * *",
        }

        with patch.dict(os.environ, env, clear=False):
            config = get_app_config()

        self.assertEqual(config.DATABASE_URL, "sqlite:///tmp/lidscout.db")
        self.assertEqual(config.LLM_API_KEY, "llm-key")
        self.assertEqual(config.OPENAI_RESPONSE_MODEL, "response-model")
        self.assertEqual(config.OPENAI_EMBEDDING_MODEL, "embedding-model")
        self.assertEqual(config.EMAIL_API_KEY, "email-key")
        self.assertEqual(config.RESEND_API_KEY, "resend-key")
        self.assertEqual(config.RESEND_FROM_EMAIL, "LidScout <alerts@example.com>")
        self.assertEqual(config.PIPELINE_SCHEDULE, "0 6 * * *")

    def test_uses_defaults_and_normalizes_blank_secrets(self):
        get_app_config.cache_clear()
        env = {
            "LLM_API_KEY": " ",
            "OPENAI_RESPONSE_MODEL": " ",
            "OPENAI_EMBEDDING_MODEL": "",
            "EMAIL_API_KEY": "",
            "RESEND_API_KEY": "",
            "RESEND_FROM_EMAIL": " ",
        }

        with patch.dict(os.environ, env, clear=True):
            config = get_app_config()

        self.assertEqual(config.DATABASE_URL, "sqlite:///lidscout.db")
        self.assertIsNone(config.LLM_API_KEY)
        self.assertEqual(config.OPENAI_RESPONSE_MODEL, "gpt-4o-mini")
        self.assertEqual(config.OPENAI_EMBEDDING_MODEL, "text-embedding-3-small")
        self.assertIsNone(config.EMAIL_API_KEY)
        self.assertIsNone(config.RESEND_API_KEY)
        self.assertIsNone(config.RESEND_FROM_EMAIL)
        self.assertEqual(config.PIPELINE_SCHEDULE, "0 8 * * *")

    def test_uses_email_api_key_as_resend_fallback(self):
        get_app_config.cache_clear()
        env = {
            "EMAIL_API_KEY": "email-key",
            "EMAIL_FROM": "LidScout <alerts@example.com>",
        }

        with patch.dict(os.environ, env, clear=True):
            config = get_app_config()

        self.assertEqual(config.RESEND_API_KEY, "email-key")
        self.assertEqual(config.RESEND_FROM_EMAIL, "LidScout <alerts@example.com>")

    def test_default_cors_origins_include_local_dev_ports(self):
        get_settings.cache_clear()

        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

        self.assertIn("http://localhost:3000", settings.cors_origins)
        self.assertIn("http://localhost:3001", settings.cors_origins)

    def test_loads_app_config_from_dotenv_file(self):
        get_app_config.cache_clear()

        with TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "DATABASE_URL=postgresql://localhost/lidscout",
                        "LLM_API_KEY=llm-from-env-file",
                        "OPENAI_RESPONSE_MODEL=response-from-env-file",
                        "OPENAI_EMBEDDING_MODEL=embedding-from-env-file",
                        "RESEND_API_KEY=resend-from-env-file",
                        "RESEND_FROM_EMAIL=LidScout <alerts@example.com>",
                        "PIPELINE_SCHEDULE=0 7 * * *",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                load_environment(str(env_file))
                config = get_app_config()

        self.assertEqual(config.DATABASE_URL, "postgresql://localhost/lidscout")
        self.assertEqual(config.LLM_API_KEY, "llm-from-env-file")
        self.assertEqual(config.OPENAI_RESPONSE_MODEL, "response-from-env-file")
        self.assertEqual(config.OPENAI_EMBEDDING_MODEL, "embedding-from-env-file")
        self.assertEqual(config.RESEND_API_KEY, "resend-from-env-file")
        self.assertEqual(config.RESEND_FROM_EMAIL, "LidScout <alerts@example.com>")
        self.assertEqual(config.PIPELINE_SCHEDULE, "0 7 * * *")


if __name__ == "__main__":
    unittest.main()
