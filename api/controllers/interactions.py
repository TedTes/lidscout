"""Interaction extraction API controller."""
from api.schemas import InteractionExtractionRequest, InteractionExtractionResponse
from application.factory import ServiceFactory


async def extract_interactions(
    request: InteractionExtractionRequest,
) -> InteractionExtractionResponse:
    """Extract public interaction signals from request sources."""
    extraction_service = ServiceFactory.get_interaction_extraction_service()
    return await extraction_service.extract(request)
