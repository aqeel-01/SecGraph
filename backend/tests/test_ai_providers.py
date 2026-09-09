import json

import httpx

from app.core.config import Settings
from app.services.ai.groq import GroqProvider
from app.services.ai.ollama import OllamaProvider

CONTEXT = {
    "endpoint": {"method": "GET", "path": "/users/{id}"},
    "relevant_source": "def get_user(user_id): ...",
}


def test_ollama_provider_uses_configured_model_and_context() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url == "http://ollama.test/api/generate"
        assert payload["model"] == "deepseek-r1:1.5b"
        assert "users/{id}" in payload["prompt"]
        assert "security analysis" in payload["prompt"]
        assert "Do not invent code behavior" in payload["prompt"]
        assert "valid JSON" in payload["prompt"]
        assert payload["stream"] is False
        return httpx.Response(200, json={"response": "Ollama analysis"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OllamaProvider(
        Settings(ollama_base_url="http://ollama.test"),
        client=client,
    )

    result = provider.analyze(CONTEXT)

    assert result.success is True
    assert result.content == "Ollama analysis"
    assert result.error is None


def test_groq_provider_sends_authorized_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer test-key"
        assert payload["model"] == "deepseek-r1:7b"
        assert "relevant_source" in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Groq analysis"}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GroqProvider(
        Settings(groq_api_key="test-key"),
        client=client,
    )

    result = provider.analyze(CONTEXT)

    assert result.success is True
    assert result.content == "Groq analysis"


def test_groq_without_api_key_returns_structured_error() -> None:
    provider = GroqProvider(Settings(groq_api_key=None))

    result = provider.analyze(CONTEXT)

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "configuration_error"
    assert result.error.retryable is False


def test_ollama_timeout_returns_retryable_structured_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OllamaProvider(client=client)

    result = provider.analyze(CONTEXT)

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "timeout"
    assert result.error.retryable is True


def test_groq_connection_error_returns_structured_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GroqProvider(
        Settings(groq_api_key="test-key"),
        client=client,
    )

    result = provider.analyze(CONTEXT)

    assert result.success is False
    assert result.error is not None
    assert result.error.code == "connection_error"
    assert result.error.retryable is True
