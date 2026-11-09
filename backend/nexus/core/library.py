"""Biblioteca NEXUS: dati aperti importati (Wikidata, World Bank, ...) condivisi in sola lettura.

I dati della Biblioteca appartengono a un utente di sistema (``external_id = LIBRARY_EXTERNAL_ID``).
Ogni utente li vede accanto ai propri, ma non può modificarli né eliminarli: le funzioni di
scrittura dei servizi usano ``own=True`` e rifiutano gli elementi della Biblioteca.
"""

from __future__ import annotations

import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

LIBRARY_EXTERNAL_ID = "nexus-library"
LIBRARY_EMAIL = "library@nexus-library.invalid"
READ_ONLY = "Elemento della Biblioteca NEXUS (dati aperti condivisi): è in sola lettura."

_cache: dict[str, int | None] = {}
_lock = threading.Lock()


def library_user_id(db: Session) -> int | None:
    """Id dell'utente Biblioteca, oppure None se la Biblioteca non è stata creata."""
    from ..models import User

    key = str(db.get_bind().url)
    with _lock:
        if key in _cache and _cache[key] is not None:
            return _cache[key]
    uid = db.scalar(select(User.id).where(User.external_id == LIBRARY_EXTERNAL_ID))
    with _lock:
        _cache[key] = uid
    return uid


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def visible_owner_ids(db: Session, user) -> list[int]:
    """Proprietari i cui dati l'utente può leggere: sé stesso e la Biblioteca."""
    lib = library_user_id(db)
    return [user.id] if lib is None or lib == user.id else [user.id, lib]


def can_read(db: Session, user, owner_id: int) -> bool:
    return owner_id in visible_owner_ids(db, user)


def is_library(db: Session, owner_id: int) -> bool:
    lib = library_user_id(db)
    return lib is not None and owner_id == lib


def ensure_library_user(db: Session):
    from ..models import User

    u = db.scalar(select(User).where(User.external_id == LIBRARY_EXTERNAL_ID))
    if u is None:
        u = User(email=LIBRARY_EMAIL, display_name="Biblioteca NEXUS", external_id=LIBRARY_EXTERNAL_ID, role="user",
                 plan="free", is_local=False, is_active=False)
        db.add(u)
        db.commit()
        db.refresh(u)
        reset_cache()
    return u


def access(db: Session, user, obj, own: bool, not_found: str):
    """Lettura: dati propri e della Biblioteca. Scrittura (own=True): solo dati propri."""
    from .errors import NotFoundError, ReadOnlyError

    if obj is None or not can_read(db, user, obj.owner_id):
        raise NotFoundError(not_found)
    if own and obj.owner_id != user.id:
        raise ReadOnlyError(READ_ONLY)
    return obj
