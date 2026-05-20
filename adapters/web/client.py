"""Capability-based URL activity adapters."""
from datetime import datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from domain.post import RawPost
from domain.source import SourceInput
from shared.config import get_settings


class BaseUrlAdapter:
    """Shared configuration for URL fetch adapters."""
    def __init__(self):
        settings = get_settings()
        self.timeout_seconds = settings.request_timeout_seconds
        self.headers = {"User-Agent": settings.http_user_agent}


class StaticUrlAdapter(BaseUrlAdapter):
    """Fetches static public HTML pages and normalizes visible text."""

    def can_handle(self, source: SourceInput) -> bool:
        """Return whether this adapter can fetch the source input."""
        return _is_http_url(source.locator) and not _looks_like_json_url(source.locator)

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        """Fetch a static HTML URL source and normalize it into one raw post."""
        response = requests.get(
            source.locator,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return [self._normalize_page(source, response.text)]

    def _normalize_page(self, source: SourceInput, html: str) -> RawPost:
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        title = _page_title(soup) or source.locator
        body = _page_text(soup)
        parsed = urlparse(source.locator)

        return RawPost.create(
            source="web",
            source_id=_source_id(source.locator),
            title=title,
            body=body,
            author=None,
            url=source.locator,
            created_at=None,
            upvotes=None,
            comments_count=None,
            metadata={
                "domain": parsed.netloc.lower(),
            },
        )


class JsonUrlAdapter(BaseUrlAdapter):
    """Fetches public JSON URLs and normalizes text-bearing records."""

    def can_handle(self, source: SourceInput) -> bool:
        """Return whether this adapter can fetch the source input."""
        return _is_http_url(source.locator) and _looks_like_json_url(source.locator)

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        """Fetch a JSON URL source and normalize it into raw posts."""
        response = requests.get(
            source.locator,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return self._normalize_json(source, response.json(), default_limit)

    def _normalize_json(
        self,
        source: SourceInput,
        payload: Any,
        default_limit: int,
    ) -> list[RawPost]:
        records = [
            record
            for record in _walk_json_records(payload)
            if _record_text(record)
        ]
        limit = source.limit or default_limit
        posts = [
            _raw_post_from_record(source, record, index)
            for index, record in enumerate(records[:limit])
        ]

        if posts:
            return posts

        return [
            RawPost.create(
                source="web_json",
                source_id=_source_id(source.locator),
                title=source.locator,
                body=str(payload),
                url=source.locator,
                metadata={"domain": urlparse(source.locator).netloc.lower()},
            )
        ]


class RenderedUrlAdapter(BaseUrlAdapter):
    """Placeholder for browser-rendered page fetching."""

    def can_handle(self, source: SourceInput) -> bool:
        return bool(source.options.get("render"))

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        raise NotImplementedError("Rendered URL fetching is not implemented yet")


class FeedAdapter(BaseUrlAdapter):
    """Placeholder for RSS/Atom feed fetching."""

    def can_handle(self, source: SourceInput) -> bool:
        return False

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        raise NotImplementedError("Feed fetching is not implemented yet")


class DocumentAdapter(BaseUrlAdapter):
    """Placeholder for document fetching such as PDF or plain text files."""

    def can_handle(self, source: SourceInput) -> bool:
        return False

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        raise NotImplementedError("Document fetching is not implemented yet")


class ApiAdapter(BaseUrlAdapter):
    """Placeholder for authenticated or custom API fetching."""

    def can_handle(self, source: SourceInput) -> bool:
        return False

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        raise NotImplementedError("API source fetching is not implemented yet")


class BrowserSessionAdapter(BaseUrlAdapter):
    """Placeholder for browser-session scraping with cookies or login state."""

    def can_handle(self, source: SourceInput) -> bool:
        return False

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        raise NotImplementedError("Browser session fetching is not implemented yet")


class UrlActivityAdapter:
    """Composite URL adapter kept for compatibility with existing imports."""

    def __init__(self):
        self.adapters = [
            JsonUrlAdapter(),
            StaticUrlAdapter(),
        ]

    def can_handle(self, source: SourceInput) -> bool:
        return any(adapter.can_handle(source) for adapter in self.adapters)

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        for adapter in self.adapters:
            if adapter.can_handle(source):
                return adapter.fetch_source(source, default_limit)
        raise ValueError("source locator is not supported")


def _is_http_url(locator: str) -> bool:
    parsed = urlparse(locator)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _looks_like_json_url(locator: str) -> bool:
    return urlparse(locator).path.rstrip("/").endswith(".json")


def _source_id(locator: str) -> str:
    return sha256(locator.encode("utf-8")).hexdigest()[:16]


def _page_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    heading = soup.find("h1")
    return heading.get_text(" ", strip=True) if heading else ""


def _page_text(soup: BeautifulSoup) -> str:
    candidates = soup.find_all(["h1", "h2", "h3", "p", "li", "blockquote"])
    parts = [candidate.get_text(" ", strip=True) for candidate in candidates]
    return "\n".join(part for part in parts if part)


def _walk_json_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        records.append(payload)
        for value in payload.values():
            records.extend(_walk_json_records(value))
    elif isinstance(payload, list):
        for item in payload:
            records.extend(_walk_json_records(item))
    return records


def _record_text(record: dict[str, Any]) -> str:
    parts = []
    for key in ("title", "name", "body", "text", "selftext", "description", "comment"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n".join(parts)


def _record_title(record: dict[str, Any], fallback: str) -> str:
    for key in ("title", "name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _record_author(record: dict[str, Any]) -> str | None:
    for key in ("author", "by", "user", "username"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _record_timestamp(record: dict[str, Any]) -> datetime | int | float | None:
    for key in ("created_at", "created_utc", "time", "timestamp"):
        value = record.get(key)
        if isinstance(value, (int, float, datetime)):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _record_int(record: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _raw_post_from_record(
    source: SourceInput,
    record: dict[str, Any],
    index: int,
) -> RawPost:
    parsed = urlparse(source.locator)
    record_id = record.get("id") or record.get("objectID") or record.get("permalink")
    source_id = str(record_id) if record_id else f"{_source_id(source.locator)}:{index}"
    permalink = record.get("permalink")
    record_url = record.get("url")
    if isinstance(permalink, str) and permalink.startswith("/"):
        record_url = f"{parsed.scheme}://{parsed.netloc}{permalink}"

    return RawPost.create(
        source="web_json",
        source_id=source_id,
        title=_record_title(record, source.locator),
        body=_record_text(record),
        author=_record_author(record),
        url=record_url if isinstance(record_url, str) else source.locator,
        created_at=_record_timestamp(record),
        upvotes=_record_int(record, "score", "points", "upvotes"),
        comments_count=_record_int(record, "num_comments", "comments_count", "descendants"),
        metadata={
            "domain": parsed.netloc.lower(),
        },
    )


WebPageActivityAdapter = UrlActivityAdapter
