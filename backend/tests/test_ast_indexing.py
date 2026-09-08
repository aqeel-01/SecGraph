from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    APIRoute,
    CodeAssignment,
    CodeClass,
    CodeFunction,
    CodeImport,
    FunctionCall,
    FunctionParameter,
    ParseError,
    Project,
    ProjectFile,
)
from app.services.ast_indexing import index_project
from app.services.ast_parser import parse_python_source


REPRESENTATIVE_SOURCE = """
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/items")
async def get_item(item_id: str, *, include_details: bool = False):
    result = load_item(item_id)
    return result

class ItemService:
    @classmethod
    def save(cls, item):
        return persist(item)
"""


def test_parser_extracts_representative_python_entities() -> None:
    result = parse_python_source(REPRESENTATIVE_SOURCE, "example.py")

    assert {item.module for item in result.imports} == {"os", "fastapi"}
    assert [item.name for item in result.classes] == ["ItemService"]
    assert {item.name for item in result.functions} == {"get_item", "save"}
    get_item = next(item for item in result.functions if item.name == "get_item")
    assert [parameter[0] for parameter in get_item.parameters] == [
        "item_id",
        "include_details",
    ]
    assert any(item.expression == "app.get('/items')" for item in result.decorators)
    assert {item.expression for item in result.calls} >= {
        "FastAPI",
        "load_item",
        "persist",
    }
    assert any(item.target == "app" for item in result.assignments)


def test_index_project_persists_entities_and_parse_errors(tmp_path: Path) -> None:
    valid_path = tmp_path / "valid.py"
    valid_path.write_text(REPRESENTATIVE_SOURCE, encoding="utf-8")
    invalid_path = tmp_path / "invalid.py"
    invalid_path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(name="AST test", source_type="upload", storage_path=str(tmp_path))
        project.files.extend(
            [
                ProjectFile(
                    relative_path="valid.py",
                    size_bytes=valid_path.stat().st_size,
                    sha256="a" * 64,
                    language="python",
                ),
                ProjectFile(
                    relative_path="invalid.py",
                    size_bytes=invalid_path.stat().st_size,
                    sha256="b" * 64,
                    language="python",
                ),
            ]
        )
        session.add(project)
        session.commit()

        summary = index_project(project, session)
        session.commit()

        assert summary.files_indexed == 1
        assert summary.parse_errors == 1
        assert session.query(CodeImport).count() == 2
        assert session.query(CodeClass).count() == 1
        assert session.query(CodeFunction).count() == 2
        assert session.query(APIRoute).count() == 1
        assert session.query(APIRoute).one().path == "/items"
        assert session.query(FunctionParameter).count() == 4
        assert session.query(FunctionCall).count() >= 3
        assert session.query(CodeAssignment).count() >= 2
        assert session.query(ParseError).count() == 1
        assert session.query(ParseError).one().line_number == 1
