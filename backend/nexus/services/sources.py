from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_research import SourceIn, SourceOut
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..database.base import utcnow
from ..models import Source, User
from ..research.citations import crossref_lookup, format_citation
from . import activity


def to_out(s: Source) -> SourceOut:
    out = SourceOut.model_validate(s)
    out.citation = format_citation(s)
    return out


def list_sources(db: Session, user: User, q: str | None = None) -> list[Source]:
    stmt = select(Source).where(Source.owner_id == user.id)
    if q:
        stmt = stmt.where(Source.title.ilike(f"%{q}%"))
    return list(db.scalars(stmt.order_by(Source.title)))


def get_source(db: Session, user: User, source_id: int) -> Source:
    s = db.get(Source, source_id)
    if s is None or s.owner_id != user.id:
        raise NotFoundError("Fonte non trovata.")
    return s


def _check_primary(db: Session, user: User, primary_id: int | None, self_id: int | None = None) -> None:
    """La fonte primaria deve esistere, essere dell'utente e non creare cicli."""
    seen = {self_id} if self_id else set()
    cur = primary_id
    while cur is not None:
        if cur in seen:
            raise ValidationFailedError("La fonte primaria indicata crea un ciclo.")
        seen.add(cur)
        p = db.get(Source, cur)
        if p is None or p.owner_id != user.id:
            raise ValidationFailedError("Fonte primaria inesistente.")
        cur = p.primary_source_id


def create_source(db: Session, user: User, data: SourceIn, is_demo: bool = False) -> Source:
    _check_primary(db, user, data.primary_source_id)
    s = Source(owner_id=user.id, is_demo=is_demo, **data.model_dump())
    db.add(s)
    db.flush()
    activity.record(db, user=user, actor="user", action="source.create", entity_type="source", entity_id=s.id,
                    summary=f"Aggiunta la fonte «{s.title[:80]}»")
    db.commit()
    db.refresh(s)
    return s


def update_source(db: Session, user: User, source_id: int, data: SourceIn) -> Source:
    s = get_source(db, user, source_id)
    _check_primary(db, user, data.primary_source_id, s.id)
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    # Qualsiasi modifica invalida la verifica precedente.
    s.verification_status = "unverified"
    s.verification_note = "Modificata dopo l'ultima verifica."
    s.verified_at = None
    activity.record(db, user=user, actor="user", action="source.update", entity_type="source", entity_id=s.id,
                    summary=f"Modificata la fonte «{s.title[:80]}»")
    db.commit()
    db.refresh(s)
    return s


def delete_source(db: Session, user: User, source_id: int, confirm: bool) -> None:
    s = get_source(db, user, source_id)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare una fonte richiede conferma (confirm=true).")
    db.delete(s)
    activity.record(db, user=user, actor="user", action="source.delete", entity_type="source", entity_id=source_id,
                    summary=f"Eliminata la fonte «{s.title[:80]}»")
    db.commit()


def verify_source(db: Session, user: User, source_id: int, method: str, note: str) -> Source:
    s = get_source(db, user, source_id)
    if method == "user":
        s.verification_status = "verified_user"
        s.verification_note = note or "Controllata dall'utente sull'originale."
    else:
        if not s.doi:
            raise ValidationFailedError("La verifica su registro richiede un DOI.")
        result = crossref_lookup(s.doi)
        if result.status == "unavailable":
            raise ValidationFailedError(result.note)
        s.verification_status = result.status
        notes = [result.note]
        if result.status == "verified_registry":
            meta = result.metadata
            mismatches = []
            if meta.get("title") and meta["title"].strip().lower() != s.title.strip().lower():
                mismatches.append(f"titolo nel registro: «{meta['title']}»")
            if meta.get("year") and s.year and meta["year"] != s.year:
                mismatches.append(f"anno nel registro: {meta['year']}")
            if mismatches:
                notes.append("Discrepanze da controllare: " + "; ".join(mismatches))
        s.verification_note = " ".join(notes)
    s.verified_at = utcnow()
    activity.record(db, user=user, actor="user", action="source.verify", entity_type="source", entity_id=s.id,
                    summary=f"Verifica fonte «{s.title[:60]}»: {s.verification_status}")
    db.commit()
    db.refresh(s)
    return s


# --- BibTeX (Zotero, Mendeley, JabRef) -------------------------------------------------------


def export_bibtex(db: Session, user: User, ids: list[int] | None = None) -> str:
    from ..studio.bibtex import cite_key, source_to_bibtex

    items = list_sources(db, user)
    if ids:
        items = [x for x in items if x.id in set(ids)]
    taken: set[str] = set()
    return "\n".join(source_to_bibtex(x, cite_key(x.authors, x.year, x.title, taken)) for x in items)


def import_bibtex(db: Session, user: User, text: str) -> dict:
    from pydantic import ValidationError

    from ..studio.bibtex import entry_to_source, parse_bibtex

    try:
        entries = parse_bibtex(text)
    except ValueError as exc:
        raise ValidationFailedError(f"File BibTeX non leggibile: {exc}") from exc
    if not entries:
        raise ValidationFailedError("Nessuna voce BibTeX trovata nel file.")
    existing_doi = {x.doi.lower() for x in list_sources(db, user) if x.doi}
    created, skipped = [], []
    for e in entries:
        fields = entry_to_source(e)
        label = e.get("key") or fields["title"][:60] or "?"
        if fields["doi"] and fields["doi"].lower() in existing_doi:
            skipped.append({"key": label, "reason": "DOI già presente nella bibliografia"})
            continue
        try:
            data = SourceIn(**fields)
        except ValidationError as exc:
            skipped.append({"key": label, "reason": exc.errors()[0]["msg"][:200]})
            continue
        src = Source(owner_id=user.id, **data.model_dump())
        db.add(src)
        db.flush()
        created.append(src.id)
        if data.doi:
            existing_doi.add(data.doi.lower())
    activity.record(db, user=user, actor="user", action="source.import_bibtex", entity_type="source", entity_id=None,
                    summary=f"Importate {len(created)} fonti da BibTeX ({len(skipped)} scartate), tutte da verificare")
    db.commit()
    return {"created": len(created), "skipped": skipped}
