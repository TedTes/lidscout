"""Background jobs for signal detection workflows."""
from api.schemas import InteractionExtractionRequest, InteractionExtractionResponse
from application.factory import ServiceFactory


async def extract_public_activity_signals(
    request: InteractionExtractionRequest,
) -> InteractionExtractionResponse:
    """Run the extraction pipeline for supplied public activity sources."""
    extractor = ServiceFactory.get_interaction_extraction_service()
    return await extractor.extract(request)
