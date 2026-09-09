"""Add external project source metadata.

Revision ID: 20260909_0011
Revises: 20260909_0010
Create Date: 2026-09-09 18:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260909_0011"
down_revision: Union[str, None] = "20260909_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("source_url", sa.String(length=2048), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("source_ref", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "source_ref")
    op.drop_column("projects", "source_url")
