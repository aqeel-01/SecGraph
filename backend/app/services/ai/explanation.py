"""Validated AI security explanation generation."""

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.models import AIAnalysis, SecurityFinding
from app.services.ai.router import AIRouter, RoutingResult
from app.services.rules.base import Finding


class AIExplanation(BaseModel):
    """Strict structured output expected from an AI provider."""

    model_config = ConfigDict(extra="forbid")

    severity: Literal["critical", "high", "medium", "low", "informational"]
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1)
    potential_attack: str = Field(min_length=1)
    impact: str = Field(min_length=1)
    suggested_fix: str = Field(min_length=1)


@dataclass(frozen=True)
class ExplanationValidation:
    """Safe validation result for raw provider content."""

    valid: bool
    explanation: AIExplanation | None
    error: str | None


@dataclass(frozen=True)
class ExplanationResult:
    """Complete routing, validation, and persistence-ready outcome."""

    routing: RoutingResult
    status: str
    explanation: AIExplanation | None
    validation_error: str | None


def validate_ai_explanation(content: str | None) -> ExplanationValidation:
    """Parse and validate provider output without allowing exceptions out."""

    if not content or not content.strip():
        return ExplanationValidation(False, None, "AI response was empty.")

    payload = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, re.DOTALL)
    if fenced:
        payload = fenced.group(1)
    try:
        data = json.loads(payload)
        explanation = AIExplanation.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        return ExplanationValidation(
            False,
            None,
            f"AI response did not match the required schema: {exc}",
        )
    return ExplanationValidation(True, explanation, None)


class AIExplanationService:
    """Generate, validate, and persist explanations for eligible findings."""

    def __init__(self, router: AIRouter | None = None) -> None:
        self.router = router or AIRouter()

    def explain(
        self,
        finding: SecurityFinding,
        context: Mapping[str, Any] | None,
        db: Session,
    ) -> ExplanationResult:
        """Route one finding and persist only validated structured output."""

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
        routing = self.router.analyze(
            normalized,
            context if context is not None else finding.context_package,
        )

        if routing.status == "static_only":
            status = "static_only"
            validation = ExplanationValidation(True, None, None)
        elif routing.status != "completed":
            status = "provider_failed"
            validation = ExplanationValidation(
                False,
                None,
                routing.error.get("message")
                if routing.error
                else "AI provider failed.",
            )
        else:
            validation = validate_ai_explanation(routing.content)
            status = "validated" if validation.valid else "invalid_response"

        error = validation.error
        if error is None and routing.error is not None:
            error = routing.error.get("message")
        db.add(
            AIAnalysis(
                finding_id=finding.id,
                decision=routing.decision,
                status=routing.status,
                provider=routing.provider,
                model=routing.model,
                ai_confidence=(
                    validation.explanation.confidence
                    if validation.explanation is not None
                    else routing.ai_confidence
                ),
                response=routing.content,
                error_code=(
                    "invalid_response"
                    if status == "invalid_response"
                    else routing.error.get("code")
                    if routing.error
                    else None
                ),
                error_message=(
                    error
                    if status in {"invalid_response", "provider_failed"}
                    else None
                ),
                explanation_status=status,
                structured_output=(
                    validation.explanation.model_dump()
                    if validation.explanation is not None
                    else None
                ),
                validation_error=validation.error,
                attempts=routing.attempts,
            )
        )
        return ExplanationResult(
            routing=routing,
            status=status,
            explanation=validation.explanation,
            validation_error=validation.error,
        )
