"""Project database model."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.graph import GraphEdge, GraphNode
    from app.models.project_file import ProjectFile
    from app.models.scan import Scan


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A backend project submitted for future security analysis."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    python_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    backend_framework: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    scans: Mapped[list["Scan"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    files: Mapped[list["ProjectFile"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    graph_nodes: Mapped[list["GraphNode"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    graph_edges: Mapped[list["GraphEdge"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
