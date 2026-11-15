"""knowledge_items: data del fatto, data di pubblicazione e data di disponibilità separate

Revision ID: 0020
Revises: 0019
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0020'
down_revision: Union[str, None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("knowledge_items") as b:
        # Date in forma AAAA, AAAA-MM o AAAA-MM-GG ("" = non indicata).
        b.add_column(sa.Column("refers_to", sa.String(10), nullable=False, server_default=""))
        b.add_column(sa.Column("published_on", sa.String(10), nullable=False, server_default=""))
        b.add_column(sa.Column("available_on", sa.String(10), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("knowledge_items") as b:
        b.drop_column("available_on")
        b.drop_column("published_on")
        b.drop_column("refers_to")
