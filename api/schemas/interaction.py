"""
Data models for extracting public interaction signals from review pages.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class PageSourceInput(BaseModel):
    """A URL or pasted page text to extract public interactions from."""

    source_type: Literal["url", "text"] = "url"
    url: Optional[str] = Field(default=None, description="Public review page URL to fetch")
    text: Optional[str] = Field(default=None, description="Raw pasted page text or review excerpts")
    label: Optional[str] = Field(default=None, description="Human-readable source label")

    @model_validator(mode="after")
    def validate_source(self) -> "PageSourceInput":
        if self.source_type == "url" and not self.url:
            raise ValueError("url is required when source_type is 'url'")
        if self.source_type == "text" and not self.text:
            raise ValueError("text is required when source_type is 'text'")
        return self


class InteractionExtractionRequest(BaseModel):
    """Request to normalize pages and extract public review interactions."""

    sources: list[PageSourceInput] = Field(..., min_length=1, max_length=25)


class PageStats(BaseModel):
    """Basic metadata about extracted page text."""

    line_count: int
    word_count: int
    character_count: int


class ExtractedPage(BaseModel):
    """Normalized page JSON produced before interaction extraction."""

    source_id: str
    label: str
    source_url: Optional[str] = None
    title: Optional[str] = None
    content: dict
    stats: PageStats


class PublicInteraction(BaseModel):
    """A review, comment, or public feedback snippet extracted from a page."""

    interaction_id: str
    source_id: str
    body: str
    title: Optional[str] = None
    author: Optional[str] = None
    rating: Optional[float] = None
    published_at: Optional[str] = None
    sentiment: Literal["negative", "neutral", "positive", "mixed", "unknown"]
    topics: list[str] = Field(default_factory=list)
    evidence_terms: list[str] = Field(default_factory=list)


class NegativeSignal(BaseModel):
    """Grouped negative signal derived from extracted public interactions."""

    theme: str
    frequency: int
    severity: Literal["low", "medium", "high"]
    interaction_ids: list[str]
    excerpts: list[str]


class InteractionExtractionResponse(BaseModel):
    """Response containing normalized page JSON and extracted interaction signals."""

    total_sources: int
    pages: list[ExtractedPage]
    interactions: list[PublicInteraction]
    negative_comments: list[PublicInteraction]
    negative_signals: list[NegativeSignal]
