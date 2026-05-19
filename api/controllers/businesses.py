"""Business search API controller."""
from api.schemas import SearchCriteria, SearchResponse
from application.factory import ServiceFactory


async def search_businesses(criteria: SearchCriteria) -> SearchResponse:
    """Search businesses and shape the API response."""
    search_service = ServiceFactory.get_search_service()
    businesses = await search_service.search_businesses(criteria)
    query = f"{criteria.industry} near {criteria.location}"

    return SearchResponse(
        query=query,
        total_results=len(businesses),
        businesses=businesses,
    )
