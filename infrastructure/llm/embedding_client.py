"""Embedding client interface for signal text vectors."""
from abc import ABC, abstractmethod


class EmbeddingClient(ABC):
    """Boundary for embedding providers used by clustering workflows."""

    def generate_embedding(self, signal_text: str) -> list[float]:
        """Generate a vector embedding for signal text."""
        normalized_text = signal_text.strip()
        if not normalized_text:
            raise ValueError("signal_text is required")

        embedding = self._generate_embedding(normalized_text)
        if not embedding:
            raise ValueError("embedding must not be empty")
        return [float(value) for value in embedding]

    @abstractmethod
    def _generate_embedding(self, signal_text: str) -> list[float]:
        """Provider-specific embedding generation."""
        raise NotImplementedError
