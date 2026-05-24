"""Resolve generic source inputs through source adapters."""
from dataclasses import dataclass
from typing import Protocol

from domain.post import RawPost
from domain.source import SourceInput


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
            if adapter is None:
                failed_count += 1
                details.append(
                    SourceFetchDetail(
                        source=source,
                        fetched_count=0,
                        error="No source adapter can handle locator",
                    )
                )
                continue

            try:
                source_posts = adapter.fetch_source(source, default_limit)
            except Exception as exc:
                failed_count += 1
                details.append(
                    SourceFetchDetail(
                        source=source,
                        fetched_count=0,
                        error=str(exc) or exc.__class__.__name__,
                    )
                )
                continue

            posts.extend(source_posts)
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
