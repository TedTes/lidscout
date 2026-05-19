"""Persistence boundaries for extracted signal data."""
from abc import ABC, abstractmethod

from api.schemas import InteractionExtractionResponse


class SignalRepository(ABC):
    """Storage interface for extraction results."""

    @abstractmethod
    def save_extraction(self, response: InteractionExtractionResponse) -> None:
        """Persist an extraction response."""
        raise NotImplementedError
