from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Project, ProjectFile
from app.services.ast_indexing import index_project
from app.services.context_builder import SecurityContextBuilder
from app.services.graph import build_project_graph
from app.services.rules.base import Finding


RELEVANT_SOURCE = """
from fastapi import Depends, FastAPI

app = FastAPI()

def authenticate():
    return True

@app.get("/users/{user_id}", dependencies=[Depends(authenticate)])
def get_user(user_id: str):
    return load_user(user_id)

def load_user(user_id: str):
    return db.execute(query)
"""

IRRELEVANT_SOURCE = """
def unrelated_function():
    return "this must not enter the context"
"""


def test_context_builder_limits_package_to_relevant_code(tmp_path: Path) -> None:
    relevant_path = tmp_path / "main.py"
    relevant_path.write_text(RELEVANT_SOURCE, encoding="utf-8")
    irrelevant_path = tmp_path / "unrelated.py"
    irrelevant_path.write_text(IRRELEVANT_SOURCE, encoding="utf-8")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(
            name="Context test",
            source_type="upload",
            storage_path=str(tmp_path),
        )
        project.files.extend(
            [
                ProjectFile(
                    relative_path="main.py",
                    size_bytes=relevant_path.stat().st_size,
                    sha256=sha256(relevant_path.read_bytes()).hexdigest(),
                    language="python",
                ),
                ProjectFile(
                    relative_path="unrelated.py",
                    size_bytes=irrelevant_path.stat().st_size,
                    sha256=sha256(irrelevant_path.read_bytes()).hexdigest(),
                    language="python",
                ),
            ]
        )
        session.add(project)
        session.commit()
        index_project(project, session)
        build_project_graph(project, session)
        session.commit()

        route = project.files[0].routes[0]
        finding = Finding(
            rule_id="test-rule",
            title="Test finding",
            severity="medium",
            confidence=0.7,
            file="main.py",
            line=route.line_number,
            endpoint="GET /users/{user_id}",
            description="Test",
            evidence="@app.get('/users/{user_id}')",
            remediation="Test remediation",
            project_file_id=project.files[0].id,
            route_id=route.id,
        )
        package = SecurityContextBuilder(session).build(project, finding)

        assert package["endpoint"]["path"] == "/users/{user_id}"
        assert "get_user" in package["vulnerable_function"]["name"]
        assert "load_user" in {
            item["name"] for item in package["related_functions"]
        }
        assert package["authentication_dependencies"] == [
            "Depends(authenticate)"
        ]
        assert "unrelated_function" not in str(package)
        assert "this must not enter the context" not in str(package)
        assert len(package["relevant_source"]) < len(
            RELEVANT_SOURCE + IRRELEVANT_SOURCE
        )
