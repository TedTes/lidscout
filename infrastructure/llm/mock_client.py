"""Mock LLM client for tests."""
from dataclasses import dataclass, field

from infrastructure.llm.client import LLMClient


@dataclass
class MockLLMClient(LLMClient):
    """Returns a fixed structured response and records calls."""

    response: str
    calls: list[tuple[str, str]] = field(default_factory=list)

    def generate_structured_response(self, prompt: str, post_content: str) -> str:
        self.calls.append((prompt, post_content))
        return self.response
