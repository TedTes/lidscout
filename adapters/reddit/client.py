"""Reddit public activity adapter."""
from typing import Any

import requests

from domain.post import RawPost
from shared.config import get_settings


class RedditActivityAdapter:
    """Fetches public Reddit activity through Reddit's JSON endpoints."""

    def __init__(self):
        settings = get_settings()
        self.timeout_seconds = settings.request_timeout_seconds
        self.headers = {"User-Agent": settings.http_user_agent}

    def search_subreddit(self, subreddit: str, query: str, limit: int = 25) -> list[RawPost]:
        """Search a subreddit and return normalized raw posts."""
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

    def _normalize_post(self, post: dict[str, Any]) -> RawPost:
        permalink = post.get("permalink") or ""
        source_id = post.get("id") or permalink
        return RawPost.create(
            source="reddit",
            source_id=source_id,
            title=post.get("title") or "",
            body=post.get("selftext") or "",
            author=post.get("author"),
            url=f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink,
            created_at=post.get("created_utc"),
            upvotes=post.get("score"),
            comments_count=post.get("num_comments"),
            metadata={
                "subreddit": post.get("subreddit"),
                "permalink": permalink,
                "post_hint": post.get("post_hint"),
            },
        )
