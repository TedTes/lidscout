"""
Abstract interfaces for application services.
Following Dependency Inversion Principle - depend on abstractions.
"""
from abc import ABC, abstractmethod

from api.schemas import Business, InteractionExtractionRequest, InteractionExtractionResponse, SearchCriteria


class IBusinessSearchService(ABC):
    """Interface for business search operations."""
    
    @abstractmethod
    async def search_businesses(self, criteria: SearchCriteria) -> list[Business]:
        """
        Search for businesses based on criteria.
        
        Args:
            criteria: Search criteria including industry, location, radius
            
        Returns:
            List of Business objects matching the criteria
        """
        pass


class IInteractionExtractionService(ABC):
    """Interface for public interaction extraction operations."""

    @abstractmethod
    async def extract(self, request: InteractionExtractionRequest) -> InteractionExtractionResponse:
        """
        Extract normalized page JSON, comments, and negative signals.

        Args:
            request: Input URL or text sources

        Returns:
            Structured public interaction extraction response
        """
        pass
