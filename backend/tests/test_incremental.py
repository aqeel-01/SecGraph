from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Project, ProjectFile
from app.services.ast_indexing import index_project
from app.services.incremental import synchronize_project_files
from app.services.preprocessing import preprocess_directory


def make_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def add_file(project: Project, path: Path, relative_path: str) -> None:
    content = path.read_bytes()
    project.files.append(
        ProjectFile(
            relative_path=relative_path,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            language="python",
        )
    )


def test_unchanged_files_are_not_reindexed(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "main.py"
    source.write_text("def main():\n    return True\n", encoding="utf-8")
    other = tmp_path / "other.py"
    other.write_text("def other():\n    return False\n", encoding="utf-8")
    engine = make_database()

    with Session(engine) as session:
        project = Project(
            name="Incremental test",
            source_type="upload",
            storage_path=str(tmp_path),
        )
        add_file(project, source, "main.py")
        add_file(project, other, "other.py")
        session.add(project)
        session.commit()

        current = preprocess_directory(tmp_path)
        changes = synchronize_project_files(project, current, session)

        parse_calls = 0

        def unexpected_parse(*args, **kwargs):
            nonlocal parse_calls
            parse_calls += 1
            raise AssertionError("unchanged files should not be parsed")

        monkeypatch.setattr(
            "app.services.ast_indexing.parse_python_file",
            unexpected_parse,
        )
        index_project(project, session, changes.affected_file_ids)

        assert changes.added == ()
        assert changes.modified == ()
        assert changes.deleted == ()
        assert set(changes.unchanged) == {"main.py", "other.py"}
        assert changes.affected_file_ids == frozenset()
        assert parse_calls == 0


def test_incremental_sync_identifies_added_modified_and_deleted(
    tmp_path: Path,
) -> None:
    main = tmp_path / "main.py"
    main.write_text("def main():\n    return 2\n", encoding="utf-8")
    added = tmp_path / "added.py"
    added.write_text("def added():\n    return 3\n", encoding="utf-8")
    engine = make_database()

    with Session(engine) as session:
        project = Project(
            name="Change set test",
            source_type="upload",
            storage_path=str(tmp_path),
        )
        old_main = ProjectFile(
            relative_path="main.py",
            size_bytes=1,
            sha256="0" * 64,
            language="python",
        )
        deleted = ProjectFile(
            relative_path="deleted.py",
            size_bytes=1,
            sha256="1" * 64,
            language="python",
        )
        project.files.extend([old_main, deleted])
        session.add(project)
        session.commit()

        changes = synchronize_project_files(
            project,
            preprocess_directory(tmp_path),
            session,
        )

        assert changes.added == ("added.py",)
        assert changes.modified == ("main.py",)
        assert changes.deleted == ("deleted.py",)
        assert changes.unchanged == ()
        assert len(changes.affected_file_ids) == 3
