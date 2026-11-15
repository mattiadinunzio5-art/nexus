"""Sicurezza dei file: cestino dei documenti e registro dei controlli di integrità."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin, utcnow


class DeletedDocument(TimestampMixin, Base):
    """Documento eliminato: metadati e copia del file nel cestino, ripristinabili fino a ``purge_after``."""

    __tablename__ = "deleted_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    origin: Mapped[str] = mapped_column(String(40), nullable=False)
    origin_url: Mapped[str] = mapped_column(String(1000), default="", server_default="", nullable=False)
    license_note: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False)
    author: Mapped[str] = mapped_column(String(300), default="", server_default="", nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "" = il file originale mancava già al momento dell'eliminazione (si ripristinano solo i metadati: non possibile)
    trash_key: Mapped[str] = mapped_column(String(500), default="", server_default="", nullable=False)
    purge_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restored_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SystemCheck(Base):
    """Esito di un controllo di sistema (integrità dei file): manuale, programmato o da script."""

    __tablename__ = "system_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)  # ok | problems | failed
    trigger: Mapped[str] = mapped_column(String(12), default="manual", server_default="manual", nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
