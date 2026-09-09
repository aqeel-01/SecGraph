from typing import Any, Mapping

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.models import AIAnalysis, Project, SecurityFinding
from app.services.ai.base import AIProvider, AIProviderResponse
from app.services.ai.explanation import (
    AIExplanationService,
    validate_ai_explanation,
)
from app.services.ai.router import AIRouter


VALID_RESPONSE = """{
  "severity": "high",
  "confidence": 0.91,
  "explanation": "The route may lack an access control check.",
  "potential_attack": "An attacker could request another user's resource.",
  "impact": "Unauthorized resource access is possible if the suspicion is confirmed.",
  "suggested_fix": "Validate resource ownership before returning it."
}"""


class FakeExplanationProvider(AIProvider):
    provider_name = "ollama"

    def __init__(self, content: str) -> None:
        self.content = content

    def analyze(self, context: Mapping[str, Any]) -> AIProviderResponse:
        return AIProviderResponse(
            provider=self.provider_name,
            model="deepseek-r1:1.5b",
            success=True,
            content=self.content,
        )


def test_valid_ai_response_is_validated() -> None:
    result = validate_ai_explanation(VALID_RESPONSE)

    assert result.valid is True
    assert result.explanation is not None
    assert result.explanation.severity == "high"
    assert result.explanation.confidence == 0.91


def test_malformed_ai_response_is_rejected_safely() -> None:
    result = validate_ai_explanation('{"severity": "high"}')

    assert result.valid is False
    assert result.explanation is None
    assert result.error is not None


def test_invalid_ai_response_is_persisted_without_being_accepted() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    router = AIRouter(
        Settings(),
        ollama_provider=FakeExplanationProvider('{"severity": "high"}'),
        ollama_complex_provider=FakeExplanationProvider('{"severity": "high"}'),
    )
    service = AIExplanationService(router)

    with Session(engine) as session:
        project = Project(
            name="Explanation test",
            source_type="upload",
            storage_path="storage/explanation-test",
        )
        session.add(project)
        session.flush()
        finding = SecurityFinding(
            project_id=project.id,
            rule_id="possible-idor",
            title="Possible IDOR",
            severity="high",
            confidence=0.65,
            file="main.py",
            line=10,
            endpoint="GET /users/{id}",
            description="Possible ownership issue.",
            evidence="No ownership check found.",
            remediation="Validate ownership.",
            context_package={"relevant_source": "compact"},
        )
        session.add(finding)
        session.flush()

        result = service.explain(finding, None, session)
        session.commit()

        stored = session.query(AIAnalysis).one()
        assert result.status == "invalid_response"
        assert stored.explanation_status == "invalid_response"
        assert stored.structured_output is None
        assert stored.validation_error


def test_valid_ai_explanation_is_stored_as_structured_output() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    router = AIRouter(
        Settings(),
        ollama_provider=FakeExplanationProvider(VALID_RESPONSE),
        ollama_complex_provider=FakeExplanationProvider(VALID_RESPONSE),
    )
    service = AIExplanationService(router)

    with Session(engine) as session:
        project = Project(
            name="Valid explanation test",
            source_type="upload",
            storage_path="storage/valid-explanation-test",
        )
        session.add(project)
        session.flush()
        finding = SecurityFinding(
            project_id=project.id,
            rule_id="missing-authentication",
            title="Missing authentication",
            severity="medium",
            confidence=0.8,
            file="main.py",
            line=2,
            description="Possible missing authentication.",
            evidence="@app.get('/')",
            remediation="Review authentication.",
            context_package={"endpoint": {"path": "/"}},
        )
        session.add(finding)
        session.flush()

        result = service.explain(finding, {"endpoint": {"path": "/"}}, session)
        session.commit()

        stored = session.query(AIAnalysis).one()
        assert result.status == "validated"
        assert stored.explanation_status == "validated"
        assert stored.structured_output["severity"] == "high"
        assert stored.ai_confidence == 0.91
