"""Componente G — integrazione con il Knowledge Graph esistente (services/graph.py).

Aggiunge risoluzione delle entità (niente duplicati), nodi per le serie e per le ipotesi.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Entity, Series, User


def norm(name: str) -> str:
    """Nome normalizzato per il confronto: minuscolo, senza accenti, punteggiatura e articoli iniziali."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"^(the|il|lo|la|i|gli|le|l) ", "", s)


def find_entity(db: Session, user: User, name: str, entity_type: str | None = None, exclude_id: int | None = None) -> Entity | None:
    """Entità esistente con lo stesso nome o alias (normalizzati), dello stesso tipo se indicato."""
    key = norm(name)
    if not key:
        return None
    stmt = select(Entity).where(Entity.owner_id == user.id)
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    for e in db.scalars(stmt):
        if e.id == exclude_id:
            continue
        if norm(e.name) == key or any(norm(a) == key for a in (e.aliases or [])):
            return e
    return None


def ensure_series_entity(db: Session, user: User, s: Series) -> Entity:
    """Nodo «indicatore» collegato a una serie importata (creato una sola volta)."""
    e = db.scalar(select(Entity).where(Entity.owner_id == user.id, Entity.series_id == s.id))
    if e:
        return e
    e = find_entity(db, user, s.name, "indicator")
    if e and e.series_id is None:
        e.series_id = s.id
        db.flush()
        return e
    e = Entity(owner_id=user.id, entity_type="indicator", name=s.name[:300], series_id=s.id,
               description=f"Serie: {s.source_label}. Unità: {s.unit or 'n.d.'}.", aliases=[])
    db.add(e)
    db.flush()
    return e


def event_entity(db: Session, event_id: int) -> Entity | None:
    return db.scalar(select(Entity).where(Entity.event_id == event_id))
