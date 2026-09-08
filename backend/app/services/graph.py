"""Construction of the relational code relationship graph."""

from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from app.models import (
    APIRoute,
    CodeClass,
    CodeFunction,
    FunctionCall,
    GraphEdge,
    GraphNode,
    Project,
)

REL_CALLS = "CALLS"
REL_IMPORTS = "IMPORTS"
REL_ROUTES_TO = "ROUTES_TO"

DATABASE_CALL_PATTERN = re.compile(
    r"(?:^|_)(?:db|database|session|query|execute|commit|rollback|select|cursor)(?:$|_)",
    re.IGNORECASE,
)
AUTH_CALL_PATTERN = re.compile(
    r"(?:auth|authenticate|authorization|authorize|permission|token|login|"
    r"current_user|security)",
    re.IGNORECASE,
)
DEPENDENCY_FUNCTION_PATTERN = re.compile(
    r"(?:Depends|Security)\(\s*([A-Za-z_]\w*)",
)


@dataclass(frozen=True)
class GraphBuildSummary:
    """Counts of graph objects created for a project."""

    nodes: int
    edges: int


def _call_name(expression: str) -> str:
    return expression.rsplit(".", maxsplit=1)[-1]


def _call_node_type(expression: str) -> str:
    name = _call_name(expression)
    if DATABASE_CALL_PATTERN.search(name):
        return "database_call"
    if AUTH_CALL_PATTERN.search(name):
        return "authentication_call"
    return "call"


def _add_edge(
    db: Session,
    project: Project,
    source: GraphNode,
    target: GraphNode,
    relationship_type: str,
    metadata: dict,
) -> GraphEdge:
    edge = GraphEdge(
        project_id=project.id,
        source_node_id=source.id,
        target_node_id=target.id,
        relationship_type=relationship_type,
        edge_metadata=metadata,
    )
    db.add(edge)
    return edge


def build_project_graph(project: Project, db: Session) -> GraphBuildSummary:
    """Build graph nodes and edges from the existing code index."""

    db.flush()
    db.query(GraphEdge).filter(GraphEdge.project_id == project.id).delete(
        synchronize_session=False,
    )
    db.query(GraphNode).filter(GraphNode.project_id == project.id).delete(
        synchronize_session=False,
    )
    db.flush()

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    file_nodes: dict[object, GraphNode] = {}
    function_nodes: dict[object, GraphNode] = {}
    functions_by_name: dict[str, list[GraphNode]] = {}
    module_nodes: dict[str, GraphNode] = {}

    for project_file in project.files:
        file_node = GraphNode(
            project_id=project.id,
            project_file_id=project_file.id,
            node_type="file",
            source_file=project_file.relative_path,
            symbol_name=project_file.relative_path,
            node_metadata={"language": project_file.language},
        )
        db.add(file_node)
        nodes.append(file_node)
        file_nodes[project_file.id] = file_node

        for function in project_file.functions:
            function_node = GraphNode(
                project_id=project.id,
                project_file_id=project_file.id,
                node_type="function",
                source_file=project_file.relative_path,
                line_number=function.line_number,
                symbol_name=function.qualname,
                node_metadata={"is_async": function.is_async},
            )
            db.add(function_node)
            nodes.append(function_node)
            function_nodes[function.id] = function_node
            functions_by_name.setdefault(function.name, []).append(function_node)

        for code_class in project_file.classes:
            class_node = GraphNode(
                project_id=project.id,
                project_file_id=project_file.id,
                node_type="class",
                source_file=project_file.relative_path,
                line_number=code_class.line_number,
                symbol_name=code_class.qualname,
                node_metadata={},
            )
            db.add(class_node)
            nodes.append(class_node)

    db.flush()

    for project_file in project.files:
        file_node = file_nodes[project_file.id]
        for code_import in project_file.imports:
            module_node = module_nodes.get(code_import.module)
            if module_node is None:
                module_node = GraphNode(
                    project_id=project.id,
                    node_type="module",
                    symbol_name=code_import.module,
                    node_metadata={},
                )
                db.add(module_node)
                nodes.append(module_node)
                module_nodes[code_import.module] = module_node
            db.flush()
            edges.append(
                _add_edge(
                    db,
                    project,
                    file_node,
                    module_node,
                    REL_IMPORTS,
                    {
                        "line_number": code_import.line_number,
                        "imported_name": code_import.imported_name,
                        "alias": code_import.alias,
                    },
                )
            )

        for route in project_file.routes:
            route_node = GraphNode(
                project_id=project.id,
                project_file_id=project_file.id,
                node_type="route",
                source_file=project_file.relative_path,
                line_number=route.line_number,
                symbol_name=f"{route.http_method} {route.path}",
                node_metadata={
                    "http_method": route.http_method,
                    "path": route.path,
                    "router_name": route.router_name,
                    "dependencies": route.dependencies,
                    "decorator": route.decorator_expression,
                },
            )
            db.add(route_node)
            nodes.append(route_node)
            target_function = (
                function_nodes.get(route.function_id)
                if route.function_id is not None
                else None
            )
            if target_function is not None:
                db.flush()
                edges.append(
                    _add_edge(
                        db,
                        project,
                        route_node,
                        target_function,
                        REL_ROUTES_TO,
                        {"line_number": route.line_number},
                    )
                )
                for dependency in route.dependencies:
                    match = DEPENDENCY_FUNCTION_PATTERN.search(dependency)
                    if match is None:
                        continue
                    dependency_candidates = functions_by_name.get(match.group(1), [])
                    if len(dependency_candidates) == 1:
                        edges.append(
                            _add_edge(
                                db,
                                project,
                                target_function,
                                dependency_candidates[0],
                                REL_CALLS,
                                {
                                    "line_number": route.line_number,
                                    "dependency": dependency,
                                },
                            )
                        )

        for call in project_file.calls:
            caller = (
                function_nodes.get(call.function_id)
                if call.function_id is not None
                else file_node
            )
            target_candidates = functions_by_name.get(_call_name(call.expression), [])
            if len(target_candidates) == 1:
                db.flush()
                edges.append(
                    _add_edge(
                        db,
                        project,
                        caller,
                        target_candidates[0],
                        REL_CALLS,
                        {
                            "line_number": call.line_number,
                            "expression": call.expression,
                        },
                    )
                )
                continue

            call_node = GraphNode(
                project_id=project.id,
                project_file_id=project_file.id,
                node_type=_call_node_type(call.expression),
                source_file=project_file.relative_path,
                line_number=call.line_number,
                symbol_name=call.expression,
                node_metadata={"expression": call.expression},
            )
            db.add(call_node)
            nodes.append(call_node)
            db.flush()
            edges.append(
                _add_edge(
                    db,
                    project,
                    caller,
                    call_node,
                    REL_CALLS,
                    {"line_number": call.line_number},
                )
            )

    db.add(project)
    return GraphBuildSummary(nodes=len(nodes), edges=len(edges))
