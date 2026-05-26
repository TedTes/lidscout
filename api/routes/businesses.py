"""
API endpoints for business search.
Following Single Responsibility Principle - only handles HTTP routing.
"""
from fastapi import APIRouter, Depends, HTTPException
from api.controllers.businesses import search_businesses as search_businesses_controller
from api.routes.auth import get_current_user
from api.schemas import SearchCriteria, SearchResponse

router = APIRouter(prefix="/api/businesses", tags=["businesses"], dependencies=[Depends(get_current_user)])


@router.post("/search", response_model=SearchResponse)
async def search_businesses(criteria: SearchCriteria):
    """
    Search for businesses based on criteria.
    
    Args:
        criteria: Search criteria including industry, location, radius
        
    Returns:
        SearchResponse with list of businesses
    """
    try:
        return await search_businesses_controller(criteria)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "business-scraper-api"}
