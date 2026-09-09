"""Persistence service for Python AST indexes."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    APIRoute,
    CodeAssignment,
    CodeClass,
    CodeDecorator,
    CodeFunction,
    CodeImport,
    FunctionCall,
    FunctionParameter,
    ParseError,
    Project,
)
from app.services.ast_parser import parse_python_file


@dataclass(frozen=True)
class IndexingSummary:
    """Counts from indexing one project."""

    files_indexed: int
    parse_errors: int


def index_project(
    project: Project,
    db: Session,
    file_ids: set[UUID] | frozenset[UUID] | None = None,
) -> IndexingSummary:
    """Parse every project Python file and persist its AST entities.

    A failure in one file is recorded as a ``ParseError`` and does not stop
    other files from being indexed.
    """

    db.flush()
    root = Path(project.storage_path)
    files_indexed = 0
    parse_errors = 0

    for project_file in project.files:
        if file_ids is not None and project_file.id not in file_ids:
            continue
        project_file.imports.clear()
        project_file.classes.clear()
        project_file.functions.clear()
        project_file.decorators.clear()
        project_file.calls.clear()
        project_file.routes.clear()
        project_file.assignments.clear()
        project_file.parse_errors.clear()
        path = root / Path(project_file.relative_path)
        try:
            result = parse_python_file(path)
        except (OSError, UnicodeError, SyntaxError, RecursionError) as exc:
            syntax_error = exc if isinstance(exc, SyntaxError) else None
            project_file.parse_errors.append(
                ParseError(
                    message=str(exc),
                    line_number=getattr(syntax_error, "lineno", None),
                    column_number=getattr(syntax_error, "offset", None),
                )
            )
            parse_errors += 1
            continue

        files_indexed += 1
        function_by_qualname: dict[str, CodeFunction] = {}
        for item in result.imports:
            project_file.imports.append(
                CodeImport(
                    module=item.module,
                    imported_name=item.imported_name,
                    alias=item.alias,
                    line_number=item.line_number,
                )
            )
        for item in result.classes:
            project_file.classes.append(
                CodeClass(
                    name=item.name,
                    qualname=item.qualname,
                    line_number=item.line_number,
                    end_line=item.end_line,
                )
            )
        for item in result.functions:
            function = CodeFunction(
                name=item.name,
                qualname=item.qualname,
                line_number=item.line_number,
                end_line=item.end_line,
                is_async=item.is_async,
            )
            function.parameters.extend(
                FunctionParameter(name=name, kind=kind, position=position)
                for name, kind, position in item.parameters
            )
            project_file.functions.append(function)
            function_by_qualname[item.qualname] = function
        for item in result.decorators:
            project_file.decorators.append(
                CodeDecorator(
                    target_type=item.target_type,
                    target_name=item.target_name,
                    expression=item.expression,
                    line_number=item.line_number,
                )
            )
        for item in result.calls:
            project_file.calls.append(
                FunctionCall(
                    expression=item.expression,
                    line_number=item.line_number,
                    function=function_by_qualname.get(item.function_qualname),
                )
            )
        for item in result.routes:
            project_file.routes.append(
                APIRoute(
                    http_method=item.http_method,
                    path=item.path,
                    function_name=item.function_name,
                    router_name=item.router_name,
                    decorator_expression=item.decorator_expression,
                    dependencies=item.dependencies,
                    line_number=item.line_number,
                    function=function_by_qualname.get(item.function_qualname),
                )
            )
        for item in result.assignments:
            project_file.assignments.append(
                CodeAssignment(
                    target=item.target,
                    value=item.value,
                    line_number=item.line_number,
                )
            )

    db.add(project)
    return IndexingSummary(
        files_indexed=files_indexed,
        parse_errors=parse_errors,
    )
