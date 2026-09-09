from typing import Any, Mapping

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.models import AIAnalysis, Project, SecurityFinding
from app.services.ai.base import AIProvider, AIProviderResponse, ProviderError
from app.services.ai.router import AIRouter
from app.services.rules.base import Finding


class FakeProvider(AIProvider):
    def __init__(self, name: str, model: str, response: AIProviderResponse) -> None:
        self.provider_name = name
        self.model = model
        self.response = response
        self.calls: list[Mapping[str, Any]] = []

    def analyze(self, context: Mapping[str, Any]) -> AIProviderResponse:
        self.calls.append(context)
        return self.response


def make_finding(
    rule_id: str = "missing-authentication",
    confidence: float = 0.8,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        title="Test finding",
        severity="medium",
        confidence=confidence,
        file="main.py",
        line=10,
        endpoint="GET /users",
        description="Description",
        evidence="Evidence",
        remediation="Remediation",
    )


def test_high_confidence_finding_skips_ai() -> None:
    ollama = FakeProvider(
        "ollama",
        "deepseek-r1:1.5b",
        AIProviderResponse("ollama", "deepseek-r1:1.5b", True, "unused"),
    )
    router = AIRouter(
        Settings(),
        ollama_provider=ollama,
        ollama_complex_provider=ollama,
    )

    result = router.analyze(make_finding(confidence=0.95), {"only": "context"})

    assert result.status == "static_only"
    assert ollama.calls == []


def test_simple_finding_uses_local_ollama() -> None:
    context = {"relevant_source": "only this source"}
    ollama = FakeProvider(
        "ollama",
        "deepseek-r1:1.5b",
        AIProviderResponse(
            "ollama",
            "deepseek-r1:1.5b",
            True,
            '{"confidence": 0.74}',
        ),
    )
    router = AIRouter(
        Settings(groq_api_key="unused-for-simple"),
        ollama_provider=ollama,
        ollama_complex_provider=ollama,
    )

    result = router.analyze(make_finding(), context)

    assert result.status == "completed"
    assert result.provider == "ollama"
    assert result.ai_confidence == 0.74
    assert ollama.calls == [context]


def test_complex_finding_prefers_groq_when_configured() -> None:
    groq = FakeProvider(
        "groq",
        "deepseek-r1:7b",
        AIProviderResponse("groq", "deepseek-r1:7b", True, "analysis"),
    )
    ollama = FakeProvider(
        "ollama",
        "deepseek-r1:7b",
        AIProviderResponse("ollama", "deepseek-r1:7b", True, "fallback"),
    )
    router = AIRouter(
        Settings(groq_api_key="configured"),
        ollama_provider=ollama,
        ollama_complex_provider=ollama,
        groq_provider=groq,
    )

    result = router.analyze(
        make_finding(rule_id="possible-idor", confidence=0.65),
        {"relevant_source": "compact"},
    )

    assert result.provider == "groq"
    assert groq.calls
    assert ollama.calls == []


def test_groq_failure_falls_back_to_ollama() -> None:
    groq = FakeProvider(
        "groq",
        "deepseek-r1:7b",
        AIProviderResponse(
            "groq",
            "deepseek-r1:7b",
            False,
            error=ProviderError("connection_error", "unavailable", True),
        ),
    )
    ollama = FakeProvider(
        "ollama",
        "deepseek-r1:7b",
        AIProviderResponse("ollama", "deepseek-r1:7b", True, "fallback analysis"),
    )
    router = AIRouter(
        Settings(groq_api_key="configured"),
        ollama_provider=ollama,
        ollama_complex_provider=ollama,
        groq_provider=groq,
    )

    result = router.analyze(
        make_finding(rule_id="possible-idor", confidence=0.65),
        {"relevant_source": "compact"},
    )

    assert result.provider == "ollama"
    assert result.status == "completed"
    assert [attempt["provider"] for attempt in result.attempts] == [
        "groq",
        "ollama",
    ]


def test_routing_result_is_persisted() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    ollama = FakeProvider(
        "ollama",
        "deepseek-r1:1.5b",
        AIProviderResponse("ollama", "deepseek-r1:1.5b", True, "analysis"),
    )
    router = AIRouter(
        Settings(),
        ollama_provider=ollama,
        ollama_complex_provider=ollama,
    )
    with Session(engine) as session:
        project = Project(
            name="Router test",
            source_type="upload",
            storage_path="storage/router-test",
        )
        session.add(project)
        session.flush()
        finding = SecurityFinding(
            project_id=project.id,
            rule_id="missing-authentication",
            title="Test",
            severity="medium",
            confidence=0.8,
            file="main.py",
            line=1,
            description="Description",
            evidence="Evidence",
            remediation="Remediation",
            context_package={"relevant_source": "compact"},
        )
        session.add(finding)
        session.flush()

        result = router.route_and_persist(finding, None, session)
        session.commit()

        stored = session.query(AIAnalysis).one()
        assert result.provider == stored.provider == "ollama"
        assert stored.model == "deepseek-r1:1.5b"
        assert stored.attempts[0]["provider"] == "ollama"
