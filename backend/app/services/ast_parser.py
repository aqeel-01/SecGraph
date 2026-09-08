"""Modular Python AST parsing for the code index."""

from ast import (
    AnnAssign,
    Assign,
    AsyncFunctionDef,
    AugAssign,
    Call,
    ClassDef,
    FunctionDef,
    Import,
    ImportFrom,
    NodeVisitor,
    parse,
    unparse,
)
from dataclasses import dataclass, field
from pathlib import Path

from app.services.route_detection import (
    RouteRecord,
    detect_fastapi_routes,
)


@dataclass(frozen=True)
class ImportRecord:
    module: str
    imported_name: str | None
    alias: str | None
    line_number: int


@dataclass(frozen=True)
class ClassRecord:
    name: str
    qualname: str
    line_number: int
    end_line: int | None


@dataclass(frozen=True)
class FunctionRecord:
    name: str
    qualname: str
    line_number: int
    end_line: int | None
    is_async: bool
    parameters: list[tuple[str, str, int]]


@dataclass(frozen=True)
class DecoratorRecord:
    target_type: str
    target_name: str
    expression: str
    line_number: int


@dataclass(frozen=True)
class CallRecord:
    expression: str
    line_number: int
    function_qualname: str | None


@dataclass(frozen=True)
class AssignmentRecord:
    target: str
    value: str | None
    line_number: int


@dataclass
class ASTIndexResult:
    imports: list[ImportRecord] = field(default_factory=list)
    classes: list[ClassRecord] = field(default_factory=list)
    functions: list[FunctionRecord] = field(default_factory=list)
    decorators: list[DecoratorRecord] = field(default_factory=list)
    calls: list[CallRecord] = field(default_factory=list)
    assignments: list[AssignmentRecord] = field(default_factory=list)
    routes: list[RouteRecord] = field(default_factory=list)


def _expression(node: object) -> str:
    """Render an AST node without allowing formatting to break indexing."""

    try:
        return unparse(node)  # type: ignore[arg-type]
    except (AttributeError, ValueError):
        return type(node).__name__


class PythonASTIndexer(NodeVisitor):
    """Collect deterministic code entities from one parsed module."""

    def __init__(self) -> None:
        self.result = ASTIndexResult()
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []

    @property
    def _qualname(self) -> str:
        return ".".join([*self._class_stack, *self._function_stack])

    def visit_Import(self, node: Import) -> None:
        for alias in node.names:
            self.result.imports.append(
                ImportRecord(
                    module=alias.name,
                    imported_name=None,
                    alias=alias.asname,
                    line_number=node.lineno,
                )
            )

    def visit_ImportFrom(self, node: ImportFrom) -> None:
        module = "." * node.level + (node.module or "")
        for alias in node.names:
            self.result.imports.append(
                ImportRecord(
                    module=module,
                    imported_name=alias.name,
                    alias=alias.asname,
                    line_number=node.lineno,
                )
            )

    def visit_ClassDef(self, node: ClassDef) -> None:
        qualname = ".".join([*self._class_stack, node.name])
        self.result.classes.append(
            ClassRecord(
                name=node.name,
                qualname=qualname,
                line_number=node.lineno,
                end_line=getattr(node, "end_lineno", None),
            )
        )
        self._add_decorators("class", qualname, node.decorator_list)
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def _visit_function(
        self,
        node: FunctionDef | AsyncFunctionDef,
        *,
        is_async: bool,
    ) -> None:
        qualname = ".".join([*self._class_stack, *self._function_stack, node.name])
        self.result.functions.append(
            FunctionRecord(
                name=node.name,
                qualname=qualname,
                line_number=node.lineno,
                end_line=getattr(node, "end_lineno", None),
                is_async=is_async,
                parameters=self._parameters(node),
            )
        )
        self._add_decorators("function", qualname, node.decorator_list)
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def _parameters(
        self,
        node: FunctionDef | AsyncFunctionDef,
    ) -> list[tuple[str, str, int]]:
        args = node.args
        positional = [*args.posonlyargs, *args.args]
        parameters = [
            (argument.arg, "positional", position)
            for position, argument in enumerate(positional)
        ]
        offset = len(parameters)
        parameters.extend(
            (argument.arg, "keyword_only", offset + position)
            for position, argument in enumerate(args.kwonlyargs)
        )
        if args.vararg is not None:
            parameters.append((args.vararg.arg, "var_positional", len(parameters)))
        if args.kwarg is not None:
            parameters.append((args.kwarg.arg, "var_keyword", len(parameters)))
        return parameters

    def _add_decorators(
        self,
        target_type: str,
        target_name: str,
        decorators: list[object],
    ) -> None:
        for decorator in decorators:
            self.result.decorators.append(
                DecoratorRecord(
                    target_type=target_type,
                    target_name=target_name,
                    expression=_expression(decorator),
                    line_number=getattr(decorator, "lineno", 0),
                )
            )

    def visit_Call(self, node: Call) -> None:
        self.result.calls.append(
            CallRecord(
                expression=_expression(node.func),
                line_number=node.lineno,
                function_qualname=self._qualname or None,
            )
        )
        self.generic_visit(node)

    def visit_Assign(self, node: Assign) -> None:
        for target in node.targets:
            self._add_assignment(target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: AnnAssign) -> None:
        self._add_assignment(node.target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: AugAssign) -> None:
        self._add_assignment(node.target, node.value, node.lineno)
        self.generic_visit(node)

    def _add_assignment(self, target: object, value: object, line_number: int) -> None:
        self.result.assignments.append(
            AssignmentRecord(
                target=_expression(target),
                value=_expression(value) if value is not None else None,
                line_number=line_number,
            )
        )


def parse_python_source(source: str, filename: str = "<unknown>") -> ASTIndexResult:
    """Parse and index one Python source string.

    ``SyntaxError`` is intentionally allowed to propagate so the persistence
    layer can record it against the specific file without aborting a project.
    """

    tree = parse(source, filename=filename)
    indexer = PythonASTIndexer()
    indexer.visit(tree)
    indexer.result.routes = detect_fastapi_routes(tree)
    return indexer.result


def parse_python_file(path: Path) -> ASTIndexResult:
    """Read and index one UTF-8 Python file."""

    return parse_python_source(path.read_text(encoding="utf-8"), str(path))
