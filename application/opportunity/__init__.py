"""Application services for synthesized opportunities."""
from application.opportunity.evaluation import (
    OpportunityQualificationReport,
    evaluate_opportunity_qualification,
)
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
    "OpportunityQualificationReport",
    "OpportunitySynthesisContext",
    "OpportunitySynthesisResult",
    "OpportunitySynthesisService",
    "evaluate_opportunity_qualification",
    "merge_near_duplicate_opportunities",
    "qualify_cluster_for_opportunity",
]
