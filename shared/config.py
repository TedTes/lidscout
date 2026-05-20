"""Runtime configuration for LidScout."""
from dataclasses import dataclass
from functools import lru_cache
import os


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
    REDDIT_CLIENT_ID: str | None
    REDDIT_CLIENT_SECRET: str | None
    EMAIL_API_KEY: str | None
    PIPELINE_SCHEDULE: str


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


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
        REDDIT_CLIENT_ID=_optional_env("REDDIT_CLIENT_ID"),
        REDDIT_CLIENT_SECRET=_optional_env("REDDIT_CLIENT_SECRET"),
        EMAIL_API_KEY=_optional_env("EMAIL_API_KEY"),
        PIPELINE_SCHEDULE=os.getenv("PIPELINE_SCHEDULE", "0 8 * * *").strip(),
    )
