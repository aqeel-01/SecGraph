"""Configurable AI provider routing with fallback behavior."""

from dataclasses import asdict, dataclass
import json
import re
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import AIAnalysis, SecurityFinding
from app.services.ai.base import AIProvider, AIProviderResponse
from app.services.ai.groq import GroqProvider
from app.services.ai.ollama import OllamaProvider
from app.services.rules.base import Finding

CONFIDENCE_PATTERN = re.compile(
    r"""["'](?:ai_)?confidence["']\s*:\s*([01](?:\.\d+)?)""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RoutingDecision:
    """The provider-independent result of routing policy evaluation."""

    decision: str
    reason: str
    provider: str | None
    model: str | None


@dataclass(frozen=True)
class RoutingResult:
    """Normalized routing and provider outcome."""

    decision: str
    status: str
    reason: str
    provider: str | None
    model: str | None
    content: str | None
    ai_confidence: float | None
    error: dict[str, Any] | None
    attempts: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable routing result."""

        return asdict(self)


class AIRouter:
    """Choose a provider without exposing repository contents to it."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        ollama_provider: AIProvider | None = None,
        ollama_complex_provider: AIProvider | None = None,
        groq_provider: AIProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.ollama_provider = ollama_provider or OllamaProvider(self.settings)
        self.ollama_complex_provider = (
            ollama_complex_provider
            or OllamaProvider(
                self.settings,
                model=self.settings.ollama_complex_model,
            )
        )
        self.groq_provider = groq_provider or GroqProvider(self.settings)

    def decide(self, finding: Finding) -> RoutingDecision:
        """Choose static-only, simple-local, or complex analysis."""

        if not self.settings.ai_routing_enabled:
            return RoutingDecision(
                "static_only",
                "AI routing is disabled by configuration.",
                None,
                None,
            )
        if finding.confidence >= self.settings.ai_static_confidence_threshold:
            return RoutingDecision(
                "static_only",
                "Deterministic confidence is high enough to avoid an AI call.",
                None,
                None,
            )

        complex_rules = {
            rule_id.strip()
            for rule_id in self.settings.ai_complex_rule_ids.split(",")
            if rule_id.strip()
        }
        is_complex = (
            finding.rule_id in complex_rules
            or finding.confidence < self.settings.ai_simple_confidence_threshold
        )
        provider_mode = self.settings.ai_provider.strip().lower()
        if provider_mode == "ollama":
            return RoutingDecision(
                "complex" if is_complex else "simple",
                "AI_PROVIDER is configured for local Ollama analysis.",
                "ollama",
                (
                    self.settings.ollama_complex_model
                    if is_complex
                    else self.settings.ollama_model
                ),
            )
        if provider_mode == "groq":
            return RoutingDecision(
                "complex" if is_complex else "simple",
                "AI_PROVIDER is configured for Groq analysis.",
                "groq",
                self.settings.groq_model,
            )
        if not is_complex:
            return RoutingDecision(
                "simple",
                "Finding is suitable for lightweight local analysis.",
                "ollama",
                self.settings.ollama_model,
            )
        if self.settings.ai_prefer_groq_for_complex and self.settings.groq_api_key:
            return RoutingDecision(
                "complex",
                "Finding is configured for complex cloud analysis.",
                "groq",
                self.settings.groq_model,
            )
        return RoutingDecision(
            "complex",
            "Finding requires larger-model analysis using local fallback.",
            "ollama",
            self.settings.ollama_complex_model,
        )

    def analyze(
        self,
        finding: Finding,
        context: Mapping[str, Any],
    ) -> RoutingResult:
        """Route a finding using only the supplied compact context."""

        decision = self.decide(finding)
        if decision.decision == "static_only":
            return RoutingResult(
                decision=decision.decision,
                status="static_only",
                reason=decision.reason,
                provider=None,
                model=None,
                content=None,
                ai_confidence=None,
                error=None,
                attempts=[],
            )

        provider = self._provider_for(decision)
        attempts: list[dict[str, Any]] = []
        response = provider.analyze(context)
        attempts.append(self._attempt(response))

        if not response.success and decision.provider == "groq":
            fallback = self.ollama_complex_provider
            fallback_response = fallback.analyze(context)
            attempts.append(self._attempt(fallback_response))
            response = fallback_response

        confidence = (
            response.confidence
            if response.confidence is not None
            else self._extract_confidence(response.content)
        )
        error = (
            asdict(response.error)
            if response.error is not None
            else None
        )
        return RoutingResult(
            decision=decision.decision,
            status="completed" if response.success else "failed",
            reason=decision.reason,
            provider=response.provider if response.success else None,
            model=response.model if response.success else None,
            content=response.content if response.success else None,
            ai_confidence=confidence,
            error=error,
            attempts=attempts,
        )

    def route_and_persist(
        self,
        finding: SecurityFinding,
        context: Mapping[str, Any] | None,
        db: Session,
    ) -> RoutingResult:
        """Route one persisted finding and record the result."""

        normalized = Finding(
            rule_id=finding.rule_id,
            title=finding.title,
            severity=finding.severity,
            confidence=finding.confidence,
            file=finding.file,
            line=finding.line,
            endpoint=finding.endpoint,
            description=finding.description,
            evidence=finding.evidence,
            remediation=finding.remediation,
            project_file_id=finding.project_file_id,
            route_id=finding.route_id,
        )
        result = self.analyze(
            normalized,
            context if context is not None else finding.context_package,
        )
        db.add(
            AIAnalysis(
                finding_id=finding.id,
                decision=result.decision,
                status=result.status,
                provider=result.provider,
                model=result.model,
                ai_confidence=result.ai_confidence,
                response=result.content,
                error_code=result.error["code"] if result.error else None,
                error_message=result.error["message"] if result.error else None,
                attempts=result.attempts,
            )
        )
        return result

    def _provider_for(self, decision: RoutingDecision) -> AIProvider:
        if decision.provider == "groq":
            return self.groq_provider
        if decision.decision == "complex":
            return self.ollama_complex_provider
        return self.ollama_provider

    @staticmethod
    def _extract_confidence(content: str | None) -> float | None:
        if not content:
            return None
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            value = parsed.get("confidence", parsed.get("ai_confidence"))
            if isinstance(value, (int, float)):
                return max(0.0, min(1.0, float(value)))
        match = CONFIDENCE_PATTERN.search(content)
        if match:
            return max(0.0, min(1.0, float(match.group(1))))
        return None

    @staticmethod
    def _attempt(response: AIProviderResponse) -> dict[str, Any]:
        return {
            "provider": response.provider,
            "model": response.model,
            "success": response.success,
            "error_code": response.error.code if response.error else None,
        }
