"""OpenAI embedding provider client."""
from typing import Any

import requests

from infrastructure.llm.embedding_client import EmbeddingClient


class OpenAIEmbeddingClient(EmbeddingClient):
    """Calls OpenAI's Embeddings API for signal text vectors."""

    endpoint = "https://api.openai.com/v1/embeddings"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "text-embedding-3-small",
        timeout_seconds: int = 30,
    ):
        cleaned_key = api_key.strip()
        if not cleaned_key:
            raise ValueError("api_key is required")
        self.api_key = cleaned_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def _generate_embedding(self, signal_text: str) -> list[float]:
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": signal_text,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return _embedding_from_response(response.json())


def _embedding_from_response(payload: dict[str, Any]) -> list[float]:
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("OpenAI embedding response did not include data")

    first_item = data[0]
    if not isinstance(first_item, dict):
        raise RuntimeError("OpenAI embedding response data item is invalid")

    embedding = first_item.get("embedding")
    if not isinstance(embedding, list):
        raise RuntimeError("OpenAI embedding response did not include an embedding")

    return [float(value) for value in embedding]
