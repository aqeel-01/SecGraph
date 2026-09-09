"""Add validated AI explanation output.

Revision ID: 20260909_0010
Revises: 20260908_0009
Create Date: 2026-09-09 14:50:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260909_0010"
down_revision: Union[str, None] = "20260908_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_analyses",
        sa.Column("explanation_status", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "ai_analyses",
        sa.Column("structured_output", sa.JSON(), nullable=True),
    )
    op.add_column(
        "ai_analyses",
        sa.Column("validation_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_analyses", "validation_error")
    op.drop_column("ai_analyses", "structured_output")
    op.drop_column("ai_analyses", "explanation_status")
