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


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


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
        cors_origins=_csv(os.getenv("CORS_ORIGINS", "http://localhost:3000")),
        http_user_agent=os.getenv(
            "HTTP_USER_AGENT",
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        ),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
    )
