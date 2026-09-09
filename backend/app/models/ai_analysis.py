"""AI routing and provider result persistence."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.finding import SecurityFinding


class AIAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Record of one routing decision and its provider attempts."""

    __tablename__ = "ai_analyses"

    finding_id: Mapped[UUID] = mapped_column(
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    structured_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[list[dict]] = mapped_column(JSON, nullable=False)

    finding: Mapped["SecurityFinding"] = relationship(
        back_populates="ai_analyses",
    )
