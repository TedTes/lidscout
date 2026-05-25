"""Resolve generic source inputs through source adapters."""
from dataclasses import dataclass
import logging
from time import perf_counter
from typing import Protocol

from domain.post import RawPost
from domain.source import SourceInput
from shared.logger import get_logger, log_event
from shared.url_logging import safe_url_for_logs


logger = get_logger(__name__)


class SourceAdapter(Protocol):
    """Adapter contract for fetching posts from a generic source input."""

    def can_handle(self, source: SourceInput) -> bool:
        """Return whether this adapter can fetch the given source."""
        ...

    def fetch_source(self, source: SourceInput, default_limit: int = 25) -> list[RawPost]:
        """Fetch source data and normalize it into raw posts."""
        ...


@dataclass(frozen=True)
class SourceFetchDetail:
    """Fetch outcome for one source input."""

    source: SourceInput
    fetched_count: int
    error: str | None = None


@dataclass(frozen=True)
class SourceFetchResult:
    """Fetched posts, failure count, and per-source outcomes for a batch."""

    posts: list[RawPost]
    failed_count: int
    details: list[SourceFetchDetail]


class SourceResolver:
    """Routes source inputs to the first adapter that can handle each one."""

    def __init__(self, adapters: list[SourceAdapter]):
        self.adapters = adapters

    def fetch(
        self,
        sources: list[SourceInput],
        default_limit: int = 25,
    ) -> SourceFetchResult:
        """Fetch all source inputs through matching adapters."""
        posts: list[RawPost] = []
        failed_count = 0
        details: list[SourceFetchDetail] = []

        for source in sources:
            adapter = self._adapter_for(source)
            source_context = _source_context(source)
            if adapter is None:
                failed_count += 1
                log_event(
                    logger,
                    "source_fetch_skipped",
                    level=logging.WARNING,
                    error="No source adapter can handle locator",
                    **source_context,
                )
                details.append(
                    SourceFetchDetail(
                        source=source,
                        fetched_count=0,
                        error="No source adapter can handle locator",
                    )
                )
                continue

            adapter_name = adapter.__class__.__name__
            log_event(
                logger,
                "source_fetch_started",
                adapter=adapter_name,
                **source_context,
            )
            started_at = perf_counter()
            try:
                source_posts = adapter.fetch_source(source, default_limit)
            except Exception as exc:
                failed_count += 1
                duration_ms = round((perf_counter() - started_at) * 1000, 2)
                error = str(exc) or exc.__class__.__name__
                log_event(
                    logger,
                    "source_fetch_failed",
                    level=logging.WARNING,
                    adapter=adapter_name,
                    duration_ms=duration_ms,
                    error=error,
                    error_type=exc.__class__.__name__,
                    **source_context,
                )
                details.append(
                    SourceFetchDetail(
                        source=source,
                        fetched_count=0,
                        error=error,
                    )
                )
                continue

            posts.extend(source_posts)
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            log_event(
                logger,
                "source_fetch_completed",
                adapter=adapter_name,
                duration_ms=duration_ms,
                fetched_count=len(source_posts),
                **source_context,
            )
            details.append(
                SourceFetchDetail(
                    source=source,
                    fetched_count=len(source_posts),
                    error=None,
                )
            )

        return SourceFetchResult(
            posts=posts,
            failed_count=failed_count,
            details=details,
        )

    def _adapter_for(self, source: SourceInput) -> SourceAdapter | None:
        for adapter in self.adapters:
            if adapter.can_handle(source):
                return adapter
        return None


def _source_context(source: SourceInput) -> dict[str, object]:
    return {
        "locator": safe_url_for_logs(source.locator),
        "limit": source.limit,
        "source_type": source.options.get("source_type"),
        "source_family": source.options.get("source_family"),
        "market_id": source.options.get("market_id"),
        "market_name": source.options.get("market_name"),
        "competitor_id": source.options.get("competitor_id"),
        "competitor_name": source.options.get("competitor_name"),
        "monitored_source_id": source.options.get("monitored_source_id"),
    }
