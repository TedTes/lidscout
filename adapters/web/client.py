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
from shared.logger import get_logger, log_event
from shared.url_logging import safe_url_for_logs


logger = get_logger(__name__)


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
        _log_response("static_url_response_received", source, response)
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
            metadata=_source_metadata(source, parsed.netloc),
        )


class JsonUrlAdapter(BaseUrlAdapter):
    """Fetches public JSON URLs and normalizes text-bearing records."""

    def can_handle(self, source: SourceInput) -> bool:
        """Return whether this adapter can fetch the source input."""
        return _is_http_url(source.locator) and (
            source.options.get("adapter") == "json"
            or _looks_like_json_url(source.locator)
        )

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        """Fetch a JSON URL source and normalize it into raw posts."""
        response = requests.get(
            source.locator,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        _log_response("json_url_response_received", source, response)
        response.raise_for_status()
        return self._normalize_json(source, response.json(), default_limit)

    def _normalize_json(
        self,
        source: SourceInput,
        payload: Any,
        default_limit: int,
    ) -> list[RawPost]:
        return _normalize_json_payload(source, payload, default_limit)


class RedditAdapter:
    """Fetches Reddit posts via PRAW (Python Reddit API Wrapper).

    PRAW handles OAuth token management, rate limiting, and 429 backoff
    automatically. Uses read-only client-credentials flow — no user login needed.
    """

    def __init__(self, client_id: str, client_secret: str):
        import praw
        self._reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="python:lidscout:v1.0",
        )

    def can_handle(self, source: SourceInput) -> bool:
        return "reddit.com" in source.locator

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        limit = source.limit or default_limit
        parsed = urlparse(source.locator)
        path = parsed.path.rstrip("/")
        params = dict(pair.split("=", 1) for pair in parsed.query.split("&") if "=" in pair)
        query = params.get("q", "")

        if "/search" in path and query:
            submissions = self._reddit.subreddit("all").search(
                query, sort="new", limit=limit
            )
        else:
            # e.g. /r/SimplePractice/new or /r/therapists/new
            parts = [p for p in path.split("/") if p]
            subreddit_name = parts[1] if len(parts) >= 2 else "all"
            subreddit = self._reddit.subreddit(subreddit_name)
            submissions = subreddit.new(limit=limit)

        posts = [self._to_raw_post(source, submission) for submission in submissions]
        log_event(logger, "reddit_fetched", locator=safe_url_for_logs(source.locator), count=len(posts))
        return posts

    def _to_raw_post(self, source: SourceInput, submission: Any) -> RawPost:
        parsed = urlparse(source.locator)
        return RawPost.create(
            source="reddit",
            source_id=submission.id,
            title=submission.title,
            body=submission.selftext or "",
            author=str(submission.author) if submission.author else None,
            url=f"https://www.reddit.com{submission.permalink}",
            created_at=datetime.utcfromtimestamp(submission.created_utc),
            upvotes=submission.score,
            comments_count=submission.num_comments,
            metadata=_source_metadata(source, parsed.netloc),
        )


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


def _normalize_json_payload(
    source: SourceInput,
    payload: Any,
    default_limit: int,
    source_label: str = "web_json",
) -> list[RawPost]:
    items_path = source.options.get("items_path")
    if items_path and isinstance(payload, dict):
        raw = payload.get(items_path)
        candidates = raw if isinstance(raw, list) else []
    else:
        candidates = _walk_json_records(payload)
    records = [r for r in candidates if isinstance(r, dict) and _record_text(r)]
    limit = source.limit or default_limit
    posts = [
        _raw_post_from_record(source, record, index)
        for index, record in enumerate(records[:limit])
    ]
    if posts:
        return posts
    return [
        RawPost.create(
            source=source_label,
            source_id=_source_id(source.locator),
            title=source.locator,
            body=str(payload),
            url=source.locator,
            metadata=_source_metadata(source, urlparse(source.locator).netloc),
        )
    ]


def _is_http_url(locator: str) -> bool:
    parsed = urlparse(locator)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _log_response(event: str, source: SourceInput, response: requests.Response) -> None:
    content_length = response.headers.get("content-length")
    log_event(
        logger,
        event,
        locator=safe_url_for_logs(source.locator),
        status_code=response.status_code,
        content_type=response.headers.get("content-type"),
        content_length=(
            int(content_length)
            if content_length and content_length.isdigit()
            else None
        ),
        source_type=source.options.get("source_type"),
        source_family=source.options.get("source_family"),
        market_id=source.options.get("market_id"),
        competitor_id=source.options.get("competitor_id"),
        monitored_source_id=source.options.get("monitored_source_id"),
    )


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
    for key in (
        "title",
        "name",
        "body",
        "text",
        "selftext",
        "story_text",
        "comment_text",
        "description",
        "comment",
        "content",
    ):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n".join(parts)


def _record_title(record: dict[str, Any], fallback: str) -> str:
    for key in ("title", "name", "story_title"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _record_author(record: dict[str, Any]) -> str | None:
    for key in ("author", "by", "user", "username"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("user", "owner"):
        value = record.get(key)
        if isinstance(value, dict):
            for nested_key in ("login", "display_name", "name", "username"):
                nested_value = value.get(nested_key)
                if isinstance(nested_value, str) and nested_value.strip():
                    return nested_value.strip()
    return None


def _record_timestamp(record: dict[str, Any]) -> datetime | int | float | None:
    for key in (
        "created_at",
        "created_utc",
        "creation_date",
        "updated_at",
        "time",
        "timestamp",
    ):
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
    record_id = (
        record.get("id")
        or record.get("objectID")
        or record.get("question_id")
        or record.get("number")
        or record.get("permalink")
        or record.get("html_url")
        or record.get("link")
    )
    source_id = str(record_id) if record_id else f"{_source_id(source.locator)}:{index}"
    permalink = record.get("permalink")
    record_url = record.get("html_url") or record.get("link") or record.get("url")
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
        comments_count=_record_int(
            record,
            "num_comments",
            "comments_count",
            "comments",
            "answer_count",
            "descendants",
        ),
        metadata=_source_metadata(source, parsed.netloc),
    )


def _source_metadata(source: SourceInput, domain: str) -> dict[str, Any]:
    metadata = {
        "domain": domain.lower(),
    }
    for key in (
        "competitor_id",
        "competitor_name",
        "competitor_website",
        "competitor_domain",
        "competitor_category",
        "monitored_source_id",
        "niche_source_id",
        "market_id",
        "market_name",
        "market_target_user",
        "market_idea_prompt",
        "source_family",
        "source_type",
        "source_tier",
        "source_quality_score",
        "source_access_mode",
        "agent_extra_instructions",
        "agent_ignored_themes",
        "agent_ignored_categories",
    ):
        value = source.options.get(key)
        if isinstance(value, str) and value.strip():
            metadata[key] = value.strip()
    return metadata


WebPageActivityAdapter = UrlActivityAdapter
