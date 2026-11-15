"""project research design: question, objectives, period, scope

Revision ID: 0015
Revises: 0014
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as b:
        b.add_column(sa.Column("research_question", sa.Text(), nullable=False, server_default=""))
        b.add_column(sa.Column("objectives", sa.Text(), nullable=False, server_default=""))
        b.add_column(sa.Column("scope", sa.Text(), nullable=False, server_default=""))
        b.add_column(sa.Column("period_start", sa.Integer(), nullable=True))
        b.add_column(sa.Column("period_end", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as b:
        for c in ("period_end", "period_start", "scope", "objectives", "research_question"):
            b.drop_column(c)
