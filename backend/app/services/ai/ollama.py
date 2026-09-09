"""Ollama AI provider."""

from typing import Any, Mapping

import httpx

from app.core.config import Settings, get_settings
from app.services.ai.base import AIProvider, AIProviderResponse, ProviderError
from app.services.ai.common import context_prompt


class OllamaProvider(AIProvider):
    """Analyze context using a locally hosted Ollama model."""

    provider_name = "ollama"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
        model: str | None = None,
    ) -> None:
        settings = settings or get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = settings.ai_timeout_seconds
        self._client = client or httpx.Client(timeout=self.timeout)

    def analyze(self, context: Mapping[str, Any]) -> AIProviderResponse:
        try:
            response = self._client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": context_prompt(context),
                    "stream": False,
                },
            )
        except httpx.TimeoutException:
            return self._error("timeout", "Ollama request timed out.", True)
        except httpx.ConnectError:
            return self._error(
                "connection_error",
                "Could not connect to Ollama.",
                True,
            )
        except httpx.RequestError:
            return self._error(
                "request_error",
                "Ollama request failed.",
                True,
            )

        if response.status_code >= 400:
            return self._error(
                "provider_error",
                f"Ollama returned HTTP {response.status_code}.",
                response.status_code >= 500 or response.status_code == 429,
            )
        try:
            content = response.json()["response"]
        except (ValueError, KeyError, TypeError):
            return self._error(
                "invalid_response",
                "Ollama returned an invalid response.",
                False,
            )
        if not isinstance(content, str):
            return self._error(
                "invalid_response",
                "Ollama response content was not text.",
                False,
            )
        return AIProviderResponse(
            provider=self.provider_name,
            model=self.model,
            success=True,
            content=content,
        )

    def _error(
        self,
        code: str,
        message: str,
        retryable: bool,
    ) -> AIProviderResponse:
        return AIProviderResponse(
            provider=self.provider_name,
            model=self.model,
            success=False,
            error=ProviderError(code, message, retryable),
        )
