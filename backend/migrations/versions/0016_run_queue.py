"""persistent research queue: attempts, heartbeat, retry time, checkpoint

Revision ID: 0016
Revises: 0015
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0016'
down_revision: Union[str, None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("research_runs") as b:
        b.add_column(sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        b.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
        b.add_column(sa.Column("checkpoint", sa.JSON(), nullable=False, server_default="{}"))
        b.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_research_runs_status", "research_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_research_runs_status", table_name="research_runs")
    with op.batch_alter_table("research_runs") as b:
        for c in ("started_at", "checkpoint", "next_attempt_at", "heartbeat_at", "attempts"):
            b.drop_column(c)
