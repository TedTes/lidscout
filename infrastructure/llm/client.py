"""LLM client interface for structured model responses."""
from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """Boundary for LLM providers used by application services."""

    @abstractmethod
    def generate_structured_response(
        self,
        prompt: str,
        post_content: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        """Return a raw structured model response for the prompt and post content."""
        raise NotImplementedError
