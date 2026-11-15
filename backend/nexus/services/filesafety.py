"""File dei documenti: eliminazione recuperabile e verificata, ripristino, file orfani, integrità.

Regole:
* un'eliminazione è «completata» solo dopo aver verificato sullo storage che la copia nel cestino
  esiste con la dimensione giusta e che il file originale non esiste più; se una verifica fallisce,
  il documento resta com'era e l'utente riceve un errore esplicito;
* il cestino conserva file e metadati per ``trash_days`` giorni: il ripristino reimporta il file
  (stesso contenuto, verificato con lo SHA-256);
* il controllo di integrità confronta database e storage: documenti senza file, file senza documento
  (orfani), dimensioni diverse, copie del cestino scadute. Gira da solo ogni ``integrity_interval_hours``
  ore, dall'area amministratore o con ``scripts/storage_check.py``.
"""

from __future__ import annotations

import hashlib
import time
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..core.logging import logger
from ..database.base import utcnow
from ..models import DeletedDocument, Document, SystemCheck, User
from . import activity, storage

TRASH = "trash"
UPLOADS = "uploads"


def _verify_absent(st, key: str) -> None:
    if st.stat(key) is not None:
        raise storage.StorageError("Il file risulta ancora presente nello storage dopo la cancellazione: operazione annullata.")


def delete_document(db: Session, user: User, settings: Settings, document_id: int, confirm: bool) -> dict:
    from ..research import index
    from . import documents

    d = documents.get_document(db, user, document_id, own=True)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un documento dall'archivio richiede conferma (confirm=true).")
    st = storage.for_settings(settings)
    key, size = d.storage_path, st.stat(d.storage_path)
    trash_key = ""
    if size is not None:
        # 1) copia nel cestino e verifica (dimensione) PRIMA di toccare il database
        trash_key = f"{TRASH}/{d.owner_id}/{d.sha256}.{d.kind}.{int(time.time() * 1000)}"
        st.copy(key, trash_key)
        if st.stat(trash_key) != size:
            raise storage.StorageError("La copia di sicurezza nel cestino non è verificabile: documento NON eliminato.")
    rec = DeletedDocument(owner_id=d.owner_id, document_id=d.id, title=d.title, filename=d.filename, kind=d.kind, category=d.category,
                          origin=d.origin, origin_url=d.origin_url, license_note=d.license_note, author=d.author, sha256=d.sha256,
                          size_bytes=d.size_bytes, project_id=d.project_id, source_id=d.source_id, trash_key=trash_key,
                          purge_after=utcnow() + timedelta(days=settings.trash_days))
    db.add(rec)
    index.fts_delete_document(db, d.id)
    db.delete(d)
    db.flush()
    # 2) cancellazione dell'originale e verifica; se fallisce si annulla tutto
    try:
        if size is not None:
            st.delete(key)
            _verify_absent(st, key)
    except Exception:
        db.rollback()
        if trash_key:
            try:
                st.delete(trash_key)
            except Exception:  # noqa: BLE001 - resta un file nel cestino senza record: lo trova il controllo di integrità
                logger.warning("Copia nel cestino non rimossa dopo un errore: %s", trash_key)
        raise
    activity.record(db, user=user, actor="user", action="document.delete", entity_type="document", entity_id=document_id,
                    summary=f"Eliminato il documento «{rec.title}» (recuperabile dal cestino fino al {rec.purge_after:%d/%m/%Y})"
                    if trash_key else f"Eliminato il documento «{rec.title}» (il file originale mancava già)")
    db.commit()
    index.semantic_index.invalidate(user.id)
    return {"deleted": True, "storage_verified": True, "trash_id": rec.id, "recoverable": bool(trash_key),
            "recoverable_until": rec.purge_after.isoformat() if trash_key else None}


def list_trash(db: Session, user: User) -> list[DeletedDocument]:
    return list(db.scalars(select(DeletedDocument).where(DeletedDocument.owner_id == user.id, DeletedDocument.restored_at.is_(None),
                                                         DeletedDocument.purged_at.is_(None)).order_by(DeletedDocument.id.desc())))


def _own_trash(db: Session, user: User, trash_id: int) -> DeletedDocument:
    t = db.get(DeletedDocument, trash_id)
    if t is None or t.owner_id != user.id or t.restored_at or t.purged_at:
        raise NotFoundError("Elemento del cestino non trovato.")
    return t


