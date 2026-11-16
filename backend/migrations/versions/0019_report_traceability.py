"""reports: fonti consultate e cronologia delle versioni delle sezioni

Revision ID: 0019
Revises: 0018
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as b:
        # Fonti in bibliografia lette ma non citate nel testo («consultate»).
        b.add_column(sa.Column("consulted_ids", sa.JSON(), nullable=False, server_default="[]"))
    op.create_table(
        "report_section_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("report_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("embeds", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False, server_default="edit"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_report_section_versions_section_id", "report_section_versions", ["section_id"])
    op.create_index("ix_report_section_versions_report_id", "report_section_versions", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_report_section_versions_report_id", table_name="report_section_versions")
    op.drop_index("ix_report_section_versions_section_id", table_name="report_section_versions")
    op.drop_table("report_section_versions")
    with op.batch_alter_table("reports") as b:
        b.drop_column("consulted_ids")
