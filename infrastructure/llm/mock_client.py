"""Mock LLM client for tests."""
from dataclasses import dataclass, field
from typing import Any

from infrastructure.llm.client import LLMClient


@dataclass
class MockLLMClient(LLMClient):
    """Returns a fixed structured response and records calls."""

    response: str
    calls: list[tuple[str, str, dict[str, Any] | None]] = field(default_factory=list)

    def generate_structured_response(
        self,
        prompt: str,
        post_content: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        self.calls.append((prompt, post_content, response_schema))
        return self.response
