"""LLM client boundary for future extraction enrichment."""
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Minimal LLM interface for signal enrichment."""

    @abstractmethod
    async def summarize(self, text: str) -> str:
        """Summarize text for reporting or enrichment."""
        raise NotImplementedError
