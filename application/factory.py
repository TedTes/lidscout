"""
Service factory for dependency injection.
Following Dependency Inversion Principle.
"""
from application.extraction.interaction_extractor import InteractionExtractorService
from application.ingestion.google_maps_scraper import PlaywrightScraperService
from application.interfaces import IBusinessSearchService, IInteractionExtractionService


class ServiceFactory:
    """Factory for creating service instances."""
    
    @staticmethod
    def get_search_service() -> IBusinessSearchService:
        """
        Get the business search service implementation.
        Can easily swap implementations here without changing dependent code.
        """
        return PlaywrightScraperService()

    @staticmethod
    def get_interaction_extraction_service() -> IInteractionExtractionService:
        """
        Get the public interaction extraction implementation.
        Can be swapped for an LLM-backed extractor without changing the API layer.
        """
        return InteractionExtractorService()
