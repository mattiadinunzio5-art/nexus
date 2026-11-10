"""full-text index on document chunks (PostgreSQL only)

Revision ID: 0013
Revises: 0012
"""
from typing import Sequence, Union

from alembic import op


revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Su SQLite la ricerca usa già la tabella FTS5; l'indice serve solo a PostgreSQL.
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_fts ON document_chunks USING gin (to_tsvector('simple', text))")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_document_chunks_fts")
