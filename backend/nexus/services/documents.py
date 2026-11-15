"""Importazione, indicizzazione e gestione dei documenti."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_research import DocumentUpdate
from ..core.config import Settings
from ..core.errors import ConfirmationRequiredError, NexusError, ValidationFailedError
from ..core.logging import logger
from ..models import Document, DocumentChunk, Project, Source, User
from ..research import index
from ..research.chunking import chunk_sections
from ..research.extract import ExtractionError, detect_kind, extract
from ..research.safety import looks_like_injection
from . import activity, quotas


class DuplicateDocumentError(NexusError):
    status_code = 409
    code = "duplicate_document"


def _check_refs(db: Session, user: User, project_id: int | None, source_id: int | None) -> None:
    if project_id is not None:
        p = db.get(Project, project_id)
        if p is None or p.owner_id != user.id:
            raise ValidationFailedError("Progetto inesistente.")
    if source_id is not None:
        s = db.get(Source, source_id)
        if s is None or s.owner_id != user.id:
            raise ValidationFailedError("Fonte inesistente.")


def import_bytes(
    db: Session,
    user: User,
    settings: Settings,
    *,
    filename: str,
    data: bytes,
    title: str | None = None,
    category: str = "source_material",
    project_id: int | None = None,
    origin: str = "upload",
    origin_url: str = "",
    license_note: str = "",
    author: str = "",
    is_demo: bool = False,
) -> Document:
    if not data:
        raise ValidationFailedError("Il file è vuoto.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValidationFailedError(f"File troppo grande (massimo {settings.max_upload_mb} MB).")
    quotas.check(db, user, "documents", extra_bytes=len(data))
    _check_refs(db, user, project_id, None)
    from ..core import library, licenses

    if library.is_library(db, user.id) and licenses.for_document(origin, origin_url) is None:
        # Copyright & Data Policy: nella Biblioteca entrano solo testi con una scheda nel registro delle licenze.
        raise ValidationFailedError("Biblioteca NEXUS: questo testo non ha una licenza registrata (core/licenses.py).")
    filename = Path(filename).name[:300] or "documento"
    try:
        kind = detect_kind(filename, data[:8192])
    except ExtractionError as exc:
        raise ValidationFailedError(str(exc)) from exc

    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.owner_id == user.id, Document.sha256 == sha))
    if existing:
        raise DuplicateDocumentError("Documento già presente nell'archivio.", details={"document_id": existing.id})

    try:
        extracted = extract(kind, data)
    except ExtractionError as exc:
        raise ValidationFailedError(str(exc)) from exc

    from . import storage

    key = f"uploads/{user.id}/{sha}.{kind}"
    st = storage.for_settings(settings)
    st.put(key, data)
    # Upload controllato: il file deve risultare nello storage con la dimensione giusta prima di registrare il documento.
    if st.stat(key) != len(data):
        raise storage.StorageError("Il file caricato non risulta salvato correttamente nello storage: riprova.")
    try:
        return _register(db, user, settings, key, data, filename, kind, sha, extracted, title, category, project_id, origin, origin_url,
                         license_note, author, is_demo)
    except Exception:
        # Se il database non registra il documento, il file non deve restare orfano.
        db.rollback()
        try:
            st.delete(key)
        except Exception:  # noqa: BLE001 - lo troverà il controllo di integrità
            pass
        raise


def _register(db, user, settings, key, data, filename, kind, sha, extracted, title, category, project_id, origin, origin_url,
              license_note, author, is_demo) -> Document:
    chunks = chunk_sections(extracted.sections)
    doc = Document(
        owner_id=user.id,
        project_id=project_id,
        title=(title or extracted.title or Path(filename).stem)[:300],
        filename=filename,
        kind=kind,
        category=category,
        origin=origin,
        origin_url=origin_url,
        license_note=license_note,
        author=(author or extracted.author or "")[:300],
        sha256=sha,
        size_bytes=len(data),
        storage_path=key,
        page_count=extracted.page_count,
        char_count=sum(len(s.text) for s in extracted.sections),
        chunk_count=len(chunks),
        is_demo=is_demo,
    )
    db.add(doc)
    db.flush()
    rows = []
    for i, c in enumerate(chunks):
        flag = looks_like_injection(c.text)
        rows.append(
            DocumentChunk(document_id=doc.id, owner_id=user.id, ordinal=i, page=c.page, locator=c.locator, text=c.text, injection_flag=flag)
        )
    db.add_all(rows)
    db.flush()
    doc.flagged_chunks = sum(1 for r in rows if r.injection_flag)
    _embed_neural(settings, rows)
    index.fts_add(db, rows)
    activity.record(
        db, user=user, actor="user", action="document.import", entity_type="document", entity_id=doc.id,
        summary=f"Importato «{doc.title}» ({kind.upper()}, {len(rows)} segmenti"
        + (f", {doc.flagged_chunks} segnalati come possibili istruzioni" if doc.flagged_chunks else "") + ")",
    )
    db.commit()
    index.semantic_index.invalidate(user.id)
    db.refresh(doc)
    return doc


def _embed_neural(settings: Settings, rows: list[DocumentChunk]) -> None:
    if settings.embeddings != "sentence-transformers" or not rows:
        return
    try:
        emb = index.NeuralEmbedder(settings.embedding_model)
        vecs = emb.encode([r.text for r in rows])
        for r, v in zip(rows, vecs):
            r.embedding = np.asarray(v, dtype=np.float32).tobytes()
            r.embedding_model = emb.name
    except Exception as exc:  # noqa: BLE001
        # Gli embedding neurali sono facoltativi: si ripiega su LSA, segnalandolo nel log.
        logger.warning("Embedding neurali non disponibili, uso LSA: %s", exc)


GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
GUTENBERG_LICENSE = (
    "Project Gutenberg: opera in pubblico dominio negli Stati Uniti secondo il catalogo. "
    "Verificare lo status nel proprio paese. Il marchio 'Project Gutenberg' ha condizioni d'uso proprie."
)


def import_gutenberg(db: Session, user: User, settings: Settings, ebook_id: int, title: str, author: str, project_id: int | None) -> Document:
    """Scarica UN testo richiesto dall'utente (nessuna raccolta automatica massiva)."""
    url = GUTENBERG_URL.format(id=ebook_id)
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "NEXUS/0.1 (single user-requested download)"}) as c:
            r = c.get(url)
    except httpx.HTTPError as exc:
        raise ValidationFailedError(f"Project Gutenberg non raggiungibile: {type(exc).__name__}") from exc
    if r.status_code != 200:
        raise ValidationFailedError(f"Testo non disponibile (HTTP {r.status_code}). Verifica l'ID dell'ebook.")
    return import_bytes(
        db, user, settings, filename=f"gutenberg-{ebook_id}.txt", data=r.content, title=title, author=author,
        project_id=project_id, origin="gutenberg", origin_url=f"https://www.gutenberg.org/ebooks/{ebook_id}",
        license_note=GUTENBERG_LICENSE,
    )


