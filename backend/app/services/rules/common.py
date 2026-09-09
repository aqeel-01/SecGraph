"""Helpers shared by static security rules."""

from pathlib import Path
from uuid import UUID

from app.models import APIRoute, CodeFunction, Project
from app.services.rules.base import RuleContext


def build_rule_context(
    project: Project,
    file_ids: set[UUID] | frozenset[UUID] | None = None,
    root_path: Path | None = None,
) -> RuleContext:
    """Load source text for the already-indexed project files."""

    sources: dict[UUID, str] = {}
    root = root_path or Path(project.storage_path)
    selected_files = (
        project.files
        if file_ids is None
        else [item for item in project.files if item.id in file_ids]
    )
    for project_file in selected_files:
        try:
            sources[project_file.id] = (
                root / project_file.relative_path
            ).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            sources[project_file.id] = ""
    return RuleContext(
        project=project,
        sources=sources,
        file_ids=frozenset(file_ids) if file_ids is not None else None,
    )


def endpoint_for(route: APIRoute) -> str:
    """Format a route consistently in findings."""

    return f"{route.http_method} {route.path}"


def function_source(context: RuleContext, function: CodeFunction) -> str:
    """Return the source span belonging to a function."""

    source = context.source_for(function.project_file_id)
    lines = source.splitlines()
    start = max(function.line_number - 1, 0)
    end = function.end_line or len(lines)
    return "\n".join(lines[start:end])
