"""Static security finding model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.project_file import ProjectFile
    from app.models.code_index import APIRoute


class SecurityFinding(UUIDPrimaryKeyMixin, Base):
    """A normalized deterministic security rule result."""

    __tablename__ = "security_findings"

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
    route_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("api_routes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    file: Mapped[str] = mapped_column(String(1024), nullable=False)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    context_package: Mapped[dict] = mapped_column(JSON, nullable=False)

    project: Mapped["Project"] = relationship()
    project_file: Mapped["ProjectFile | None"] = relationship()
    route: Mapped["APIRoute | None"] = relationship()
