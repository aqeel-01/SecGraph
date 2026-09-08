"""FastAPI route detection from Python AST nodes."""

from ast import (
    AST,
    Attribute,
    Call,
    FunctionDef,
    List,
    Name,
    NodeVisitor,
    Tuple,
    literal_eval,
    unparse,
)
from dataclasses import dataclass

FASTAPI_METHODS = {"get", "post", "put", "patch", "delete"}


@dataclass(frozen=True)
class RouteRecord:
    """A structured FastAPI route declaration."""

    http_method: str
    path: str
    function_name: str
    function_qualname: str
    router_name: str
    decorator_expression: str
    dependencies: list[str]
    line_number: int


def _expression(node: AST) -> str:
    return unparse(node)


def _string_or_expression(node: AST) -> str:
    try:
        value = literal_eval(node)
    except (ValueError, SyntaxError):
        return _expression(node)
    return value if isinstance(value, str) else _expression(node)


def _methods(node: Call, decorator_name: str) -> list[str]:
    if decorator_name != "api_route":
        return [decorator_name.upper()]
    keyword = next((item for item in node.keywords if item.arg == "methods"), None)
    if keyword is None:
        return ["GET"]
    try:
        values = literal_eval(keyword.value)
    except (ValueError, SyntaxError):
        values = []
    if isinstance(values, (list, tuple, set)):
        return [str(value).upper() for value in values if isinstance(value, str)]
    return []


def _dependencies(node: Call) -> list[str]:
    keyword = next(
        (item for item in node.keywords if item.arg == "dependencies"),
        None,
    )
    if keyword is None:
        return []
    value = keyword.value
    if isinstance(value, (List, Tuple)):
        return [_expression(item) for item in value.elts]
    return [_expression(value)]


class FastAPIRouteDetector(NodeVisitor):
    """Find FastAPI route decorators on functions."""

    def __init__(self) -> None:
        self.routes: list[RouteRecord] = []
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []

    def visit_ClassDef(self, node) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node) -> None:
        self._visit_function(node)

    def _visit_function(self, node: FunctionDef) -> None:
        qualname = ".".join([*self._class_stack, *self._function_stack, node.name])
        self._function_stack.append(node.name)
        for decorator in node.decorator_list:
            self._add_routes(decorator, node, qualname)
        self.generic_visit(node)
        self._function_stack.pop()

    def _add_routes(self, decorator: AST, node: FunctionDef, qualname: str) -> None:
        if not isinstance(decorator, Call):
            return
        if not isinstance(decorator.func, Attribute):
            return
        decorator_name = decorator.func.attr
        if decorator_name not in FASTAPI_METHODS and decorator_name != "api_route":
            return
        if not decorator.args:
            return
        router_node = decorator.func.value
        if not isinstance(router_node, (Name, Attribute)):
            return
        router_name = _expression(router_node)
        path = _string_or_expression(decorator.args[0])
        for method in _methods(decorator, decorator_name):
            self.routes.append(
                RouteRecord(
                    http_method=method,
                    path=path,
                    function_name=node.name,
                    function_qualname=qualname,
                    router_name=router_name,
                    decorator_expression=_expression(decorator),
                    dependencies=_dependencies(decorator),
                    line_number=decorator.lineno,
                )
            )


def detect_fastapi_routes(tree: AST) -> list[RouteRecord]:
    """Return FastAPI routes from an already parsed AST."""

    detector = FastAPIRouteDetector()
    detector.visit(tree)
    return detector.routes
