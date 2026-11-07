"""Servizio Discovery Intelligence: sessioni, risultati e azioni dell'utente."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents import llm
from ..api.schemas_history import RelationIn
from ..core.config import Settings
from ..core.errors import NexusError, NotFoundError, ValidationFailedError
from ..database.base import utcnow
from ..database.session import Database
from ..discovery import causal, core, foresight, hypotheses as hy, kg
from ..models import (DiscoveryAnalysis, DiscoveryAnomaly, DiscoveryConnection, DiscoveryHypothesis, DiscoverySession, Entity,
                      HistoricalEvent, Series, User)
from . import activity, ai, graph, notifications, quotas


class InvalidStateError(NexusError):
    status_code = 409
    code = "invalid_state"


def _own(db: Session, user: User, model, oid: int, label: str):
    x = db.get(model, oid)
    if x is None or x.owner_id != user.id:
        raise NotFoundError(f"{label} non trovata.")
    return x


# --- Sessioni ------------------------------------------------------------------------------------


def create_session(db: Session, user: User, settings: Settings, mode: str, query: str) -> DiscoverySession:
    if mode == "guided" and not query.strip():
        raise ValidationFailedError("Scrivi la domanda da analizzare.")
    if db.scalar(select(DiscoverySession).where(DiscoverySession.owner_id == user.id, DiscoverySession.status.in_(("queued", "running")))):
        raise InvalidStateError("C'è già una sessione di discovery in corso: attendi, mettila in pausa o fermala.")
    try:
        client = ai.client_for(db, user, settings)
    except llm.ProviderError:
        client = None
    if client:
        quotas.check(db, user, "ai_runs")
    s = DiscoverySession(owner_id=user.id, mode=mode, query=query.strip()[:2000],
                         limits={"max_seconds": settings.discovery_max_seconds, "max_llm_calls": settings.discovery_max_llm_calls if client else 0,
                                 "max_items": settings.discovery_max_items, "provider": client.provider if client else "none"})
    db.add(s)
    db.flush()
    activity.record(db, user=user, actor="user", action="discovery.start", entity_type="discovery_session", entity_id=s.id,
                    summary=f"Avviata discovery {'guidata' if mode == 'guided' else 'autonoma'}" + (f": «{query[:80]}»" if query else ""))
    db.commit()
    db.refresh(s)
    return s


def run_in_background(database: Database, settings: Settings, session_id: int) -> None:
    with database.session_factory() as db:
        s = db.get(DiscoverySession, session_id)
        if s is None or s.status not in ("queued",):
            return
        user = db.get(User, s.owner_id)
        try:
            client = ai.client_for(db, user, settings) if s.limits.get("max_llm_calls") else None
        except llm.ProviderError:
            client = None
        core.execute(db, s, user, settings, client)
        if s.status in ("completed", "stopped", "failed"):
            c = s.result.get("counts", {})
            title = f"Discovery #{s.id} " + {"completed": "completata", "stopped": "fermata", "failed": "non riuscita"}[s.status]
            body = s.error or f"{c.get('connections', 0)} connessioni, {c.get('hypotheses', 0)} ipotesi, {c.get('anomalies', 0)} anomalie."
            notifications.create(db, user, title, body, level="error" if s.status == "failed" else "info")
            activity.record(db, user=None, actor="system", action="discovery.finish", entity_type="discovery_session", entity_id=s.id, summary=f"{title}: {body}"[:500])
            db.commit()


def list_sessions(db: Session, user: User, limit: int = 30) -> list[DiscoverySession]:
    return list(db.scalars(select(DiscoverySession).where(DiscoverySession.owner_id == user.id).order_by(DiscoverySession.id.desc()).limit(limit)))


def get_session(db: Session, user: User, sid: int) -> DiscoverySession:
    return _own(db, user, DiscoverySession, sid, "Sessione")


def control(db: Session, user: User, sid: int, action: str) -> DiscoverySession:
    s = get_session(db, user, sid)
    allowed = {"pause": ("queued", "running"), "resume": ("paused",), "stop": ("queued", "running", "paused")}
    if s.status not in allowed[action]:
        raise InvalidStateError(f"Impossibile eseguire «{action}» su una sessione nello stato «{s.status}».")
    if action == "resume" and db.scalar(select(DiscoverySession).where(DiscoverySession.owner_id == user.id, DiscoverySession.id != s.id,
                                                                        DiscoverySession.status.in_(("queued", "running")))):
        raise InvalidStateError("C'è già un'altra sessione in corso.")
    s.status = {"pause": "paused", "resume": "queued", "stop": "stopped"}[action]
    if action == "stop":
        s.finished_at = utcnow()
    activity.record(db, user=user, actor="user", action=f"discovery.{action}", entity_type="discovery_session", entity_id=s.id,
                    summary=f"Discovery #{s.id}: {action}")
    db.commit()
    db.refresh(s)
    return s


# --- Panoramica -----------------------------------------------------------------------------------


def overview(db: Session, user: User) -> dict:
    def count(model, *cond):
        return db.scalar(select(func.count()).select_from(model).where(model.owner_id == user.id, *cond)) or 0

    return {
        "connections": count(DiscoveryConnection), "connections_new": count(DiscoveryConnection, DiscoveryConnection.status == "new"),
        "hypotheses": count(DiscoveryHypothesis, DiscoveryHypothesis.archived.is_(False)),
        "hypotheses_by_status": {st: count(DiscoveryHypothesis, DiscoveryHypothesis.status == st, DiscoveryHypothesis.archived.is_(False))
                                 for st in ("to_verify", "verifying", "confirmed", "rejected", "inconclusive")},
        "anomalies_open": count(DiscoveryAnomaly, DiscoveryAnomaly.status == "open"),
        "running": [{"id": s.id, "mode": s.mode, "query": s.query, "status": s.status, "cursor": s.cursor, "steps_total": len(core.STEPS[s.mode])}
                    for s in db.scalars(select(DiscoverySession).where(DiscoverySession.owner_id == user.id, DiscoverySession.status.in_(("queued", "running", "paused"))))],
        "latest_connections": [connection_out(c) for c in db.scalars(select(DiscoveryConnection).where(DiscoveryConnection.owner_id == user.id)
                                                                      .order_by(DiscoveryConnection.id.desc()).limit(5))],
        "latest_hypotheses": [hypothesis_out(h) for h in db.scalars(select(DiscoveryHypothesis).where(DiscoveryHypothesis.owner_id == user.id, DiscoveryHypothesis.archived.is_(False))
                                                                      .order_by(DiscoveryHypothesis.id.desc()).limit(5))],
        "latest_anomalies": [anomaly_out(a) for a in db.scalars(select(DiscoveryAnomaly).where(DiscoveryAnomaly.owner_id == user.id, DiscoveryAnomaly.status == "open")
                                                                  .order_by(DiscoveryAnomaly.relevance.desc()).limit(5))],
        "archive": {"events": count(HistoricalEvent), "series": count(Series), "entities": count(Entity)},
    }


# --- Serializzazione -------------------------------------------------------------------------------


def _cols(x, names: list[str]) -> dict:
    return {n: getattr(x, n) for n in names}


def connection_out(c: DiscoveryConnection) -> dict:
    from ..discovery.connections import KIND_LABEL

    return {**_cols(c, ["id", "session_id", "kind", "title", "elements", "period", "evidence", "sources", "reliability", "reliability_reasons",
                        "explanation", "caveats", "score", "status", "graph_relation_id", "created_at"]), "kind_label": KIND_LABEL.get(c.kind, c.kind)}


def hypothesis_out(h: DiscoveryHypothesis) -> dict:
    return _cols(h, ["id", "session_id", "connection_id", "title", "description", "phenomena", "motivation", "supporting", "contrary", "missing",
                     "method", "confidence", "status", "archived", "verification", "decision_note", "decided_at", "origin", "graph_entity_id", "created_at"])


def anomaly_out(a: DiscoveryAnomaly) -> dict:
    return _cols(a, ["id", "session_id", "kind", "title", "what_changed", "reference", "period", "data", "alternatives", "refs", "relevance",
                     "verifiability", "status", "note", "created_at"])


def analysis_out(a: DiscoveryAnalysis) -> dict:
    return _cols(a, ["id", "session_id", "kind", "title", "params", "result", "created_at"])


def session_out(s: DiscoverySession) -> dict:
    return {**_cols(s, ["id", "mode", "query", "status", "cursor", "scope", "steps", "result", "limits", "llm_calls", "elapsed_ms", "error",
                        "started_at", "finished_at", "created_at"]), "steps_total": len(core.STEPS[s.mode]),
            "plan": [core.STEP_LABEL[x] for x in core.STEPS[s.mode]]}


# --- Connessioni -----------------------------------------------------------------------------------


def list_connections(db: Session, user: User, status: str | None = None, kind: str | None = None, session_id: int | None = None) -> list[DiscoveryConnection]:
    stmt = select(DiscoveryConnection).where(DiscoveryConnection.owner_id == user.id)
    if status:
        stmt = stmt.where(DiscoveryConnection.status == status)
    if kind:
        stmt = stmt.where(DiscoveryConnection.kind == kind)
    if session_id:
        stmt = stmt.where(DiscoveryConnection.session_id == session_id)
    return list(db.scalars(stmt.order_by(DiscoveryConnection.score.desc(), DiscoveryConnection.id.desc()).limit(300)))


def _entity_for(db: Session, user: User, el: dict) -> Entity:
    if el["type"] == "event":
        e = kg.event_entity(db, el["id"])
    elif el["type"] == "series":
        s = db.get(Series, el["id"])
        e = kg.ensure_series_entity(db, user, s) if s and s.owner_id == user.id else None
    else:
        e = db.get(Entity, el["id"])
    if e is None or e.owner_id != user.id:
        raise ValidationFailedError(f"L'elemento «{el['label']}» non esiste più.")
    return e


RELATION_FOR_KIND = {"shared_actors": "related_to", "textual_reference": "influenced", "graph_proximity": "related_to",
                     "event_data_change": "related_to", "statistical_association": "related_to"}


def set_connection_status(db: Session, user: User, cid: int, status: str) -> DiscoveryConnection:
    c = _own(db, user, DiscoveryConnection, cid, "Connessione")
    if status == "accepted" and c.graph_relation_id is None:
        a, b = (_entity_for(db, user, el) for el in c.elements[:2])
        rel = RelationIn(source_entity_id=a.id, target_entity_id=b.id, relation_type=RELATION_FOR_KIND[c.kind], provenance="user_hypothesis",
                         evidence_note=f"Discovery Intelligence, connessione #{c.id} ({c.kind}), accettata dall'utente come ipotesi: {c.explanation}"[:2000],
                         confidence="low" if c.reliability == "low" else "medium")
        try:
            r = graph.create_relation(db, user, rel, provenance_override="ai_hypothesis")
            c.graph_relation_id = r.id
        except ValidationFailedError:
            pass  # relazione già presente nel grafo
    c.status = status
    activity.record(db, user=user, actor="user", action=f"discovery.connection_{status}", entity_type="discovery_connection", entity_id=c.id,
                    summary=f"Connessione «{c.title[:80]}»: {status}" + (" (salvata nel grafo come ipotesi)" if c.graph_relation_id else ""))
    db.commit()
    db.refresh(c)
    return c


# --- Ipotesi ---------------------------------------------------------------------------------------


def list_hypotheses(db: Session, user: User, status: str | None = None, archived: bool = False) -> list[DiscoveryHypothesis]:
    stmt = select(DiscoveryHypothesis).where(DiscoveryHypothesis.owner_id == user.id, DiscoveryHypothesis.archived.is_(archived))
    if status:
        stmt = stmt.where(DiscoveryHypothesis.status == status)
    return list(db.scalars(stmt.order_by(DiscoveryHypothesis.id.desc()).limit(300)))


def hypothesis_from_connection(db: Session, user: User, cid: int) -> DiscoveryHypothesis:
    c = _own(db, user, DiscoveryConnection, cid, "Connessione")
    ex = db.scalar(select(DiscoveryHypothesis).where(DiscoveryHypothesis.owner_id == user.id, DiscoveryHypothesis.fingerprint == c.fingerprint))
    if ex:
        return ex
    h = DiscoveryHypothesis(owner_id=user.id, connection_id=c.id, fingerprint=c.fingerprint, origin="rules", **hy.from_connection(db, c))
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def verify_hypothesis(db: Session, user: User, settings: Settings, hid: int) -> DiscoveryHypothesis:
    h = _own(db, user, DiscoveryHypothesis, hid, "Ipotesi")
    if h.status in ("confirmed", "rejected", "inconclusive"):
        raise InvalidStateError("L'ipotesi ha già un esito: riportala «da verificare» per ripetere la verifica.")
    c = db.get(DiscoveryConnection, h.connection_id) if h.connection_id else None
    checks = hy.verify(db, user, settings, c)
    h.verification = [*h.verification, {"at": utcnow().isoformat(), "checks": checks, "suggested": hy.suggested_outcome(checks)}][-10:]
    h.status = "verifying"
    activity.record(db, user=user, actor="system", action="discovery.hypothesis_verify", entity_type="discovery_hypothesis", entity_id=h.id,
                    summary=f"Verifica dell'ipotesi «{h.title[:80]}»: {len(checks)} controlli")
    db.commit()
    db.refresh(h)
    return h


def decide_hypothesis(db: Session, user: User, hid: int, status: str, note: str) -> DiscoveryHypothesis:
    h = _own(db, user, DiscoveryHypothesis, hid, "Ipotesi")
    if status in ("confirmed", "rejected", "inconclusive"):
        if not note.strip():
            raise ValidationFailedError("Motiva la decisione: indica su quali evidenze ti basi.")
        if not h.verification and status == "confirmed":
            raise ValidationFailedError("Esegui almeno una verifica prima di confermare un'ipotesi.")
        h.decided_at = utcnow()
    else:
        h.decided_at = None
    h.status, h.decision_note = status, note.strip()[:5000]
    activity.record(db, user=user, actor="user", action="discovery.hypothesis_decide", entity_type="discovery_hypothesis", entity_id=h.id,
                    summary=f"Ipotesi «{h.title[:80]}»: {status}")
    db.commit()
    db.refresh(h)
    return h


def archive_hypothesis(db: Session, user: User, hid: int, archived: bool) -> DiscoveryHypothesis:
    h = _own(db, user, DiscoveryHypothesis, hid, "Ipotesi")
    h.archived = archived
    db.commit()
    db.refresh(h)
    return h


def hypothesis_to_graph(db: Session, user: User, hid: int) -> DiscoveryHypothesis:
    """Nodo «ipotesi» nel Knowledge Graph, collegato agli elementi coinvolti (relazioni marcate come ipotesi)."""
    h = _own(db, user, DiscoveryHypothesis, hid, "Ipotesi")
    if h.graph_entity_id and db.get(Entity, h.graph_entity_id):
        return h
    c = db.get(DiscoveryConnection, h.connection_id) if h.connection_id else None
    node = kg.find_entity(db, user, h.title, "hypothesis") or Entity(owner_id=user.id, entity_type="hypothesis", name=h.title[:300],
                                                                      description=f"Stato: {h.status}. {h.description[:1500]}", aliases=[])
    db.add(node)
    db.flush()
    for el in (c.elements if c else []):
        try:
            target = _entity_for(db, user, el)
            graph.create_relation(db, user, RelationIn(source_entity_id=node.id, target_entity_id=target.id, relation_type="related_to",
                                                       provenance="user_hypothesis", evidence_note=f"Ipotesi #{h.id} di Discovery Intelligence"),
                                  provenance_override="ai_hypothesis")
        except NexusError:
            continue
    h.graph_entity_id = node.id
    db.commit()
    db.refresh(h)
    return h


# --- Anomalie --------------------------------------------------------------------------------------


def list_anomalies(db: Session, user: User, status: str | None = None) -> list[DiscoveryAnomaly]:
    stmt = select(DiscoveryAnomaly).where(DiscoveryAnomaly.owner_id == user.id)
    if status:
        stmt = stmt.where(DiscoveryAnomaly.status == status)
    order = {"high": 0, "medium": 1, "low": 2}
    rows = list(db.scalars(stmt.limit(500)))
    return sorted(rows, key=lambda a: (-a.relevance, order.get(a.verifiability, 3)))


def update_anomaly(db: Session, user: User, aid: int, status: str, note: str) -> DiscoveryAnomaly:
    a = _own(db, user, DiscoveryAnomaly, aid, "Anomalia")
    if status in ("explained", "dismissed") and not note.strip():
        raise ValidationFailedError("Indica la spiegazione o il motivo.")
    a.status, a.note = status, note.strip()[:5000]
    db.commit()
    db.refresh(a)
    return a


# --- Analisi: catene causali, trasmissione, scenari -------------------------------------------------


def _save_analysis(db: Session, user: User, kind: str, title: str, params: dict, result: dict) -> DiscoveryAnalysis:
    a = DiscoveryAnalysis(owner_id=user.id, kind=kind, title=title[:500], params=params, result=result)
    db.add(a)
    activity.record(db, user=user, actor="user", action=f"discovery.{kind}", entity_type="discovery_analysis", entity_id=None, summary=title[:300])
    db.commit()
    db.refresh(a)
    return a


def causal_chain(db: Session, user: User, start: int, end: int, max_depth: int) -> DiscoveryAnalysis:
    res = causal.chains(db, user, start, end, max_depth=max_depth)
    return _save_analysis(db, user, "causal_chain", f"{res['start']} → {res['end']}", {"start": start, "end": end, "max_depth": max_depth}, res)


def transmission(db: Session, user: User, series_ids: list[int], labels: list[str]) -> DiscoveryAnalysis:
    for sid in series_ids:
        s = db.get(Series, sid)
        if s and s.owner_id == user.id:
            kg.ensure_series_entity(db, user, s)
    res = causal.transmission(db, user, series_ids, labels or None)
    title = " → ".join(x["from"] for x in res["steps"]) + " → " + res["steps"][-1]["to"]
    return _save_analysis(db, user, "transmission", title, {"series_ids": series_ids, "labels": labels}, res)


def run_foresight(db: Session, user: User, variables: list[dict], horizon_years: float, triggers: list[str]) -> DiscoveryAnalysis:
    res = foresight.scenarios(db, user, variables, horizon_years, triggers)
    title = "Scenari: " + ", ".join(v["name"][:40] for v in res["variables"]) + f" — {horizon_years:g} anni"
    return _save_analysis(db, user, "foresight", title, {"variables": variables, "horizon_years": horizon_years, "triggers": triggers}, res)


def list_analyses(db: Session, user: User, kind: str | None = None) -> list[DiscoveryAnalysis]:
    stmt = select(DiscoveryAnalysis).where(DiscoveryAnalysis.owner_id == user.id)
    if kind:
        stmt = stmt.where(DiscoveryAnalysis.kind == kind)
    return list(db.scalars(stmt.order_by(DiscoveryAnalysis.id.desc()).limit(100)))


def get_analysis(db: Session, user: User, aid: int) -> DiscoveryAnalysis:
    return _own(db, user, DiscoveryAnalysis, aid, "Analisi")


def delete_analysis(db: Session, user: User, aid: int) -> None:
    db.delete(_own(db, user, DiscoveryAnalysis, aid, "Analisi"))
    db.commit()
