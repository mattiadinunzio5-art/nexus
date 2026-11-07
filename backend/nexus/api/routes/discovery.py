from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Query, Request, status
from pydantic import BaseModel, Field, StringConstraints

from ...discovery.causal import TEMPLATES
from ...services import discovery as svc
from ..deps import DB, AppSettings, CurrentUser

router = APIRouter(prefix="/discovery", tags=["discovery"])


class SessionIn(BaseModel):
    mode: Literal["guided", "autonomous"] = "guided"
    query: Annotated[str, StringConstraints(max_length=2000)] = ""


class StatusIn(BaseModel):
    status: Literal["new", "accepted", "dismissed"]


class DecisionIn(BaseModel):
    status: Literal["to_verify", "confirmed", "rejected", "inconclusive"]
    note: Annotated[str, StringConstraints(max_length=5000)] = ""


class AnomalyIn(BaseModel):
    status: Literal["open", "explained", "dismissed"]
    note: Annotated[str, StringConstraints(max_length=5000)] = ""


class ChainIn(BaseModel):
    start: int
    end: int
    max_depth: int = Field(default=5, ge=1, le=6)


class TransmissionIn(BaseModel):
    series_ids: list[int] = Field(min_length=2, max_length=8)
    labels: list[Annotated[str, StringConstraints(max_length=100)]] = Field(default_factory=list, max_length=8)


class Variable(BaseModel):
    series_id: int
    favorable: Literal["up", "down"] = "up"


class ForesightIn(BaseModel):
    variables: list[Variable] = Field(min_length=1, max_length=6)
    horizon_years: float = Field(default=2, ge=0.25, le=10)
    triggers: list[Annotated[str, StringConstraints(max_length=300)]] = Field(default_factory=list, max_length=10)


@router.get("/overview", summary="Panoramica di Discovery Intelligence")
def overview(db: DB, user: CurrentUser) -> dict:
    return svc.overview(db, user)


@router.post("/sessions", status_code=status.HTTP_201_CREATED, summary="Avvia una sessione (guidata o autonoma), eseguita in background con limiti")
def create_session(data: SessionIn, request: Request, background: BackgroundTasks, db: DB, user: CurrentUser, settings: AppSettings) -> dict:
    s = svc.create_session(db, user, settings, data.mode, data.query)
    background.add_task(svc.run_in_background, request.app.state.database, settings, s.id)
    return svc.session_out(s)


@router.get("/sessions")
def list_sessions(db: DB, user: CurrentUser) -> list[dict]:
    return [svc.session_out(s) for s in svc.list_sessions(db, user)]


@router.get("/sessions/{sid}")
def get_session(sid: int, db: DB, user: CurrentUser) -> dict:
    return svc.session_out(svc.get_session(db, user, sid))


@router.post("/sessions/{sid}/{action}", summary="Pausa, ripresa o arresto di una sessione")
def control(sid: int, action: Literal["pause", "resume", "stop"], request: Request, background: BackgroundTasks, db: DB, user: CurrentUser, settings: AppSettings) -> dict:
    s = svc.control(db, user, sid, action)
    if action == "resume":
        background.add_task(svc.run_in_background, request.app.state.database, settings, s.id)
    return svc.session_out(s)


@router.get("/connections")
def list_connections(db: DB, user: CurrentUser, status_filter: str | None = Query(None, alias="status"), kind: str | None = None, session_id: int | None = None) -> list[dict]:
    return [svc.connection_out(c) for c in svc.list_connections(db, user, status_filter, kind, session_id)]


@router.get("/connections/{cid}")
def get_connection(cid: int, db: DB, user: CurrentUser) -> dict:
    from ...models import DiscoveryConnection

    return svc.connection_out(svc._own(db, user, DiscoveryConnection, cid, "Connessione"))


@router.post("/connections/{cid}/status", summary="Accetta (salva nel grafo come ipotesi) o scarta una connessione")
def connection_status(cid: int, data: StatusIn, db: DB, user: CurrentUser) -> dict:
    return svc.connection_out(svc.set_connection_status(db, user, cid, data.status))


