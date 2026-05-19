"""Hacker News public activity adapter."""
from dataclasses import dataclass
from typing import Any

import requests

from shared.config import get_settings


@dataclass(frozen=True)
class HackerNewsActivity:
    """Normalized Hacker News activity."""

    source_id: str
    title: str
    text: str
    url: str
    score: int | None = None


class HackerNewsActivityAdapter:
    """Fetches public Hacker News activity through the Firebase API."""

    base_url = "https://hacker-news.firebaseio.com/v0"

    def __init__(self):
        settings = get_settings()
        self.timeout_seconds = settings.request_timeout_seconds

    def top_items(self, limit: int = 25) -> list[HackerNewsActivity]:
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

    def _fetch_item(self, item_id: int) -> HackerNewsActivity:
        response = requests.get(
            f"{self.base_url}/item/{item_id}.json",
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        item: dict[str, Any] = response.json()
        return HackerNewsActivity(
            source_id=str(item.get("id") or item_id),
            title=item.get("title") or "",
            text=item.get("text") or "",
            url=item.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
            score=item.get("score"),
        )
