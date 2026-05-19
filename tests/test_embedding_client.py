import unittest

from infrastructure.llm import EmbeddingClient


class FakeEmbeddingClient(EmbeddingClient):
    def __init__(self):
        self.calls: list[str] = []

    def _generate_embedding(self, signal_text: str) -> list[float]:
        self.calls.append(signal_text)
        return [1, 0.5, "0.25"]


class EmptyEmbeddingClient(EmbeddingClient):
    def _generate_embedding(self, signal_text: str) -> list[float]:
        return []


class EmbeddingClientTests(unittest.TestCase):
    def test_generates_embedding_for_normalized_signal_text(self):
        client = FakeEmbeddingClient()

        embedding = client.generate_embedding("  Manual reporting is slow  ")

        self.assertEqual(client.calls, ["Manual reporting is slow"])
        self.assertEqual(embedding, [1.0, 0.5, 0.25])

    def test_rejects_empty_signal_text(self):
        client = FakeEmbeddingClient()

        with self.assertRaises(ValueError):
            client.generate_embedding("   ")

    def test_rejects_empty_embedding(self):
        client = EmptyEmbeddingClient()

        with self.assertRaises(ValueError):
            client.generate_embedding("Manual reporting is slow")


if __name__ == "__main__":
    unittest.main()
