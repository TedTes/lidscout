"""Raw post ingestion service."""
from dataclasses import dataclass
from typing import Protocol

from domain.post import RawPost


@dataclass(frozen=True)
class IngestionResult:
    """Counts produced by a raw post ingestion run."""

    received_count: int
    inserted_count: int
    duplicate_count: int
    failed_count: int


class RawPostRepository(Protocol):
    """Persistence boundary for raw posts."""

    def save_posts(self, posts: list[RawPost]) -> int:
        """Persist posts and return the number inserted."""
        ...


class IngestionService:
    """Validates, deduplicates, normalizes, and persists raw posts."""

    def __init__(self, repository: RawPostRepository):
        self.repository = repository

    def ingest(self, posts: list[RawPost]) -> IngestionResult:
        received_count = len(posts)
        failed_count = 0
        normalized_posts: list[RawPost] = []
        seen_ids: set[str] = set()

        for post in posts:
            try:
                normalized = self._normalize(post)
            except ValueError:
                failed_count += 1
                continue

            if normalized.id in seen_ids:
                continue

            seen_ids.add(normalized.id)
            normalized_posts.append(normalized)

        inserted_count = self.repository.save_posts(normalized_posts)
        duplicate_count = received_count - failed_count - inserted_count

        return IngestionResult(
            received_count=received_count,
            inserted_count=inserted_count,
            duplicate_count=duplicate_count,
            failed_count=failed_count,
        )

    def _normalize(self, post: RawPost) -> RawPost:
        return RawPost.create(
            source=post.source,
            source_id=post.source_id,
            title=post.title,
            body=post.body,
            author=post.author,
            url=post.url,
            created_at=post.created_at,
            upvotes=post.upvotes,
            comments_count=post.comments_count,
            metadata=post.metadata,
        )