@router.post("/connections/{cid}/hypothesis", status_code=status.HTTP_201_CREATED, summary="Genera l'ipotesi da una connessione")
def connection_hypothesis(cid: int, db: DB, user: CurrentUser) -> dict:
    return svc.hypothesis_out(svc.hypothesis_from_connection(db, user, cid))


@router.get("/hypotheses")
def list_hypotheses(db: DB, user: CurrentUser, status_filter: str | None = Query(None, alias="status"), archived: bool = False) -> list[dict]:
    return [svc.hypothesis_out(h) for h in svc.list_hypotheses(db, user, status_filter, archived)]


@router.get("/hypotheses/{hid}")
def get_hypothesis(hid: int, db: DB, user: CurrentUser) -> dict:
    from ...models import DiscoveryHypothesis

    return svc.hypothesis_out(svc._own(db, user, DiscoveryHypothesis, hid, "Ipotesi"))


@router.post("/hypotheses/{hid}/verify", summary="Verifica automatica: raccoglie elementi, non decide")
def verify(hid: int, db: DB, user: CurrentUser, settings: AppSettings) -> dict:
    return svc.hypothesis_out(svc.verify_hypothesis(db, user, settings, hid))


@router.post("/hypotheses/{hid}/decision", summary="Esito deciso dall'utente (con motivazione)")
def decide(hid: int, data: DecisionIn, db: DB, user: CurrentUser) -> dict:
    return svc.hypothesis_out(svc.decide_hypothesis(db, user, hid, data.status, data.note))


@router.post("/hypotheses/{hid}/archive")
def archive(hid: int, db: DB, user: CurrentUser, archived: bool = True) -> dict:
    return svc.hypothesis_out(svc.archive_hypothesis(db, user, hid, archived))


@router.post("/hypotheses/{hid}/graph", summary="Aggiungi l'ipotesi al Knowledge Graph")
def to_graph(hid: int, db: DB, user: CurrentUser) -> dict:
    return svc.hypothesis_out(svc.hypothesis_to_graph(db, user, hid))


@router.get("/anomalies")
def list_anomalies(db: DB, user: CurrentUser, status_filter: str | None = Query(None, alias="status")) -> list[dict]:
    return [svc.anomaly_out(a) for a in svc.list_anomalies(db, user, status_filter)]


@router.post("/anomalies/{aid}")
def update_anomaly(aid: int, data: AnomalyIn, db: DB, user: CurrentUser) -> dict:
    return svc.anomaly_out(svc.update_anomaly(db, user, aid, data.status, data.note))


@router.post("/causal/chains", status_code=status.HTTP_201_CREATED, summary="Catene causa-effetto tra due entità del grafo")
def chains(data: ChainIn, db: DB, user: CurrentUser) -> dict:
    return svc.analysis_out(svc.causal_chain(db, user, data.start, data.end, data.max_depth))


@router.get("/causal/templates", summary="Catene di trasmissione predefinite (codici reali delle serie)")
def templates() -> list[dict]:
    return TEMPLATES


@router.post("/causal/transmission", status_code=status.HTTP_201_CREATED, summary="Catena di trasmissione tra serie")
def transmission(data: TransmissionIn, db: DB, user: CurrentUser) -> dict:
    return svc.analysis_out(svc.transmission(db, user, data.series_ids, data.labels))


@router.post("/foresight", status_code=status.HTTP_201_CREATED, summary="Tre scenari dal bootstrap delle variazioni storiche")
def foresight(data: ForesightIn, db: DB, user: CurrentUser) -> dict:
    return svc.analysis_out(svc.run_foresight(db, user, [v.model_dump() for v in data.variables], data.horizon_years, data.triggers))


@router.get("/analyses")
def list_analyses(db: DB, user: CurrentUser, kind: str | None = None) -> list[dict]:
    return [svc.analysis_out(a) for a in svc.list_analyses(db, user, kind)]


@router.get("/analyses/{aid}")
def get_analysis(aid: int, db: DB, user: CurrentUser) -> dict:
    return svc.analysis_out(svc.get_analysis(db, user, aid))


@router.delete("/analyses/{aid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(aid: int, db: DB, user: CurrentUser) -> None:
    svc.delete_analysis(db, user, aid)
