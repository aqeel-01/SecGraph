"""Add normalized static security findings.

Revision ID: 20260908_0007
Revises: 20260908_0006
Create Date: 2026-09-08 15:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0007"
down_revision: Union[str, None] = "20260908_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "security_findings",
        sa.Column("id", uuid, nullable=False),
        sa.Column("project_id", uuid, nullable=False),
        sa.Column("project_file_id", uuid, nullable=True),
        sa.Column("route_id", uuid, nullable=True),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("file", sa.String(length=1024), nullable=False),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_file_id"],
            ["project_files.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["api_routes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_findings_project_id", "security_findings", ["project_id"])
    op.create_index(
        "ix_security_findings_project_file_id",
        "security_findings",
        ["project_file_id"],
    )
    op.create_index(
        "ix_security_findings_route_id",
        "security_findings",
        ["route_id"],
    )
    op.create_index(
        "ix_security_findings_rule_id",
        "security_findings",
        ["rule_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_security_findings_rule_id", table_name="security_findings")
    op.drop_index("ix_security_findings_route_id", table_name="security_findings")
    op.drop_index(
        "ix_security_findings_project_file_id",
        table_name="security_findings",
    )
    op.drop_index("ix_security_findings_project_id", table_name="security_findings")
    op.drop_table("security_findings")
