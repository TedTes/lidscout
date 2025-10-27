"""
Service factory for dependency injection.
Following Dependency Inversion Principle.
"""
from app.services.interfaces import IBusinessSearchService
from app.services.playwright_scraper import PlaywrightScraperService


class ServiceFactory:
    """Factory for creating service instances."""
    
    @staticmethod
    def get_search_service() -> IBusinessSearchService:
        """
        Get the business search service implementation.
        Can easily swap implementations here without changing dependent code.
        """
        return PlaywrightScraperService()