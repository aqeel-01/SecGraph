from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    AIAnalysis,
    Project,
    Scan,
    ScanStatus,
    SecurityFinding,
)


@pytest.fixture
def dashboard_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(
            name="Dashboard project",
            source_type="upload",
            storage_path="storage/dashboard",
            backend_framework="FastAPI",
            python_version=">=3.11",
        )
        session.add(project)
        session.flush()
        now = datetime.now(timezone.utc)
        session.add_all(
            [
                Scan(
                    project_id=project.id,
                    status=ScanStatus.COMPLETED,
                    started_at=now - timedelta(minutes=2),
                    completed_at=now - timedelta(minutes=1),
                ),
                Scan(project_id=project.id, status=ScanStatus.PENDING),
            ]
        )
        findings = [
            SecurityFinding(
                project_id=project.id,
                rule_id="hardcoded-secret",
                title="Hardcoded secret",
                severity="critical",
                confidence=0.9,
                file="main.py",
                line=4,
                endpoint="POST /users",
                description="Secret found.",
                evidence="api_key = '<redacted>'",
                remediation="Use a secret store.",
                context_package={"relevant_source": "main.py"},
            ),
            SecurityFinding(
                project_id=project.id,
                rule_id="possible-idor",
                title="Possible IDOR",
                severity="high",
                confidence=0.65,
                file="routes.py",
                line=12,
                endpoint="GET /users/{id}",
                description="Ownership check is unclear.",
                evidence="resource id",
                remediation="Validate ownership.",
                context_package={"relevant_source": "routes.py"},
            ),
            SecurityFinding(
                project_id=project.id,
                rule_id="missing-rate-limiting",
                title="Missing rate limiting",
                severity="medium",
                confidence=0.6,
                file="routes.py",
                line=20,
                endpoint="POST /users",
                description="No limiter found.",
                evidence="@app.post",
                remediation="Add rate limiting.",
                context_package={"relevant_source": "routes.py"},
            ),
            SecurityFinding(
                project_id=project.id,
                rule_id="sensitive-data-exposure",
                title="Sensitive data exposure",
                severity="low",
                confidence=0.6,
                file="users.py",
                line=8,
                endpoint=None,
                description="Sensitive field may be returned.",
                evidence="return password",
                remediation="Use a safe response schema.",
                context_package={"relevant_source": "users.py"},
            ),
        ]
        session.add_all(findings)
        session.flush()
        session.add(
            AIAnalysis(
                finding_id=findings[0].id,
                decision="complex",
                status="completed",
                provider="groq",
                model="deepseek-r1:7b",
                ai_confidence=0.92,
                response='{"severity":"critical"}',
                explanation_status="validated",
                structured_output={
                    "severity": "critical",
                    "confidence": 0.92,
                    "explanation": "Validated explanation.",
                    "potential_attack": "Credential use.",
                    "impact": "Unauthorized access.",
                    "suggested_fix": "Rotate the key.",
                },
                attempts=[{"provider": "groq", "success": True}],
            )
        )
        session.commit()
        project_id = project.id

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            yield client, project_id
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_project_list_and_detail(dashboard_client) -> None:
    client, project_id = dashboard_client

    projects = client.get("/api/projects")
    assert projects.status_code == 200
    assert projects.json()[0]["name"] == "Dashboard project"

    detail = client.get(f"/api/projects/{project_id}")
    assert detail.status_code == 200
    assert detail.json()["scan_count"] == 2
    assert detail.json()["latest_scan"]["status"] == "COMPLETED"


def test_scan_history(dashboard_client) -> None:
    client, project_id = dashboard_client

    response = client.get(f"/api/projects/{project_id}/scans")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_findings_filters_and_details(dashboard_client) -> None:
    client, project_id = dashboard_client

    response = client.get(
        f"/api/projects/{project_id}/findings",
        params={"severity": "HIGH", "rule": "possible-idor"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    finding_id = response.json()[0]["id"]

    endpoint_filtered = client.get(
        f"/api/projects/{project_id}/findings",
        params={"endpoint": "POST /users"},
    )
    assert len(endpoint_filtered.json()) == 2

    details = client.get(f"/api/findings/{finding_id}")
    assert details.status_code == 200
    assert details.json()["rule_id"] == "possible-idor"

    nested_details = client.get(
        f"/api/projects/{project_id}/findings/{finding_id}"
    )
    assert nested_details.status_code == 200


def test_security_summary(dashboard_client) -> None:
    client, project_id = dashboard_client

    response = client.get(f"/api/projects/{project_id}/summary")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": str(project_id),
        "total_findings": 4,
        "critical_count": 1,
        "high_count": 1,
        "medium_count": 1,
        "low_count": 1,
        "overall_security_score": 49.0,
    }


def test_missing_dashboard_resources_return_404(dashboard_client) -> None:
    client, _ = dashboard_client
    missing_id = "00000000-0000-0000-0000-000000000000"

    assert client.get(f"/api/projects/{missing_id}").status_code == 404
    assert client.get(f"/api/findings/{missing_id}").status_code == 404
