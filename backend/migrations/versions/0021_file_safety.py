"""file: cestino dei documenti (eliminazione recuperabile) e registro dei controlli di integrità

Revision ID: 0021
Revises: 0020
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0021'
down_revision: Union[str, None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deleted_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("origin", sa.String(40), nullable=False),
        sa.Column("origin_url", sa.String(1000), nullable=False, server_default=""),
        sa.Column("license_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("author", sa.String(300), nullable=False, server_default=""),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("trash_key", sa.String(500), nullable=False, server_default=""),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_document_id", sa.Integer(), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deleted_documents_owner_id", "deleted_documents", ["owner_id"])
    op.create_table(
        "system_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("trigger", sa.String(12), nullable=False, server_default="manual"),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_system_checks_kind", "system_checks", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_system_checks_kind", table_name="system_checks")
    op.drop_table("system_checks")
    op.drop_index("ix_deleted_documents_owner_id", table_name="deleted_documents")
    op.drop_table("deleted_documents")
