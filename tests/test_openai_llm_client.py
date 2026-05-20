import unittest
from unittest.mock import Mock, patch

from infrastructure.llm import OpenAIResponsesClient


class OpenAIResponsesClientTests(unittest.TestCase):
    def test_generates_structured_response(self):
        response = Mock()
        response.json.return_value = {"output_text": '{"has_signal": false}'}
        response.raise_for_status.return_value = None

        with patch("infrastructure.llm.openai_client.requests.post", return_value=response) as post:
            client = OpenAIResponsesClient(
                api_key="test-key",
                model="test-model",
                timeout_seconds=12,
            )

            result = client.generate_structured_response(
                "Return JSON",
                "source: reddit\ntitle: pain",
            )

        self.assertEqual(result, '{"has_signal": false}')
        post.assert_called_once()
        call = post.call_args
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(call.kwargs["json"]["model"], "test-model")
        self.assertEqual(call.kwargs["json"]["text"]["format"]["type"], "json_object")
        self.assertEqual(call.kwargs["timeout"], 12)

    def test_reads_nested_output_text(self):
        response = Mock()
        response.json.return_value = {
            "output": [
                {
                    "content": [
                        {"text": '{"has_signal": true}'},
                    ]
                }
            ]
        }
        response.raise_for_status.return_value = None

        with patch("infrastructure.llm.openai_client.requests.post", return_value=response):
            client = OpenAIResponsesClient(api_key="test-key")

            result = client.generate_structured_response("Return JSON", "post")

        self.assertEqual(result, '{"has_signal": true}')

    def test_rejects_blank_api_key(self):
        with self.assertRaises(ValueError):
            OpenAIResponsesClient(api_key=" ")


if __name__ == "__main__":
    unittest.main()
