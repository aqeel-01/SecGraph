from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import GraphEdge, GraphNode, Project, ProjectFile
from app.services.ast_indexing import index_project
from app.services.graph import (
    REL_CALLS,
    REL_IMPORTS,
    REL_ROUTES_TO,
    build_project_graph,
)


SOURCE = """
from fastapi import Depends, FastAPI
from sqlalchemy import select

app = FastAPI()

def authenticate():
    return True

@app.get("/users/{user_id}", dependencies=[Depends(authenticate)])
def get_user(user_id: str):
    return load_user(user_id)

def load_user(user_id: str):
    return db.execute(select(User)).first()
"""


def test_graph_contains_routes_calls_imports_and_special_call_nodes(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "main.py"
    source_path.write_text(SOURCE, encoding="utf-8")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        project = Project(
            name="Graph test",
            source_type="upload",
            storage_path=str(tmp_path),
        )
        project.files.append(
            ProjectFile(
                relative_path="main.py",
                size_bytes=source_path.stat().st_size,
                sha256=sha256(source_path.read_bytes()).hexdigest(),
                language="python",
            )
        )
        session.add(project)
        session.commit()

        index_project(project, session)
        summary = build_project_graph(project, session)
        session.commit()

        assert summary.nodes == session.query(GraphNode).count()
        assert summary.edges == session.query(GraphEdge).count()
        relationships = {
            edge.relationship_type for edge in session.query(GraphEdge).all()
        }
        assert {REL_CALLS, REL_IMPORTS, REL_ROUTES_TO} <= relationships

        nodes = session.query(GraphNode).all()
        assert any(node.node_type == "database_call" for node in nodes)
        assert any(node.symbol_name == "authenticate" for node in nodes)

        route_node = next(node for node in nodes if node.node_type == "route")
        route_edge = session.query(GraphEdge).filter(
            GraphEdge.source_node_id == route_node.id,
            GraphEdge.relationship_type == REL_ROUTES_TO,
        ).one()
        assert route_edge.target_node.symbol_name == "get_user"

        load_user = next(node for node in nodes if node.symbol_name == "load_user")
        get_user = next(node for node in nodes if node.symbol_name == "get_user")
        assert session.query(GraphEdge).filter(
            GraphEdge.source_node_id == get_user.id,
            GraphEdge.target_node_id == load_user.id,
            GraphEdge.relationship_type == REL_CALLS,
        ).count() == 1
        authenticate = next(
            node for node in nodes if node.symbol_name == "authenticate"
        )
        assert session.query(GraphEdge).filter(
            GraphEdge.source_node_id == get_user.id,
            GraphEdge.target_node_id == authenticate.id,
            GraphEdge.relationship_type == REL_CALLS,
        ).count() == 1
