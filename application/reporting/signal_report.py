"""Helpers for summarizing detected signal output."""
from api.schemas import InteractionExtractionResponse


def summarize_extraction(response: InteractionExtractionResponse) -> dict[str, int]:
    """Return compact counts for downstream reports."""
    return {
        "sources": response.total_sources,
        "interactions": len(response.interactions),
        "negative_comments": len(response.negative_comments),
        "negative_signals": len(response.negative_signals),
    }
