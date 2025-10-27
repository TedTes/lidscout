"""
Data models for business information.
Following Single Responsibility Principle - only defines data structure.
"""
from pydantic import BaseModel, Field
from typing import Optional


class Business(BaseModel):
    """Business entity model."""
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None


class SearchCriteria(BaseModel):
    """Search criteria for finding businesses."""
    industry: str = Field(..., description="Business industry/type (e.g., 'restaurants', 'plumbers')")
    location: str = Field(..., description="Location (e.g., 'New York, NY')")
    radius_km: Optional[int] = Field(default=10, description="Search radius in kilometers")
    max_results: Optional[int] = Field(default=20, ge=1, le=100, description="Maximum number of results")


class SearchResponse(BaseModel):
    """Response model for business search."""
    query: str
    total_results: int
    businesses: list[Business]