from fastapi import APIRouter

from ... import __version__
from ...services import system
from ..deps import DB, AppSettings, CurrentUser
from ..schemas import HealthOut, SystemStatusOut, UserOut

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut, summary="Verifica che il backend risponda")
def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)


@router.get("/health/deep", summary="Verifica backend, database, ricerca nei documenti, coda delle ricerche e memoria")
def health_deep(db: DB) -> dict:
    import time

    from sqlalchemy import func, select

    from ...models import ResearchRun
    from ...research import index
    from ...services.research import _rss_mb
    from ...services.system import database_ok

    ok = database_ok(db)
    search_ok, search_ms = False, None
    if ok:
        t0 = time.perf_counter()
        try:
            index.text_search(db, 0, "nexus health", 1)  # nessun utente 0: verifica solo che la ricerca risponda
            search_ok = True
        except Exception:  # noqa: BLE001
            search_ok = False
        search_ms = int((time.perf_counter() - t0) * 1000)
    queued = db.scalar(select(func.count()).select_from(ResearchRun).where(ResearchRun.status.in_(("queued", "running")))) if ok else None
    rss = _rss_mb()
    status = "ok" if ok and search_ok else "degraded"
    return {"status": status, "database_ok": ok, "search_ok": search_ok, "search_ms": search_ms, "research_queue": queued,
            "memory_mb": round(rss) if rss else None, "version": __version__}


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
