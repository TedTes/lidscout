import unittest
from unittest.mock import Mock, patch

from infrastructure.llm import OpenAIEmbeddingClient


class OpenAIEmbeddingClientTests(unittest.TestCase):
    def test_generates_embedding(self):
        response = Mock()
        response.json.return_value = {"data": [{"embedding": [0.1, "-0.2", 3]}]}
        response.raise_for_status.return_value = None

        with patch(
            "infrastructure.llm.openai_embedding_client.requests.post",
            return_value=response,
        ) as post:
            client = OpenAIEmbeddingClient(
                api_key="test-key",
                model="test-embedding-model",
                timeout_seconds=12,
            )

            result = client.generate_embedding("Need better invoice tracking")

        self.assertEqual(result, [0.1, -0.2, 3.0])
        post.assert_called_once()
        call = post.call_args
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(call.kwargs["json"]["model"], "test-embedding-model")
        self.assertEqual(call.kwargs["json"]["input"], "Need better invoice tracking")
        self.assertEqual(call.kwargs["timeout"], 12)

    def test_rejects_blank_api_key(self):
        with self.assertRaises(ValueError):
            OpenAIEmbeddingClient(api_key=" ")

    def test_rejects_missing_embedding(self):
        response = Mock()
        response.json.return_value = {"data": [{}]}
        response.raise_for_status.return_value = None

        with patch(
            "infrastructure.llm.openai_embedding_client.requests.post",
            return_value=response,
        ):
            client = OpenAIEmbeddingClient(api_key="test-key")

            with self.assertRaises(RuntimeError):
                client.generate_embedding("Signal text")


if __name__ == "__main__":
    unittest.main()
