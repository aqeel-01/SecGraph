"""Relational code relationship graph models."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.project_file import ProjectFile


class GraphNode(UUIDPrimaryKeyMixin, Base):
    """A symbol, file, route, module, or relevant call in a project."""

    __tablename__ = "graph_nodes"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("project_files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_file: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    node_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="graph_nodes")
    project_file: Mapped["ProjectFile | None"] = relationship()


class GraphEdge(UUIDPrimaryKeyMixin, Base):
    """A directed relationship between two graph nodes."""

    __tablename__ = "graph_edges"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    edge_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)

    project: Mapped["Project"] = relationship(back_populates="graph_edges")
    source_node: Mapped["GraphNode"] = relationship(
        foreign_keys=[source_node_id],
    )
    target_node: Mapped["GraphNode"] = relationship(
        foreign_keys=[target_node_id],
    )
