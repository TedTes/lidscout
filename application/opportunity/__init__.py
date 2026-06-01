"""Application services for synthesized opportunities."""
from application.opportunity.service import (
    ClusterQualification,
    OpportunitySynthesisContext,
    OpportunitySynthesisResult,
    OpportunitySynthesisService,
    merge_near_duplicate_opportunities,
    qualify_cluster_for_opportunity,
)

__all__ = [
    "ClusterQualification",
    "OpportunitySynthesisContext",
    "OpportunitySynthesisResult",
    "OpportunitySynthesisService",
    "merge_near_duplicate_opportunities",
    "qualify_cluster_for_opportunity",
]
