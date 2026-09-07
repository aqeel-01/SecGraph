from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Project, Scan
from app.schemas import ProjectRead, ScanRead


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def test_project_and_scan_relationship_and_schema_conversion() -> None:
    with make_session() as session:
        project = Project(
            name="Example API",
            source_type="upload",
            storage_path="storage/example",
        )
        scan = Scan(status="pending", project=project)
        session.add(project)
        session.commit()
        session.refresh(project)
        session.refresh(scan)

        assert isinstance(project.id, UUID)
        assert project.scans == [scan]
        assert scan.project_id == project.id
        assert project.created_at is not None
        assert project.updated_at is not None
        assert ProjectRead.model_validate(project).name == "Example API"
        assert ScanRead.model_validate(scan).status == "pending"

        stored_scan = session.scalar(select(Scan).where(Scan.id == scan.id))
        assert stored_scan is not None
        assert stored_scan.project.name == "Example API"


def test_deleting_project_deletes_related_scans() -> None:
    with make_session() as session:
        project = Project(
            name="Delete me",
            source_type="repository",
            storage_path="storage/delete-me",
        )
        project.scans.append(Scan(status="pending"))
        session.add(project)
        session.commit()
        scan_id = project.scans[0].id

        session.delete(project)
        session.commit()

        assert session.get(Scan, scan_id) is None
