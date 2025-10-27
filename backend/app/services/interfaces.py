"""
Abstract interface for business search service.
Following Dependency Inversion Principle - depend on abstractions.
"""
from abc import ABC, abstractmethod
from app.models import SearchCriteria, Business


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