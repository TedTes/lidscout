"""
API endpoints for public interaction extraction.
"""
from fastapi import APIRouter, Depends, HTTPException

from api.controllers.interactions import extract_interactions as extract_interactions_controller
from api.routes.auth import get_current_user
from api.schemas import InteractionExtractionRequest, InteractionExtractionResponse

router = APIRouter(prefix="/api/interactions", tags=["interactions"], dependencies=[Depends(get_current_user)])


@router.post("/extract", response_model=InteractionExtractionResponse)
async def extract_interactions(request: InteractionExtractionRequest):
    """
    Normalize public review pages and extract comments, negative comments, and signals.
    """
    try:
        return await extract_interactions_controller(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interaction extraction failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "interaction-extraction-api"}
