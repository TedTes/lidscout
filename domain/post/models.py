"""Raw online post entity."""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class RawPost:
    """Source-agnostic post captured from an online activity source."""

    id: str
    source: str
    source_id: str
    title: str
    body: str
    author: str | None
    url: str | None
    created_at: datetime | None
    upvotes: int | None
    comments_count: int | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        source: str,
        source_id: str,
        title: str = "",
        body: str = "",
        author: str | None = None,
        url: str | None = None,
        created_at: datetime | int | float | None = None,
        upvotes: int | None = None,
        comments_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "RawPost":
        """Build a normalized raw post with a stable internal id."""
        normalized_source = source.strip().lower()
        normalized_source_id = str(source_id).strip()
        if not normalized_source:
            raise ValueError("source is required")
        if not normalized_source_id:
            raise ValueError("source_id is required")

        return cls(
            id=f"{normalized_source}:{normalized_source_id}",
            source=normalized_source,
            source_id=normalized_source_id,
            title=title.strip(),
            body=body.strip(),
            author=author.strip() if author else None,
            url=url.strip() if url else None,
            created_at=cls._normalize_timestamp(created_at),
            upvotes=upvotes,
            comments_count=comments_count,
            metadata=metadata or {},
        )

    @staticmethod
    def _normalize_timestamp(value: datetime | int | float | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        return datetime.fromtimestamp(value, tz=UTC)
