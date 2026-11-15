from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_research import SourceIn, SourceOut
from ..core.errors import ConfirmationRequiredError, ValidationFailedError
from ..database.base import utcnow
from ..models import Source, User
from ..research.citations import crossref_lookup, format_citation
from . import activity


def to_out(s: Source) -> SourceOut:
    out = SourceOut.model_validate(s)
    out.citation = format_citation(s)
    return out


def list_sources(db: Session, user: User, q: str | None = None, limit: int = 500, offset: int = 0,
                 origin: str | None = None, project_id: int | None = None) -> list[Source]:
    from ..core import library

    stmt = select(Source).where(Source.owner_id.in_(library.visible_owner_ids(db, user)))
    if origin == "mine":
        stmt = stmt.where(Source.owner_id == user.id)
    elif origin == "library":
        stmt = stmt.where(Source.owner_id != user.id)
    if project_id is not None:
        from . import project_scope

        stmt = stmt.where(project_scope.scope_filter(db, user, Source, "source", project_id))
    if q:
        from sqlalchemy import String, cast

        from ..research.crosslang import match_any

        # Per titolo o autore, in italiano e in inglese.
        stmt = stmt.where(match_any([Source.title, cast(Source.authors, String)], q))
    # Prima le fonti dell'utente, poi quelle della Biblioteca.
    return list(db.scalars(stmt.order_by((Source.owner_id != user.id), Source.title, Source.id).offset(offset).limit(limit)))


def get_source(db: Session, user: User, source_id: int, own: bool = False) -> Source:
    from ..core import library

    return library.access(db, user, db.get(Source, source_id), own, "Fonte non trovata.")


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
    if not s.provenance:
        s.provenance = "Inserita manualmente dall'utente"
    db.add(s)
    db.flush()
    activity.record(db, user=user, actor="user", action="source.create", entity_type="source", entity_id=s.id,
                    summary=f"Aggiunta la fonte «{s.title[:80]}»")
    db.commit()
    db.refresh(s)
    return s


def update_source(db: Session, user: User, source_id: int, data: SourceIn) -> Source:
    s = get_source(db, user, source_id, own=True)
    _check_primary(db, user, data.primary_source_id, s.id)
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    # Qualsiasi modifica invalida la verifica precedente.
    s.verification_status = "unverified"
    s.verification_note = "Modificata dopo l'ultima verifica."
    s.verified_at = None
    s.verification_details = None
    activity.record(db, user=user, actor="user", action="source.update", entity_type="source", entity_id=s.id,
                    summary=f"Modificata la fonte «{s.title[:80]}»")
    db.commit()
    db.refresh(s)
    return s


def delete_source(db: Session, user: User, source_id: int, confirm: bool) -> None:
    s = get_source(db, user, source_id, own=True)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare una fonte richiede conferma (confirm=true).")
    db.delete(s)
    activity.record(db, user=user, actor="user", action="source.delete", entity_type="source", entity_id=source_id,
                    summary=f"Eliminata la fonte «{s.title[:80]}»")
    db.commit()


def verify_source(db: Session, user: User, source_id: int, method: str, note: str) -> Source:
    from ..research.citations import compare_metadata, registry_verdict

    s = get_source(db, user, source_id, own=True)
    if method == "user":
        # La dichiarazione dell'utente non può coprire un'incoerenza segnalata dal registro sulla stessa scheda.
        if s.verification_status == "registry_mismatch":
            raise ValidationFailedError("Il registro segnala metadati discordanti per questo DOI: correggi i campi indicati "
                                        "(o il DOI) prima di dichiarare la fonte verificata.")
        s.verification_status = "verified_user"
        s.verification_note = note or "Controllata dall'utente sull'originale."
    else:
        if not s.doi:
            raise ValidationFailedError("La verifica su registro richiede un DOI.")
        result = crossref_lookup(s.doi)
        if result.status == "unavailable":
            raise ValidationFailedError(result.note)
        checked = utcnow().isoformat()
        if result.status == "not_found":
            s.verification_status = "not_found"
            s.verification_note = result.note
            s.verification_details = {"registry": "Crossref", "registry_url": result.metadata.get("registry_url", ""),
                                      "checked_at": checked, "doi_exists": False, "fields": {}}
        else:
            meta = result.metadata
            fields = compare_metadata(s, meta)
            s.verification_status, s.verification_note = registry_verdict(fields)
            s.verification_details = {
                "registry": meta.get("registry", "Crossref"), "registry_url": meta.get("registry_url", ""),
                "checked_at": checked, "doi_exists": True, "fields": fields,
                "registry_metadata": {k: meta.get(k) for k in ("title", "subtitle", "authors", "year", "container",
                                                               "publisher", "pages", "type", "url", "licenses")},
            }
            # Conserva URL e licenza dichiarati dal registro solo se la scheda non li ha già.
            if not s.url and meta.get("url"):
                s.url = meta["url"][:1000]
            if not s.license and meta.get("licenses"):
                s.license = meta["licenses"][0][:300]
            if not s.provenance:
                s.provenance = "Scheda dell'utente, confrontata con Crossref"
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
        src.provenance = src.provenance or f"Import BibTeX ({e.get('key') or 'voce senza chiave'})"
        db.add(src)
        db.flush()
        created.append(src.id)
        if data.doi:
            existing_doi.add(data.doi.lower())
    activity.record(db, user=user, actor="user", action="source.import_bibtex", entity_type="source", entity_id=None,
                    summary=f"Importate {len(created)} fonti da BibTeX ({len(skipped)} scartate), tutte da verificare")
    db.commit()
    return {"created": len(created), "skipped": skipped}