def list_documents(db: Session, user: User, project_id: int | None = None, category: str | None = None,
                   origin: str | None = None) -> list[Document]:
    from ..core import library
    from . import project_scope

    stmt = select(Document).where(Document.owner_id.in_(library.visible_owner_ids(db, user)))
    if origin == "mine":
        stmt = stmt.where(Document.owner_id == user.id)
    elif origin == "library":
        stmt = stmt.where(Document.owner_id != user.id)
    if project_id is not None:
        stmt = stmt.where(project_scope.scope_filter(db, user, Document, "document", project_id))
    if category:
        stmt = stmt.where(Document.category == category)
    return list(db.scalars(stmt.order_by(Document.created_at.desc())))


def get_document(db: Session, user: User, document_id: int, own: bool = False) -> Document:
    from ..core import library

    return library.access(db, user, db.get(Document, document_id), own, "Documento non trovato.")


def get_chunks(db: Session, user: User, document_id: int, offset: int = 0, limit: int = 50) -> list[DocumentChunk]:
    get_document(db, user, document_id)
    return list(
        db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.ordinal).offset(offset).limit(limit)
        )
    )


def update_document(db: Session, user: User, document_id: int, data: DocumentUpdate) -> Document:
    d = get_document(db, user, document_id, own=True)
    changes = data.model_dump(exclude_unset=True)
    _check_refs(db, user, changes.get("project_id"), changes.get("source_id"))
    for k, v in changes.items():
        setattr(d, k, v)
    activity.record(db, user=user, actor="user", action="document.update", entity_type="document", entity_id=d.id,
                    summary=f"Modificati i metadati di «{d.title}»")
    db.commit()
    db.refresh(d)
    return d


def delete_document(db: Session, user: User, settings: Settings, document_id: int, confirm: bool) -> dict:
    """Eliminazione recuperabile e verificata sullo storage (vedi services/filesafety.py)."""
    from . import filesafety

    return filesafety.delete_document(db, user, settings, document_id, confirm)


def file_bytes(settings: Settings, d: Document) -> bytes:
    from . import storage

    return storage.for_settings(settings).get(d.storage_path)
