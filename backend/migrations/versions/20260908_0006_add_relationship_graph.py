"""Add relational code relationship graph.

Revision ID: 20260908_0006
Revises: 20260908_0005
Create Date: 2026-09-08 15:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0006"
down_revision: Union[str, None] = "20260908_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "graph_nodes",
        sa.Column("id", uuid, nullable=False),
        sa.Column("project_id", uuid, nullable=False),
        sa.Column("project_file_id", uuid, nullable=True),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("source_file", sa.String(length=1024), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("symbol_name", sa.String(length=1024), nullable=False),
        sa.Column("node_metadata", sa.JSON(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graph_nodes_project_id", "graph_nodes", ["project_id"])
    op.create_index(
        "ix_graph_nodes_project_file_id",
        "graph_nodes",
        ["project_file_id"],
    )
    op.create_table(
        "graph_edges",
        sa.Column("id", uuid, nullable=False),
        sa.Column("project_id", uuid, nullable=False),
        sa.Column("source_node_id", uuid, nullable=False),
        sa.Column("target_node_id", uuid, nullable=False),
        sa.Column("relationship_type", sa.String(length=50), nullable=False),
        sa.Column("edge_metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"],
            ["graph_nodes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"],
            ["graph_nodes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graph_edges_project_id", "graph_edges", ["project_id"])
    op.create_index(
        "ix_graph_edges_source_node_id",
        "graph_edges",
        ["source_node_id"],
    )
    op.create_index(
        "ix_graph_edges_target_node_id",
        "graph_edges",
        ["target_node_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_graph_edges_target_node_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_source_node_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_project_id", table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_index(
        "ix_graph_nodes_project_file_id",
        table_name="graph_nodes",
    )
    op.drop_index("ix_graph_nodes_project_id", table_name="graph_nodes")
    op.drop_table("graph_nodes")
