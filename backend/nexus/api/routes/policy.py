"""NEXUS Copyright & Data Policy: registro pubblico delle licenze (nessun accesso richiesto)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from ...core import library, licenses
from ..deps import DB

router = APIRouter(tags=["policy"])


def _library_counts(db: DB) -> dict[str, dict[str, int]]:
    """Quanti elementi della Biblioteca usano ciascuna scheda (serie, documenti, eventi, entità, relazioni)."""
    from ...models import Document, Entity, HistoricalEvent, Relation, Series, Source

    lib = library.library_user_id(db)
    counts: dict[str, dict[str, int]] = {}
    if lib is None:
        return counts

    def add(lid: str | None, kind: str, n: int = 1) -> None:
        if lid and n:
            counts.setdefault(lid, {}).setdefault(kind, 0)
            counts[lid][kind] += n

    for url, sid in db.execute(select(Series.source_url, Series.source_series_id).where(Series.owner_id == lib)):
        add(licenses.for_series(url, sid), "series")
    for origin, url in db.execute(select(Document.origin, Document.origin_url).where(Document.owner_id == lib)):
        add(licenses.for_document(origin, url), "documents")
    own = lambda m: select(func.count()).select_from(m).where(m.owner_id == lib)  # noqa: E731
    add("wikidata", "events", db.scalar(own(HistoricalEvent)) or 0)
    # Entità da Wikidata: eventi e attori (origin "wikidata" o vuoto); quelle degli indicatori seguono la licenza della serie.
    add("wikidata", "entities", db.scalar(own(Entity).where((Entity.origin == "wikidata") | Entity.origin.is_(None))) or 0)
    add("wikidata", "relations", db.scalar(own(Relation).where(Relation.origin == "wikidata")) or 0)
    wp = db.scalar(select(func.count()).select_from(Source).where(Source.owner_id == lib, Source.notes.like("%Wikipedia%"))) or 0
    add("wikipedia", "events", wp)
    return counts


@router.get("/licenses", summary="Registro delle licenze delle fonti (NEXUS Copyright & Data Policy)")
def license_registry(db: DB) -> dict:
    counts = _library_counts(db)
    return {
        "version": licenses.POLICY_VERSION,
        "updated": licenses.POLICY_DATE,
        "library_licenses": list(licenses.LIBRARY_LICENSES),
        "licenses": [{**e, "library_counts": counts.get(e["id"], {})} for e in licenses.registry()],
    }
