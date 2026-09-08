"""Add detected FastAPI routes.

Revision ID: 20260908_0005
Revises: 20260908_0004
Create Date: 2026-09-08 14:55:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0005"
down_revision: Union[str, None] = "20260908_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_routes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "project_file_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column(
            "function_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("http_method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=2048), nullable=False),
        sa.Column("function_name", sa.String(length=255), nullable=False),
        sa.Column("router_name", sa.String(length=512), nullable=False),
        sa.Column("decorator_expression", sa.Text(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_file_id"],
            ["project_files.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["function_id"],
            ["code_functions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_api_routes_project_file_id",
        "api_routes",
        ["project_file_id"],
    )
    op.create_index(
        "ix_api_routes_function_id",
        "api_routes",
        ["function_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_api_routes_function_id", table_name="api_routes")
    op.drop_index("ix_api_routes_project_file_id", table_name="api_routes")
    op.drop_table("api_routes")
