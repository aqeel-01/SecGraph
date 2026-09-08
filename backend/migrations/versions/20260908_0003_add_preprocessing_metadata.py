"""Add project preprocessing metadata.

Revision ID: 20260908_0003
Revises: 20260907_0002
Create Date: 2026-09-08 14:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0003"
down_revision: Union[str, None] = "20260907_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("python_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("backend_framework", sa.String(length=100), nullable=True),
    )
    op.create_table(
        "project_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_files_project_id",
        "project_files",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_files_project_id", table_name="project_files")
    op.drop_table("project_files")
    op.drop_column("projects", "backend_framework")
    op.drop_column("projects", "python_version")