def restore(db: Session, user: User, settings: Settings, trash_id: int) -> Document:
    from . import documents

    t = _own_trash(db, user, trash_id)
    if not t.trash_key:
        raise ValidationFailedError("Il file originale mancava già quando il documento è stato eliminato: non è ripristinabile.")
    st = storage.for_settings(settings)
    data = st.get(t.trash_key)
    if hashlib.sha256(data).hexdigest() != t.sha256:
        raise storage.StorageError("Il file nel cestino non corrisponde all'originale (SHA-256 diverso): ripristino annullato.")
    project_id = t.project_id
    if project_id is not None:
        from . import sharing

        if sharing.RANK.get(sharing.role_in(db, user, project_id) or "", 0) < sharing.RANK["editor"]:
            project_id = None
    doc = documents.import_bytes(db, user, settings, filename=t.filename, data=data, title=t.title, category=t.category,
                                 project_id=project_id, origin=t.origin, origin_url=t.origin_url, license_note=t.license_note, author=t.author)
    if t.source_id is not None:
        from ..models import Source

        src = db.get(Source, t.source_id)
        if src is not None and src.owner_id == user.id:
            doc.source_id = src.id
    t.restored_at, t.restored_document_id = utcnow(), doc.id
    activity.record(db, user=user, actor="user", action="document.restore", entity_type="document", entity_id=doc.id,
                    summary=f"Ripristinato dal cestino «{doc.title}»")
    db.commit()
    try:
        st.delete(t.trash_key)
    except Exception:  # noqa: BLE001 - il documento è ripristinato; la copia residua la rimuove il controllo di integrità
        logger.warning("Copia nel cestino non rimossa dopo il ripristino: %s", t.trash_key)
    db.refresh(doc)
    return doc


def purge(db: Session, user: User | None, settings: Settings, t: DeletedDocument) -> None:
    """Cancellazione definitiva (verificata) della copia nel cestino."""
    st = storage.for_settings(settings)
    if t.trash_key:
        st.delete(t.trash_key)
        _verify_absent(st, t.trash_key)
    t.purged_at = utcnow()
    if user is not None:
        activity.record(db, user=user, actor="user", action="document.purge", entity_type="document", entity_id=t.document_id,
                        summary=f"Eliminato definitivamente dal cestino «{t.title}»")
    db.commit()


def purge_one(db: Session, user: User, settings: Settings, trash_id: int, confirm: bool) -> None:
    if not confirm:
        raise ConfirmationRequiredError("L'eliminazione definitiva richiede conferma (confirm=true): non si potrà più recuperare.")
    purge(db, user, settings, _own_trash(db, user, trash_id))


# --- Integrità e file orfani --------------------------------------------------------------------------------


def scan(db: Session, settings: Settings, hash_sample: int = 20) -> dict:
    """Confronto database ↔ storage. Sola lettura."""
    st = storage.for_settings(settings)
    files = {**st.list(UPLOADS), **st.list(TRASH)}
    docs = list(db.execute(select(Document.id, Document.owner_id, Document.storage_path, Document.size_bytes, Document.sha256)))
    trash = list(db.scalars(select(DeletedDocument).where(DeletedDocument.restored_at.is_(None), DeletedDocument.purged_at.is_(None),
                                                         DeletedDocument.trash_key != "")))
    known = {d.storage_path for d in docs} | {t.trash_key for t in trash}
    missing, size_mismatch, hash_mismatch = [], [], []
    for d in docs:
        sz = files.get(d.storage_path)
        if sz is None:
            missing.append({"document_id": d.id, "owner_id": d.owner_id, "key": d.storage_path})
        elif sz != d.size_bytes:
            size_mismatch.append({"document_id": d.id, "key": d.storage_path, "expected": d.size_bytes, "found": sz})
    # SHA-256 su un campione (i più recenti): verifica il contenuto, non solo la presenza.
    for d in sorted(docs, key=lambda x: -x.id)[:hash_sample]:
        if d.storage_path in files:
            try:
                if hashlib.sha256(st.get(d.storage_path)).hexdigest() != d.sha256:
                    hash_mismatch.append({"document_id": d.id, "key": d.storage_path})
            except Exception as exc:  # noqa: BLE001
                hash_mismatch.append({"document_id": d.id, "key": d.storage_path, "error": type(exc).__name__})
    trash_missing = [{"trash_id": t.id, "key": t.trash_key} for t in trash if t.trash_key not in files]
    now = utcnow()
    expired = [t.id for t in trash if (t.purge_after if t.purge_after.tzinfo else t.purge_after.replace(tzinfo=now.tzinfo)) < now]
    orphans = sorted(k for k in files if k not in known)
    problems = len(missing) + len(size_mismatch) + len(hash_mismatch) + len(trash_missing) + len(orphans)
    return {"documents": len(docs), "files": len(files), "trash_items": len(trash), "hash_checked": min(hash_sample, len(docs)),
            "missing_files": missing, "size_mismatch": size_mismatch, "hash_mismatch": hash_mismatch, "trash_missing": trash_missing,
            "orphan_files": [{"key": k, "size": files[k]} for k in orphans], "expired_trash": expired, "problems": problems}


