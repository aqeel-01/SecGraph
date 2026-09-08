"""Database models for the Python AST code index."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project_file import ProjectFile


class IndexedEntity(UUIDPrimaryKeyMixin, Base):
    """Shared project-file reference for indexed AST entities."""

    __abstract__ = True

    project_file_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)


class CodeImport(IndexedEntity):
    __tablename__ = "code_imports"

    module: Mapped[str] = mapped_column(String(512), nullable=False)
    imported_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    alias: Mapped[str | None] = mapped_column(String(255), nullable=True)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="imports")


class CodeClass(IndexedEntity):
    __tablename__ = "code_classes"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualname: Mapped[str] = mapped_column(String(1024), nullable=False)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="classes")


class CodeFunction(IndexedEntity):
    __tablename__ = "code_functions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualname: Mapped[str] = mapped_column(String(1024), nullable=False)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_async: Mapped[bool] = mapped_column(Boolean, nullable=False)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="functions")
    parameters: Mapped[list["FunctionParameter"]] = relationship(
        back_populates="function",
        cascade="all, delete-orphan",
    )
    calls: Mapped[list["FunctionCall"]] = relationship(
        back_populates="function",
        cascade="all, delete-orphan",
    )
    routes: Mapped[list["APIRoute"]] = relationship(
        back_populates="function",
        cascade="all, delete-orphan",
    )


class FunctionParameter(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "function_parameters"

    function_id: Mapped[UUID] = mapped_column(
        ForeignKey("code_functions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    function: Mapped["CodeFunction"] = relationship(back_populates="parameters")


class CodeDecorator(IndexedEntity):
    __tablename__ = "code_decorators"

    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="decorators")


class FunctionCall(IndexedEntity):
    __tablename__ = "function_calls"

    function_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("code_functions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    expression: Mapped[str] = mapped_column(Text, nullable=False)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="calls")
    function: Mapped["CodeFunction | None"] = relationship(back_populates="calls")


class APIRoute(IndexedEntity):
    __tablename__ = "api_routes"

    function_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("code_functions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    http_method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    function_name: Mapped[str] = mapped_column(String(255), nullable=False)
    router_name: Mapped[str] = mapped_column(String(512), nullable=False)
    decorator_expression: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="routes")
    function: Mapped["CodeFunction | None"] = relationship(back_populates="routes")


class CodeAssignment(IndexedEntity):
    __tablename__ = "code_assignments"

    target: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="assignments")


class ParseError(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "parse_errors"

    project_file_id: Mapped[UUID] = mapped_column(
        ForeignKey("project_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    project_file: Mapped["ProjectFile"] = relationship(back_populates="parse_errors")
