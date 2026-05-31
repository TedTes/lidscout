"""Application services for synthesized opportunities."""
from application.opportunity.service import (
    OpportunitySynthesisContext,
    OpportunitySynthesisResult,
    OpportunitySynthesisService,
    merge_near_duplicate_opportunities,
)

__all__ = [
    "OpportunitySynthesisContext",
    "OpportunitySynthesisResult",
    "OpportunitySynthesisService",
    "merge_near_duplicate_opportunities",
]
