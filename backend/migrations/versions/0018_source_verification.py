"""sources: verifica campo per campo, licenza, provenienza, fonte primaria/secondaria

Revision ID: 0018
Revises: 0017
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sources") as b:
        b.add_column(sa.Column("license", sa.String(300), nullable=False, server_default=""))
        b.add_column(sa.Column("provenance", sa.String(300), nullable=False, server_default=""))
        # primary | secondary | "" (non indicato)
        b.add_column(sa.Column("evidence_class", sa.String(12), nullable=False, server_default=""))
        # Esito dettagliato dell'ultima verifica su registro (campi, metadati del registro, URL, data).
        b.add_column(sa.Column("verification_details", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sources") as b:
        b.drop_column("verification_details")
        b.drop_column("evidence_class")
        b.drop_column("provenance")
        b.drop_column("license")
