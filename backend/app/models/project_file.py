"""Project source file metadata model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.code_index import (
        APIRoute,
        CodeAssignment,
        CodeClass,
        CodeDecorator,
        CodeFunction,
        CodeImport,
        FunctionCall,
        ParseError,
    )
    from app.models.project import Project


class ProjectFile(UUIDPrimaryKeyMixin, Base):
    """Metadata for a relevant source file in an uploaded project."""

    __tablename__ = "project_files"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    project: Mapped["Project"] = relationship(back_populates="files")
    imports: Mapped[list["CodeImport"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
    classes: Mapped[list["CodeClass"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
    functions: Mapped[list["CodeFunction"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
    decorators: Mapped[list["CodeDecorator"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
    calls: Mapped[list["FunctionCall"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
    routes: Mapped[list["APIRoute"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list["CodeAssignment"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
    parse_errors: Mapped[list["ParseError"]] = relationship(
        back_populates="project_file",
        cascade="all, delete-orphan",
    )
