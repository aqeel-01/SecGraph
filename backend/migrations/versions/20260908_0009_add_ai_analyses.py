"""Add AI routing and provider analysis records.

Revision ID: 20260908_0009
Revises: 20260908_0008
Create Date: 2026-09-08 20:35:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0009"
down_revision: Union[str, None] = "20260908_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["finding_id"],
            ["security_findings.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_analyses_finding_id", "ai_analyses", ["finding_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_analyses_finding_id", table_name="ai_analyses")
    op.drop_table("ai_analyses")
