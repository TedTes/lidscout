"""Reddit public activity adapter."""
from dataclasses import dataclass
from typing import Any

import requests

from shared.config import get_settings


@dataclass(frozen=True)
class RedditActivity:
    """Normalized Reddit post/comment activity."""

    source_id: str
    title: str
    text: str
    url: str
    score: int | None = None


class RedditActivityAdapter:
    """Fetches public Reddit activity through Reddit's JSON endpoints."""

    def __init__(self):
        settings = get_settings()
        self.timeout_seconds = settings.request_timeout_seconds
        self.headers = {"User-Agent": settings.http_user_agent}

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25) -> list[RedditActivity]:
        """Search a subreddit and return normalized activity records."""
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        response = requests.get(
            url,
            params={"q": query, "restrict_sr": 1, "limit": limit},
            headers=self.headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        children = response.json().get("data", {}).get("children", [])
        return [self._normalize_post(child.get("data", {})) for child in children]

    def _normalize_post(self, post: dict[str, Any]) -> RedditActivity:
        permalink = post.get("permalink") or ""
        return RedditActivity(
            source_id=post.get("id") or permalink,
            title=post.get("title") or "",
            text=post.get("selftext") or "",
            url=f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink,
            score=post.get("score"),
        )
