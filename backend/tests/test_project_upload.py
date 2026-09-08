from io import BytesIO
from pathlib import Path
import zipfile
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
from app.models import Project, ProjectFile


@pytest.fixture
def client(tmp_path: Path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    def override_settings() -> Settings:
        return Settings(
            database_url="sqlite://",
            storage_dir=str(tmp_path / "projects"),
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings
    with TestClient(app) as test_client:
        yield test_client, engine, tmp_path
    app.dependency_overrides.clear()
    engine.dispose()


def make_zip(*files: tuple[str, str]) -> bytes:
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as zip_file:
        for path, contents in files:
            zip_file.writestr(path, contents)
    return archive.getvalue()


def test_valid_zip_is_extracted(client) -> None:
    test_client, engine, tmp_path = client
    response = test_client.post(
        "/api/projects/upload",
        files={
            "file": (
                "sample-api.zip",
                make_zip(
                    ("app/main.py", "from fastapi import FastAPI\n"),
                    (
                        "pyproject.toml",
                        '[project]\nrequires-python = ">=3.11"\n',
                    ),
                ),
                "application/zip",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "upload"
    assert body["backend_framework"] == "FastAPI"
    assert body["python_version"] == ">=3.11"
    assert Path(body["storage_path"], "app", "main.py").read_text() == (
        "from fastapi import FastAPI\n"
    )
    assert Path(body["storage_path"]).is_relative_to(tmp_path / "projects")
    with Session(engine) as session:
        files = session.query(ProjectFile).all()
        assert len(files) == 1
        assert files[0].relative_path == "app/main.py"
        assert len(files[0].sha256) == 64


def test_invalid_file_is_rejected(client) -> None:
    test_client, _, _ = client
    response = test_client.post(
        "/api/projects/upload",
        files={"file": ("not-a-zip.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 400
    assert "valid ZIP" in response.json()["detail"]


def test_path_traversal_zip_is_rejected(client) -> None:
    test_client, _, tmp_path = client
    response = test_client.post(
        "/api/projects/upload",
        files={
            "file": (
                "malicious.zip",
                make_zip(("../outside.txt", "must not be written")),
                "application/zip",
            )
        },
    )

    assert response.status_code == 400
    assert not (tmp_path / "outside.txt").exists()


def test_project_metadata_is_created(client) -> None:
    test_client, engine, _ = client
    response = test_client.post(
        "/api/projects/upload",
        files={
            "file": (
                "created-project.zip",
                make_zip(("README.md", "Project")),
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 201
    project_id = response.json()["id"]
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        assert project is not None
        assert project.name == "created-project"
        assert project.storage_path == response.json()["storage_path"]
