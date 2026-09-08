"""Compact, relevant security-analysis context construction."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    APIRoute,
    CodeFunction,
    GraphEdge,
    GraphNode,
    Project,
)
from app.services.rules.base import Finding
from app.services.rules.common import endpoint_for

MAX_SOURCE_LENGTH = 12_000
MAX_RELATED_FUNCTIONS = 10
MAX_GRAPH_RELATIONSHIPS = 20
AUTHORIZATION_CHECK = re.compile(
    r"(?:authorize|authorization|permission|owner|ownership|"
    r"current_user|is_owner|can_[a-z_]+)",
    re.IGNORECASE,
)
DATABASE_OPERATION = re.compile(
    r"(?:db|database|session|query|execute|executemany|select|commit|"
    r"rollback|cursor)",
    re.IGNORECASE,
)


def _truncate(value: str, limit: int = MAX_SOURCE_LENGTH) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n...[truncated]"


class SecurityContextBuilder:
    """Build only the code and graph context relevant to one finding."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, project: Project, finding: Finding) -> dict[str, Any]:
        """Return a JSON-serializable context package for a finding."""

        project_file = self._project_file(project, finding)
        route = self._route(project, finding, project_file)
        function = self._function(project_file, route, finding)
        endpoint = self._endpoint(route)
        source = self._source(project, project_file, function, finding)

        return {
            "finding": {
                "rule_id": finding.rule_id,
                "title": finding.title,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "description": finding.description,
                "evidence": finding.evidence,
                "remediation": finding.remediation,
            },
            "endpoint": endpoint,
            "vulnerable_function": self._function_data(
                project_file,
                function,
                source,
            ),
            "relevant_source": _truncate(source),
            "related_functions": self._related_functions(project, function),
            "authentication_dependencies": (
                list(route.dependencies) if route is not None else []
            ),
            "authorization_checks": self._authorization_checks(source),
            "database_operations": self._database_operations(function, source),
            "code_graph_relationships": self._graph_relationships(
                project,
                function,
            ),
        }

    def _project_file(self, project: Project, finding: Finding):
        if finding.project_file_id is not None:
            for project_file in project.files:
                if project_file.id == finding.project_file_id:
                    return project_file
        return next(
            (
                project_file
                for project_file in project.files
                if project_file.relative_path == finding.file
            ),
            None,
        )

    def _route(
        self,
        project: Project,
        finding: Finding,
        project_file,
    ) -> APIRoute | None:
        if project_file is None:
            return None
        for route in project_file.routes:
            if finding.route_id is not None and route.id == finding.route_id:
                return route
            if finding.endpoint == endpoint_for(route):
                return route
        return None

    def _function(
        self,
        project_file,
        route: APIRoute | None,
        finding: Finding,
    ) -> CodeFunction | None:
        if route is not None and route.function is not None:
            return route.function
        if project_file is None or finding.line is None:
            return None
        return next(
            (
                function
                for function in project_file.functions
                if function.line_number <= finding.line
                and (function.end_line is None or finding.line <= function.end_line)
            ),
            None,
        )

    def _source(
        self,
        project: Project,
        project_file,
        function: CodeFunction | None,
        finding: Finding,
    ) -> str:
        if project_file is None:
            return ""
        try:
            source = (
                Path(project.storage_path) / project_file.relative_path
            ).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""
        if function is not None:
            lines = source.splitlines()
            start = max(function.line_number - 1, 0)
            end = function.end_line or len(lines)
            return "\n".join(lines[start:end])
        lines = source.splitlines()
        if finding.line is None:
            return source
        start = max(0, finding.line - 3)
        end = min(len(lines), finding.line + 2)
        return "\n".join(lines[start:end])

    def _function_data(
        self,
        project_file,
        function: CodeFunction | None,
        source: str,
    ) -> dict[str, Any] | None:
        if function is None:
            return None
        return {
            "name": function.qualname,
            "file": project_file.relative_path if project_file else None,
            "line": function.line_number,
            "source": _truncate(source),
        }

    def _related_functions(
        self,
        project: Project,
        function: CodeFunction | None,
    ) -> list[dict[str, Any]]:
        if function is None:
            return []
        function_node = self.db.query(GraphNode).filter(
            GraphNode.project_id == project.id,
            GraphNode.node_type == "function",
            GraphNode.symbol_name == function.qualname,
        ).first()
        if function_node is None:
            return []
        edges = self.db.query(GraphEdge).filter(
            GraphEdge.project_id == project.id,
            or_(
                GraphEdge.source_node_id == function_node.id,
                GraphEdge.target_node_id == function_node.id,
            ),
        ).limit(MAX_GRAPH_RELATIONSHIPS).all()
        related_ids = {
            edge.target_node_id
            if edge.source_node_id == function_node.id
            else edge.source_node_id
            for edge in edges
        }
        nodes = self.db.query(GraphNode).filter(
            GraphNode.id.in_(related_ids),
            GraphNode.node_type == "function",
        ).all()
        return [
            {
                "name": node.symbol_name,
                "file": node.source_file,
                "line": node.line_number,
                "source": _truncate(self._node_source(project, node), 4_000),
            }
            for node in nodes[:MAX_RELATED_FUNCTIONS]
        ]

    def _node_source(self, project: Project, node: GraphNode) -> str:
        project_file = next(
            (
                project_file
                for project_file in project.files
                if project_file.id == node.project_file_id
            ),
            None,
        )
        if project_file is None:
            return ""
        function = next(
            (
                function
                for function in project_file.functions
                if function.qualname == node.symbol_name
            ),
            None,
        )
        if function is None:
            return ""
        try:
            lines = (
                Path(project.storage_path) / project_file.relative_path
            ).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return ""
        return "\n".join(
            lines[max(function.line_number - 1, 0) : function.end_line]
        )

    def _endpoint(self, route: APIRoute | None) -> dict[str, Any] | None:
        if route is None:
            return None
        return {
            "method": route.http_method,
            "path": route.path,
            "router": route.router_name,
            "dependencies": list(route.dependencies),
        }

    def _authorization_checks(self, source: str) -> list[str]:
        return [
            line.strip()
            for line in source.splitlines()
            if AUTHORIZATION_CHECK.search(line)
        ][:10]

    def _database_operations(
        self,
        function: CodeFunction | None,
        source: str,
    ) -> list[str]:
        operations = [
            call.expression
            for call in (function.calls if function is not None else [])
            if DATABASE_OPERATION.search(call.expression)
        ]
        if operations:
            return operations[:10]
        return [
            line.strip()
            for line in source.splitlines()
            if DATABASE_OPERATION.search(line)
        ][:10]

    def _graph_relationships(
        self,
        project: Project,
        function: CodeFunction | None,
    ) -> list[dict[str, Any]]:
        if function is None:
            return []
        function_node = self.db.query(GraphNode).filter(
            GraphNode.project_id == project.id,
            GraphNode.node_type == "function",
            GraphNode.symbol_name == function.qualname,
        ).first()
        if function_node is None:
            return []
        edges = self.db.query(GraphEdge).filter(
            GraphEdge.project_id == project.id,
            or_(
                GraphEdge.source_node_id == function_node.id,
                GraphEdge.target_node_id == function_node.id,
            ),
        ).limit(MAX_GRAPH_RELATIONSHIPS).all()
        node_ids = {
            edge.source_node_id for edge in edges
        } | {
            edge.target_node_id for edge in edges
        }
        nodes = {
            node.id: node
            for node in self.db.query(GraphNode).filter(GraphNode.id.in_(node_ids)).all()
        }
        return [
            {
                "relationship": edge.relationship_type,
                "source": nodes[edge.source_node_id].symbol_name,
                "target": nodes[edge.target_node_id].symbol_name,
            }
            for edge in edges
            if edge.source_node_id in nodes and edge.target_node_id in nodes
        ]
