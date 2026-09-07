"""Add project storage path.

Revision ID: 20260907_0002
Revises: 20260907_0001
Create Date: 2026-09-07 21:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_0002"
down_revision: Union[str, None] = "20260907_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
    )
    op.execute(
        "UPDATE projects SET storage_path = '' WHERE storage_path IS NULL"
    )
    op.alter_column("projects", "storage_path", nullable=False)


def downgrade() -> None:
    op.drop_column("projects", "storage_path")
