from fastapi import APIRouter

from ... import __version__
from ...services import system
from ..deps import DB, AppSettings, CurrentUser
from ..schemas import HealthOut, SystemStatusOut, UserOut

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut, summary="Verifica che il backend risponda")
def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)


@router.get("/health/deep", summary="Verifica backend e database (usata dal controllo automatico giornaliero)")
def health_deep(db: DB) -> dict:
    from ...services.system import database_ok

    ok = database_ok(db)
    return {"status": "ok" if ok else "degraded", "database_ok": ok, "version": __version__}


@router.get("/system/status", response_model=SystemStatusOut, summary="Stato di database e modalità AI")
def system_status(db: DB, settings: AppSettings, user: CurrentUser) -> SystemStatusOut:
    return system.status(db, settings, user)


@router.get("/me", response_model=UserOut, summary="Utente corrente (Fase 1: utente locale)")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/library/summary", summary="Contenuto della Biblioteca NEXUS (dati aperti condivisi, sola lettura)")
def library_summary(db: DB, user: CurrentUser) -> dict:
    from sqlalchemy import func, select

    from ...core import library
    from ...models import Document, Entity, HistoricalEvent, Relation, Series, Source

    lib = library.library_user_id(db)
    if lib is None:
        return {"available": False}

    def count(model) -> int:
        return db.scalar(select(func.count()).select_from(model).where(model.owner_id == lib)) or 0

    return {"available": True, "events": count(HistoricalEvent), "series": count(Series), "entities": count(Entity),
            "relations": count(Relation), "sources": count(Source), "documents": count(Document)}
