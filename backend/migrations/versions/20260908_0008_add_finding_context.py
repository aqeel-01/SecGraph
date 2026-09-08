"""Add compact AI-ready context to findings.

Revision ID: 20260908_0008
Revises: 20260908_0007
Create Date: 2026-09-08 16:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260908_0008"
down_revision: Union[str, None] = "20260908_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "security_findings",
        sa.Column("context_package", sa.JSON(), nullable=True),
    )
    op.execute(
        "UPDATE security_findings "
        "SET context_package = '{}' "
        "WHERE context_package IS NULL"
    )
    op.alter_column("security_findings", "context_package", nullable=False)


def downgrade() -> None:
    op.drop_column("security_findings", "context_package")
