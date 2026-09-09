"""Groq AI provider."""

from typing import Any, Mapping

import httpx

from app.core.config import Settings, get_settings
from app.services.ai.base import AIProvider, AIProviderResponse, ProviderError
from app.services.ai.common import context_prompt

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(AIProvider):
    """Analyze context using the Groq OpenAI-compatible API."""

    provider_name = "groq"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        settings = settings or get_settings()
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self.timeout = settings.ai_timeout_seconds
        self._client = client or httpx.Client(timeout=self.timeout)

    def analyze(self, context: Mapping[str, Any]) -> AIProviderResponse:
        if not self.api_key:
            return self._error(
                "configuration_error",
                "Groq API key is not configured.",
                False,
            )
        try:
            response = self._client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": context_prompt(context),
                        }
                    ],
                },
            )
        except httpx.TimeoutException:
            return self._error("timeout", "Groq request timed out.", True)
        except httpx.ConnectError:
            return self._error(
                "connection_error",
                "Could not connect to Groq.",
                True,
            )
        except httpx.RequestError:
            return self._error("request_error", "Groq request failed.", True)

        if response.status_code >= 400:
            return self._error(
                "provider_error",
                f"Groq returned HTTP {response.status_code}.",
                response.status_code >= 500 or response.status_code == 429,
            )
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            return self._error(
                "invalid_response",
                "Groq returned an invalid response.",
                False,
            )
        if not isinstance(content, str):
            return self._error(
                "invalid_response",
                "Groq response content was not text.",
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
