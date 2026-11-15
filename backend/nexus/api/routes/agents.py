from fastapi import APIRouter, BackgroundTasks, Request, status

from ...services import ai, warroom
from ..deps import DB, AdminUser, AppSettings, CurrentUser
from ..schemas_agents import DecisionIn, PlatformAIIn, ProviderSelectIn, RunCreate, RunOut, RunSummary

router = APIRouter(tags=["agents"])


@router.put("/ai/provider", summary="Seleziona il provider AI (solo tra quelli con credenziali configurate)")
def select_provider(data: ProviderSelectIn, db: DB, user: CurrentUser, settings: AppSettings) -> dict:
    return ai.select_provider(db, user, settings, data.provider, data.effort)


@router.get("/ai/provider")
def get_provider(db: DB, user: CurrentUser, settings: AppSettings) -> dict:
    return ai.status(db, user, settings)


@router.delete("/ai/provider", status_code=status.HTTP_204_NO_CONTENT, summary="Torna all'AI condivisa (o predefinita) della piattaforma")
def reset_provider(db: DB, user: CurrentUser) -> None:
    from ...models import UserPreference

    pref = db.get(UserPreference, (user.id, ai.PREF_KEY))
    if pref:
        db.delete(pref)
        db.commit()


@router.get("/ai/platform", summary="AI condivisa con tutti gli utenti (solo amministratori)")
def get_platform(db: DB, admin: AdminUser) -> dict:
    plat = ai.platform(db)
    pref = plat[1] if plat else None
    if pref is None:
        from ...models import UserPreference

        p = db.get(UserPreference, (admin.id, ai.PLATFORM_KEY))
        pref = dict(p.value) if p else {"enabled": False, "provider": "anthropic", "daily_limit": ai.DEFAULT_DAILY_LIMIT}
    return pref


@router.put("/ai/platform", summary="Condividi il tuo provider AI con tutti gli utenti, con un limite giornaliero ciascuno")
def put_platform(data: PlatformAIIn, db: DB, admin: AdminUser, settings: AppSettings) -> dict:
    return ai.set_platform(db, admin, settings, data.enabled, data.provider, data.daily_limit)


@router.post("/research/runs", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED,
             summary="Avvia una ricerca multi-agente (eseguita in background, poi in attesa di approvazione)")
def create_run(data: RunCreate, request: Request, background: BackgroundTasks, db: DB, user: CurrentUser, settings: AppSettings):
    run = warroom.create_run(db, user, settings, data)
    background.add_task(warroom.execute_in_background, request.app.state.database, settings, run.id)
    return run


@router.get("/research/runs", response_model=list[RunSummary])
def list_runs(db: DB, user: CurrentUser):
    return warroom.list_runs(db, user)


@router.get("/research/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: DB, user: CurrentUser):
    return warroom.get_run(db, user, run_id)


@router.post("/research/runs/{run_id}/decision", response_model=RunOut, summary="Approvazione o rifiuto da parte dell'utente")
def decide(run_id: int, data: DecisionIn, db: DB, user: CurrentUser):
    return warroom.decide(db, user, run_id, data)
