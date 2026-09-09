from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Project, Scan, ScanStatus, SecurityFinding
from app.services.scan_tasks import execute_scan


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


class FakeTask:
    def __init__(self) -> None:
        self.scan_ids: list[str] = []

    def delay(self, scan_id: str) -> None:
        self.scan_ids.append(scan_id)


def test_create_scan_returns_immediately_and_status_can_be_read(
    database,
    monkeypatch,
) -> None:
    with Session(database) as session:
        project = Project(
            name="Queued project",
            source_type="upload",
            storage_path="storage/queued",
        )
        session.add(project)
        session.commit()
        project_id = project.id

    task = FakeTask()
    monkeypatch.setattr("app.api.scans.run_scan", task)

    def override_db():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/projects/{project_id}/scan")
            assert response.status_code == 202
            body = response.json()
            assert body["status"] == "PENDING"
            assert task.scan_ids == [body["id"]]

            status_response = client.get(f"/api/scans/{body['id']}")
            assert status_response.status_code == 200
            assert status_response.json()["status"] == "PENDING"
    finally:
        app.dependency_overrides.clear()


def test_scan_worker_runs_pipeline_and_completes(database, tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/')\n"
        "def home():\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )
    with Session(database) as session:
        project = Project(
            name="Worker project",
            source_type="upload",
            storage_path=str(tmp_path),
        )
        session.add(project)
        session.flush()
        scan = Scan(project_id=project.id, status=ScanStatus.PENDING)
        session.add(scan)
        session.commit()
        scan_id = scan.id

        class FakeExplanation:
            def __init__(self) -> None:
                self.findings: list[UUID] = []

            def explain(self, finding, context, db) -> None:
                self.findings.append(finding.id)

        explanation = FakeExplanation()
        result = execute_scan(scan_id, session, explanation)

        refreshed_scan = session.get(Scan, scan_id)
        assert result["status"] == "COMPLETED"
        assert refreshed_scan.status == ScanStatus.COMPLETED
        assert refreshed_scan.started_at is not None
        assert refreshed_scan.completed_at is not None
        assert session.query(SecurityFinding).count() == 1
        assert len(explanation.findings) == 1


def test_scan_worker_marks_failures(database, tmp_path: Path) -> None:
    with Session(database) as session:
        project = Project(
            name="Failed project",
            source_type="upload",
            storage_path=str(tmp_path / "missing"),
        )
        session.add(project)
        session.flush()
        scan = Scan(project_id=project.id, status=ScanStatus.PENDING)
        session.add(scan)
        session.commit()

        result = execute_scan(scan.id, session)

        refreshed_scan = session.get(Scan, scan.id)
        assert result["status"] == "FAILED"
        assert refreshed_scan.status == ScanStatus.FAILED
        assert refreshed_scan.error_message
