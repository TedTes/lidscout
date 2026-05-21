"""OpenAI LLM provider client."""
from typing import Any

import requests

from infrastructure.llm.client import LLMClient


class OpenAIResponsesClient(LLMClient):
    """Calls OpenAI's Responses API for structured JSON output."""

    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_seconds: int = 30,
    ):
        cleaned_key = api_key.strip()
        if not cleaned_key:
            raise ValueError("api_key is required")
        self.api_key = cleaned_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate_structured_response(
        self,
        prompt: str,
        post_content: str,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        """Return a raw structured JSON model response."""
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": [
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": post_content,
                    },
                ],
                "text": {
                    "format": _response_format(response_schema),
                },
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return _response_text(response.json())


def _response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text

    parts: list[str] = []
    for output_item in payload.get("output", []):
        if not isinstance(output_item, dict):
            continue
        for content_item in output_item.get("content", []):
            if not isinstance(content_item, dict):
                continue
            text = content_item.get("text")
            if isinstance(text, str):
                parts.append(text)

    if not parts:
        raise RuntimeError("OpenAI response did not include output text")
    return "".join(parts)


def _response_format(response_schema: dict[str, Any] | None) -> dict[str, Any]:
    if response_schema is None:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "name": "signal_extraction_response",
        "schema": response_schema,
        "strict": True,
    }