def run_check(db: Session, settings: Settings, trigger: str = "manual") -> SystemCheck:
    chk = SystemCheck(kind="storage_integrity", status="failed", trigger=trigger, result={}, started_at=utcnow())
    db.add(chk)
    db.commit()
    try:
        res = scan(db, settings)
        chk.status = "problems" if res["problems"] else "ok"
        chk.result = res
    except Exception as exc:  # noqa: BLE001 - l'esito del controllo resta registrato
        chk.result = {"error": f"{type(exc).__name__}: {exc}"[:500]}
    chk.finished_at = utcnow()
    db.commit()
    db.refresh(chk)
    if chk.status != "ok":
        logger.warning("Controllo di integrità dei file: %s (%s)", chk.status, {k: len(v) for k, v in chk.result.items() if isinstance(v, list)})
    return chk


def cleanup(db: Session, settings: Settings, admin: User | None, confirm: bool, orphans: bool = True, expired: bool = True) -> dict:
    """Rimuove (con verifica) i file orfani e le copie del cestino scadute. Mai i file referenziati da un documento."""
    if not confirm:
        raise ConfirmationRequiredError("La pulizia elimina file in modo definitivo: serve confirm=true.")
    res = scan(db, settings, hash_sample=0)
    st = storage.for_settings(settings)
    removed, failed = [], []
    if orphans:
        for o in res["orphan_files"]:
            try:
                st.delete(o["key"])
                _verify_absent(st, o["key"])
                removed.append(o["key"])
            except Exception as exc:  # noqa: BLE001
                failed.append({"key": o["key"], "error": str(exc)[:200]})
    purged = []
    if expired:
        for tid in res["expired_trash"]:
            t = db.get(DeletedDocument, tid)
            try:
                purge(db, None, settings, t)
                purged.append(tid)
            except Exception as exc:  # noqa: BLE001
                failed.append({"trash_id": tid, "error": str(exc)[:200]})
    if admin is not None:
        activity.record(db, user=admin, actor="user", action="admin.storage_cleanup", entity_type="system", entity_id=None,
                        summary=f"Pulizia dello storage: {len(removed)} file orfani rimossi, {len(purged)} elementi del cestino scaduti")
        db.commit()
    return {"removed_orphans": removed, "purged_trash": purged, "failed": failed}


def last_check(db: Session) -> SystemCheck | None:
    return db.scalar(select(SystemCheck).where(SystemCheck.kind == "storage_integrity").order_by(SystemCheck.id.desc()).limit(1))


def due(db: Session, settings: Settings) -> bool:
    if settings.integrity_interval_hours <= 0:
        return False
    last = last_check(db)
    if last is None:
        return True
    at = last.started_at if last.started_at.tzinfo else last.started_at.replace(tzinfo=utcnow().tzinfo)
    return utcnow() - at >= timedelta(hours=settings.integrity_interval_hours)


def check_out(c: SystemCheck | None) -> dict | None:
    if c is None:
        return None
    return {"id": c.id, "status": c.status, "trigger": c.trigger, "started_at": c.started_at.isoformat(),
            "finished_at": c.finished_at.isoformat() if c.finished_at else None, "result": c.result}
