"""Helpers for logging URLs without leaking credentials."""
from urllib.parse import parse_qsl, urlencode, urlparse


SENSITIVE_QUERY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "key",
    "password",
    "secret",
    "signature",
    "token",
)


def safe_url_for_logs(url: str) -> str:
    """Return a URL with sensitive query values redacted for logs."""
    parsed = urlparse(url)
    if not parsed.query:
        return url

    query = [
        (key, "REDACTED" if _is_sensitive_key(key) else value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return parsed._replace(query=urlencode(query)).geturl()


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in SENSITIVE_QUERY_PARTS)
