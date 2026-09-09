"""Add pull request scan metadata.

Revision ID: 20260909_0012
Revises: 20260909_0011
Create Date: 2026-09-09 18:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260909_0012"
down_revision: Union[str, None] = "20260909_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column("trigger_type", sa.String(length=50), nullable=False, server_default="manual"),
    )
    op.add_column(
        "scans",
        sa.Column("pull_request_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scans",
        sa.Column("pull_request_sha", sa.String(length=40), nullable=True),
    )
    op.alter_column("scans", "trigger_type", server_default=None)


def downgrade() -> None:
    op.drop_column("scans", "pull_request_sha")
    op.drop_column("scans", "pull_request_number")
    op.drop_column("scans", "trigger_type")
