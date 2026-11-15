"""project items: documents, sources, events, entities, series and relations linked to a project

Revision ID: 0017
Revises: 0016
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0017'
down_revision: Union[str, None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "item_type", "item_id", name="uq_project_item"),
    )
    op.create_index("ix_project_items_project_id", "project_items", ["project_id"])
    op.create_index("ix_project_items_item", "project_items", ["item_type", "item_id"])
    # I documenti già assegnati a un progetto diventano elementi del progetto.
    op.execute("INSERT INTO project_items (project_id, item_type, item_id, note, created_at, updated_at) "
               "SELECT project_id, 'document', id, '', created_at, created_at FROM documents WHERE project_id IS NOT NULL")


def downgrade() -> None:
    op.drop_index("ix_project_items_item", table_name="project_items")
    op.drop_index("ix_project_items_project_id", table_name="project_items")
    op.drop_table("project_items")
