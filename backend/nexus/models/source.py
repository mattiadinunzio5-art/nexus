from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin

SOURCE_TYPES = ("book", "article", "chapter", "web", "dataset", "archive", "document", "other")
# unverified: inserita dall'utente, non controllata
# verified_user: l'utente dichiara di averla controllata sull'originale
# verified_registry: metadati confermati da un registro esterno (es. Crossref per i DOI)
# registry_mismatch: il DOI esiste ma i metadati del registro non corrispondono alla scheda (MAI verificata)
# registry_incomplete: il DOI esiste, nessuna discordanza, ma alla scheda mancano campi essenziali (autori, anno)
# not_found: il registro esterno non conosce l'identificativo indicato
VERIFICATION_STATES = ("unverified", "verified_user", "verified_registry", "registry_mismatch", "registry_incomplete", "not_found")
VERIFIED_STATES = ("verified_user", "verified_registry")
EVIDENCE_CLASSES = ("", "primary", "secondary")


class Source(TimestampMixin, Base):
    """Fonte bibliografica. Mai generata automaticamente: la crea l'utente
    (o un import con metadati reali) e il suo stato di verifica è esplicito."""

    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("owner_id", "origin", "external_id", name="uq_sources_origin_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="other", nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publisher: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    container: Mapped[str] = mapped_column(String(300), default="", nullable=False)  # rivista/volume
    pages: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    doi: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    isbn: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    url: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    accessed_at: Mapped[str] = mapped_column(String(10), default="", nullable=False)  # AAAA-MM-GG
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Licenza d'uso del testo o dei dati (es. CC BY 4.0, URL della licenza) e provenienza dei metadati della scheda.
    license: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    provenance: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    # Fonte primaria (documento d'epoca, dato originale) o secondaria (studio che la interpreta); "" = non indicato.
    evidence_class: Mapped[str] = mapped_column(String(12), default="", nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified", nullable=False)
    verification_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Fonte primaria da cui questa fonte riprende le informazioni (per valutare l'indipendenza delle conferme).
    primary_source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    # Lotto di importazione (es. "wikidata") e identificativo nella fonte (es. "Q12345"): idempotenza e cancellazione per lotto.
    origin: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
