"""
API endpoints for business search.
Following Single Responsibility Principle - only handles HTTP routing.
"""
from fastapi import APIRouter, HTTPException
from app.models import SearchCriteria, SearchResponse, Business
from app.services.factory import ServiceFactory

router = APIRouter(prefix="/api/businesses", tags=["businesses"])


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
        # Get service from factory 
        search_service = ServiceFactory.get_search_service()
        
        # Execute search
        businesses = await search_service.search_businesses(criteria)
        
        # Build query string for response
        query = f"{criteria.industry} near {criteria.location}"
        
        return SearchResponse(
            query=query,
            total_results=len(businesses),
            businesses=businesses
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "business-scraper-api"}