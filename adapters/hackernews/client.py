"""Hacker News public activity adapter."""
from typing import Any

import requests

from domain.post import RawPost
from shared.config import get_settings


class HackerNewsActivityAdapter:
    """Fetches public Hacker News activity through the Firebase API."""

    base_url = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):
        settings = get_settings()
        self.timeout_seconds = settings.request_timeout_seconds

    def top_items(self, limit: int = 25) -> list[RawPost]:
        """Return normalized top HN stories."""
        ids_response = requests.get(
            f"{self.base_url}/topstories.json",
            timeout=self.timeout_seconds,
        )
        ids_response.raise_for_status()
        item_ids = ids_response.json()[:limit]
        return [
            self._fetch_item(item_id)
            for item_id in item_ids
        ]

    def _fetch_item(self, item_id: int) -> RawPost:
        response = requests.get(
            f"{self.base_url}/item/{item_id}.json",
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        item: dict[str, Any] = response.json()
        return self._normalize_item(item, fallback_item_id=item_id)

    def _normalize_item(self, item: dict[str, Any], fallback_item_id: int | None = None) -> RawPost:
        source_id = str(item.get("id") or fallback_item_id or "")
        return RawPost.create(
            source="hackernews",
            source_id=source_id,
            title=item.get("title") or "",
            body=item.get("text") or "",
            author=item.get("by"),
            url=item.get("url") or f"https://news.ycombinator.com/item?id={source_id}",
            created_at=item.get("time"),
            upvotes=item.get("score"),
            comments_count=item.get("descendants"),
            metadata={
                "type": item.get("type"),
                "kids": item.get("kids", []),
                "parent": item.get("parent"),
            },
        )
