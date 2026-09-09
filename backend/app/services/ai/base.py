"""Common AI provider interface and response types."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ProviderError:
    """Safe, structured provider failure information."""

    code: str
    message: str
    retryable: bool


@dataclass(frozen=True)
class AIProviderResponse:
    """Normalized result returned by every AI provider."""

    provider: str
    model: str
    success: bool
    content: str | None = None
    confidence: float | None = None
    error: ProviderError | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable response."""

        return asdict(self)


class AIProvider(ABC):
    """Interface implemented by all supported AI providers."""

    provider_name: str

    @abstractmethod
    def analyze(self, context: Mapping[str, Any]) -> AIProviderResponse:
        """Analyze a compact security context."""
