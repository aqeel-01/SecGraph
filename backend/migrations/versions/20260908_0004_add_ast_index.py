"""Add Python AST index tables.

Revision ID: 20260908_0004
Revises: 20260908_0003
Create Date: 2026-09-08 14:35:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0004"
down_revision: Union[str, None] = "20260908_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def _entity_table(name: str, columns: list[sa.Column]) -> None:
    op.create_table(
        name,
        sa.Column("id", uuid, nullable=False),
        sa.Column("project_file_id", uuid, nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        *columns,
        sa.ForeignKeyConstraint(
            ["project_file_id"],
            ["project_files.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        f"ix_{name}_project_file_id",
        name,
        ["project_file_id"],
    )


def upgrade() -> None:
    _entity_table(
        "code_imports",
        [
            sa.Column("module", sa.String(length=512), nullable=False),
            sa.Column("imported_name", sa.String(length=255), nullable=True),
            sa.Column("alias", sa.String(length=255), nullable=True),
        ],
    )
    _entity_table(
        "code_classes",
        [
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("qualname", sa.String(length=1024), nullable=False),
            sa.Column("end_line", sa.Integer(), nullable=True),
        ],
    )
    _entity_table(
        "code_functions",
        [
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("qualname", sa.String(length=1024), nullable=False),
            sa.Column("end_line", sa.Integer(), nullable=True),
            sa.Column("is_async", sa.Boolean(), nullable=False),
        ],
    )
    op.create_table(
        "function_parameters",
        sa.Column("id", uuid, nullable=False),
        sa.Column("function_id", uuid, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["function_id"],
            ["code_functions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_function_parameters_function_id",
        "function_parameters",
        ["function_id"],
    )
    _entity_table(
        "code_decorators",
        [
            sa.Column("target_type", sa.String(length=50), nullable=False),
            sa.Column("target_name", sa.String(length=1024), nullable=False),
            sa.Column("expression", sa.Text(), nullable=False),
        ],
    )
    op.create_table(
        "function_calls",
        sa.Column("id", uuid, nullable=False),
        sa.Column("project_file_id", uuid, nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("function_id", uuid, nullable=True),
        sa.Column("expression", sa.Text(), nullable=False),
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
        "ix_function_calls_project_file_id",
        "function_calls",
        ["project_file_id"],
    )
    op.create_index(
        "ix_function_calls_function_id",
        "function_calls",
        ["function_id"],
    )
    _entity_table(
        "code_assignments",
        [
            sa.Column("target", sa.Text(), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
        ],
    )
    op.create_table(
        "parse_errors",
        sa.Column("id", uuid, nullable=False),
        sa.Column("project_file_id", uuid, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("column_number", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_file_id"],
            ["project_files.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_parse_errors_project_file_id",
        "parse_errors",
        ["project_file_id"],
    )


def downgrade() -> None:
    for name in (
        "parse_errors",
        "code_assignments",
        "function_calls",
        "code_decorators",
        "function_parameters",
        "code_functions",
        "code_classes",
        "code_imports",
    ):
        op.drop_table(name)
