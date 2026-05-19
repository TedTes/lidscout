"""
Page extraction service for research sources.
"""
import asyncio
import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

from api.schemas import ExtractedPage, PageSourceInput, PageStats
from shared.config import get_settings


@dataclass
class PageDocument:
    """Internal page representation with full text for analysis."""

    page: ExtractedPage
    text: str


class PageExtractorService:
    """Converts URLs or pasted text into normalized page text."""

    def __init__(self):
        settings = get_settings()
        self.timeout_seconds = settings.request_timeout_seconds
        self.headers = {
            "User-Agent": settings.http_user_agent,
        }

    async def extract(self, source: PageSourceInput, index: int) -> PageDocument:
        source_id = f"source-{index}"

        if source.source_type == "text":
            title = source.label or self._title_from_text(source.text or "")
            text = self._normalize_text(source.text or "")
            return self._build_document(source_id, source.label, source.url, title, text)

        html = await asyncio.to_thread(self._fetch_url, source.url or "")
        title, text = self._html_to_text(html)
        return self._build_document(source_id, source.label, source.url, title, text)

    def _fetch_url(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.text

    def _html_to_text(self, html: str) -> tuple[Optional[str], str]:
        soup = BeautifulSoup(html, "lxml")

        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        title = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        main = soup.find("main") or soup.body or soup
        text = main.get_text(separator="\n", strip=True)
        return title, self._normalize_text(text)

    def _build_document(
        self,
        source_id: str,
        label: Optional[str],
        source_url: Optional[str],
        title: Optional[str],
        text: str,
    ) -> PageDocument:
        display_label = label or title or source_url or source_id
        lines = [line for line in text.splitlines() if line.strip()]
        page = ExtractedPage(
            source_id=source_id,
            label=display_label[:160],
            source_url=source_url,
            title=title,
            content={
                "text_excerpt": text[:4000],
                "lines": lines[:200],
            },
            stats=PageStats(
                line_count=len(lines),
                word_count=len(text.split()),
                character_count=len(text),
            ),
        )
        return PageDocument(page=page, text=text)

    def _normalize_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        compact_lines = [line for line in lines if line]
        compact = "\n".join(compact_lines)
        return re.sub(r"[ \t]+", " ", compact).strip()

    def _title_from_text(self, text: str) -> Optional[str]:
        for line in text.splitlines():
            line = line.strip()
            if line:
                return line[:120]
        return None
