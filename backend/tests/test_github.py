from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Project, ScanStatus
from app.services.github import (
    InvalidGitHubRepository,
    parse_repository_url,
    validate_ref,
)


def test_github_repository_url_validation() -> None:
    assert parse_repository_url("https://github.com/acme/api.git") == (
        "acme",
        "api",
    )
    assert validate_ref("feature/security-review") == "feature/security-review"

    with pytest.raises(InvalidGitHubRepository):
        parse_repository_url("https://example.com/acme/api")
    with pytest.raises(InvalidGitHubRepository):
        validate_ref("../escape")


@pytest.fixture
def github_client(tmp_path: Path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    class FakeTask:
        ids: list[str] = []

        def delay(self, scan_id: str) -> None:
            self.ids.append(scan_id)

    task = FakeTask()

    def fake_download(repository_url, destination, settings, repository_ref):
        destination.mkdir(parents=True)
        (destination / "main.py").write_text("print('ok')", encoding="utf-8")
        return "https://github.com/acme/api", repository_ref

    monkeypatch.setattr("app.api.projects.download_repository", fake_download)
    monkeypatch.setattr("app.api.projects.run_scan", task)

    def override_db():
        with Session(engine) as session:
            yield session

    def override_settings() -> Settings:
        return Settings(storage_dir=str(tmp_path / "projects"))

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings
    try:
        with TestClient(app) as client:
            yield client, engine, task
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_github_import_creates_project_and_queues_scan(github_client) -> None:
    client, engine, task = github_client

    response = client.post(
        "/api/projects/github",
        json={
            "repository_url": "https://github.com/acme/api",
            "repository_ref": "main",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["project"]["source_type"] == "github"
    assert body["project"]["source_url"] == "https://github.com/acme/api"
    assert body["project"]["source_ref"] == "main"
    assert body["scan"]["status"] == ScanStatus.PENDING
    assert task.ids == [body["scan"]["id"]]
    with Session(engine) as session:
        project = session.get(Project, UUID(body["project"]["id"]))
        assert project is not None
        assert Path(project.storage_path, "main.py").exists()
