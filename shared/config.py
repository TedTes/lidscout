"""Runtime configuration for LidScout."""
from dataclasses import dataclass
from functools import lru_cache
import os

from dotenv import load_dotenv


def load_environment(env_file: str | None = None) -> None:
    """Load local environment variables from a .env file when present."""
    load_dotenv(env_file, override=False)


load_environment()


@dataclass(frozen=True)
class Settings:
    """Environment-backed application settings."""

    api_title: str
    api_description: str
    api_version: str
    cors_origins: list[str]
    http_user_agent: str
    request_timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    """Typed configuration for pipeline and external service integrations."""

    DATABASE_URL: str
    LLM_API_KEY: str | None
    OPENAI_RESPONSE_MODEL: str
    OPENAI_EMBEDDING_MODEL: str
    REDDIT_CLIENT_ID: str | None
    REDDIT_CLIENT_SECRET: str | None
    EMAIL_API_KEY: str | None
    RESEND_API_KEY: str | None
    RESEND_FROM_EMAIL: str | None
    PIPELINE_SCHEDULE: str


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    cleaned = value.strip()
    return cleaned or default


@lru_cache
def get_settings() -> Settings:
    """Load settings once per process."""
    return Settings(
        api_title=os.getenv("API_TITLE", "LidScout API"),
        api_description=os.getenv(
            "API_DESCRIPTION",
            "API for signal detection from public online activity",
        ),
        api_version=os.getenv("API_VERSION", "1.0.0"),
        cors_origins=_csv(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://localhost:3001",
            )
        ),
        http_user_agent=os.getenv(
            "HTTP_USER_AGENT",
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        ),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
    )


@lru_cache
def get_app_config() -> AppConfig:
    """Load typed application configuration once per process."""
    return AppConfig(
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///lidscout.db").strip(),
        LLM_API_KEY=_optional_env("LLM_API_KEY"),
        OPENAI_RESPONSE_MODEL=_env_or_default("OPENAI_RESPONSE_MODEL", "gpt-4o-mini"),
        OPENAI_EMBEDDING_MODEL=_env_or_default(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ),
        REDDIT_CLIENT_ID=_optional_env("REDDIT_CLIENT_ID"),
        REDDIT_CLIENT_SECRET=_optional_env("REDDIT_CLIENT_SECRET"),
        EMAIL_API_KEY=_optional_env("EMAIL_API_KEY"),
        RESEND_API_KEY=_optional_env("RESEND_API_KEY") or _optional_env("EMAIL_API_KEY"),
        RESEND_FROM_EMAIL=_optional_env("RESEND_FROM_EMAIL") or _optional_env("EMAIL_FROM"),
        PIPELINE_SCHEDULE=os.getenv("PIPELINE_SCHEDULE", "0 8 * * *").strip(),
    )
