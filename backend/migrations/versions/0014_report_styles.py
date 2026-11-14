"""report citation style and template

Revision ID: 0014
Revises: 0013
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("reports") as b:
        b.add_column(sa.Column("citation_style", sa.String(20), nullable=False, server_default="numeric"))
        b.add_column(sa.Column("template", sa.String(20), nullable=False, server_default="standard"))


def downgrade() -> None:
    with op.batch_alter_table("reports") as b:
        b.drop_column("template")
        b.drop_column("citation_style")
