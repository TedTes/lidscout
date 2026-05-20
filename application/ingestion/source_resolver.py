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
class SourceFetchResult:
    """Fetched posts and failure count for a source batch."""

    posts: list[RawPost]
    failed_count: int


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

        for source in sources:
            adapter = self._adapter_for(source)
            if adapter is None:
                failed_count += 1
                continue

            try:
                posts.extend(adapter.fetch_source(source, default_limit))
            except Exception:
                failed_count += 1

        return SourceFetchResult(posts=posts, failed_count=failed_count)

    def _adapter_for(self, source: SourceInput) -> SourceAdapter | None:
        for adapter in self.adapters:
            if adapter.can_handle(source):
                return adapter
        return None
