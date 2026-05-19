"""Hacker News public activity adapter."""
from typing import Any

import requests

from domain.post import RawPost
from shared.config import get_settings


class HackerNewsActivityAdapter:
    """Fetches public Hacker News activity through the Firebase API."""

    base_url = "https://hacker-news.firebaseio.com/v0"
    search_url = "https://hn.algolia.com/api/v1/search"
    story_endpoints = {
        "ask": "askstories",
        "best": "beststories",
        "job": "jobstories",
        "new": "newstories",
        "show": "showstories",
        "top": "topstories",
    }

    def __init__(self):
        settings = get_settings()
        self.timeout_seconds = settings.request_timeout_seconds

    def fetch_posts(self, config: str = "top", limit: int = 25) -> list[RawPost]:
        """Fetch HN stories from a story type or search query."""
        normalized_config = config.strip()
        if normalized_config.lower().startswith("search:"):
            return self._search_posts(normalized_config.split(":", 1)[1].strip(), limit)
        return self._fetch_story_posts(normalized_config, limit)

    def _fetch_story_posts(self, story_type: str, limit: int) -> list[RawPost]:
        endpoint = self.story_endpoints.get(story_type.lower(), "topstories")
        ids_response = requests.get(
            f"{self.base_url}/{endpoint}.json",
            timeout=self.timeout_seconds,
        )
        ids_response.raise_for_status()
        item_ids = ids_response.json()[:limit]
        return [
            self._fetch_item(item_id)
            for item_id in item_ids
        ]

    def _search_posts(self, query: str, limit: int) -> list[RawPost]:
        response = requests.get(
            self.search_url,
            params={"query": query, "tags": "story", "hitsPerPage": limit},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        hits = response.json().get("hits", [])
        return [self._normalize_search_hit(hit) for hit in hits]

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

    def _normalize_search_hit(self, hit: dict[str, Any]) -> RawPost:
        source_id = str(hit.get("objectID") or "")
        return RawPost.create(
            source="hackernews",
            source_id=source_id,
            title=hit.get("title") or hit.get("story_title") or "",
            body=hit.get("story_text") or hit.get("comment_text") or "",
            author=hit.get("author"),
            url=hit.get("url") or f"https://news.ycombinator.com/item?id={source_id}",
            created_at=hit.get("created_at_i"),
            upvotes=hit.get("points"),
            comments_count=hit.get("num_comments"),
            metadata={
                "tags": hit.get("_tags", []),
            },
        )
