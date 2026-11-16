"""Discovery: archivio personale e Biblioteca NEXUS condivisa.

Due utenti (Anna e Bruno) e la Biblioteca. Si verifica che:
* la Biblioteca si consulti anche nelle analisi (catene causali, trasmissione, scenari) senza essere modificata;
* `origin=mine` restituisca solo i dati dell'utente e `origin=library` solo quelli della Biblioteca;
* nessuna azione di scrittura riesca sui risultati della Biblioteca, per nessun utente;
* nessun utente veda o usi i dati di un altro (neppure passando gli ID nelle richieste).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from nexus.api.schemas_history import RelationIn
from nexus.core import library
from nexus.core.config import Settings
from nexus.main import create_app
from nexus.models import (DiscoveryAnalysis, DiscoveryAnomaly, DiscoveryConnection, DiscoveryHypothesis, DiscoverySession, Entity,
                          Observation, Relation, Series, Source)
from nexus.services import auth as auth_svc
from nexus.services import graph

H = {"X-Nexus-Client": "web"}
PWD = "Archivio-Storico-2026"


def _signup(app, email):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"email": email, "password": PWD, "display_name": email.split("@")[0]})
    assert r.status_code == 201, r.text
    c.headers.update(H)
    return c, r.json()


def _series(db, owner_id, name, values):
    s = Series(owner_id=owner_id, name=name, connector="world-bank", source_label="World Bank", unit="%", frequency="A")
    s.observations = [Observation(date=f"{1970 + i}-01-01", value=float(v)) for i, v in enumerate(values)]
    s.observation_count = len(values)
    db.add(s)
    db.flush()
    return s


def _library_counts(db, lib_id) -> dict:
    models = (Entity, Relation, Series, DiscoverySession, DiscoveryConnection, DiscoveryHypothesis, DiscoveryAnomaly, DiscoveryAnalysis)
    return {m.__name__: db.scalar(select(func.count()).select_from(m).where(m.owner_id == lib_id)) for m in models}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("disc-lib")
    s = Settings(env="test", database_url=f"sqlite:///{tmp / 'd.db'}", data_dir=tmp / "data", auth_mode="multi", secret_key="disc-lib-key")
    auth_svc.limiter._fails.clear()
    library.reset_cache()
    app = create_app(s)
    with TestClient(app):
        _signup(app, "root@example.org")
        a, ua = _signup(app, "anna@example.org")
        b, ub = _signup(app, "bruno@example.org")
        with app.state.database.session_factory() as db:
            lib = library.ensure_library_user(db)
            src = Source(owner_id=lib.id, title="Storia economica", source_type="book")
            db.add(src)
            db.flush()
            ents = {n: Entity(owner_id=lib.id, entity_type="concept", name=n, aliases=[]) for n in ("Shock petrolifero", "Inflazione", "Recessione")}
            db.add_all(ents.values())
            db.commit()
            graph.create_relation(db, lib, RelationIn(source_entity_id=ents["Shock petrolifero"].id, target_entity_id=ents["Inflazione"].id,
                                                      relation_type="caused", provenance="sourced", source_id=src.id))
            graph.create_relation(db, lib, RelationIn(source_entity_id=ents["Inflazione"].id, target_entity_id=ents["Recessione"].id,
                                                      relation_type="caused", provenance="sourced", source_id=src.id))
            s1 = _series(db, lib.id, "Prezzo del petrolio", [10 + (i % 7) * 1.5 + i * 0.3 for i in range(40)])
            s2 = _series(db, lib.id, "Inflazione annua", [3 + ((i + 1) % 7) * 0.8 + i * 0.1 for i in range(40)])
            # Risultati della Discovery eseguita sulla Biblioteca.
            sess = DiscoverySession(owner_id=lib.id, mode="autonomous", query="", status="paused", limits={}, steps=[], result={})
            db.add(sess)
            db.flush()
            conn = DiscoveryConnection(owner_id=lib.id, session_id=sess.id, fingerprint="lib-f1", kind="graph_proximity", title="Petrolio e inflazione",
                                       elements=[{"type": "entity", "id": ents["Shock petrolifero"].id, "label": "Shock petrolifero"},
                                                 {"type": "entity", "id": ents["Inflazione"].id, "label": "Inflazione"}],
                                       period="1973", evidence=[], sources=[src.id], reliability="medium", reliability_reasons=[],
                                       explanation="x", caveats=[], score=3.0)
            anom = DiscoveryAnomaly(owner_id=lib.id, session_id=sess.id, fingerprint="lib-a1", kind="series_change", title="Salto del petrolio",
                                    what_changed="x", reference="x", period="1973", data={}, alternatives=[], refs={}, relevance=5.0, verifiability="high")
            db.add_all([conn, anom])
            db.flush()
            hyp = DiscoveryHypothesis(owner_id=lib.id, session_id=sess.id, connection_id=conn.id, fingerprint="lib-f1", origin="rules",
                                      title="Il petrolio spinge l'inflazione", description="x", phenomena=[], motivation="x", supporting=[],
                                      contrary=[], missing=[], method="x", confidence="low")
            ana = DiscoveryAnalysis(owner_id=lib.id, session_id=sess.id, kind="causal_chain", title="Catena della Biblioteca", params={}, result={})
            db.add_all([hyp, ana])
            db.commit()
            ids = {"lib": lib.id, "src": src.id, **{n: e.id for n, e in ents.items()}, "s1": s1.id, "s2": s2.id,
                   "sess": sess.id, "conn": conn.id, "anom": anom.id, "hyp": hyp.id, "ana": ana.id}
        yield {"app": app, "a": a, "b": b, "ua": ua, "ub": ub, "ids": ids}
    library.reset_cache()


def _db(world):
    return world["app"].state.database.session_factory()


def test_library_is_consultable_in_analyses_without_being_modified(world):
    a, b, ids = world["a"], world["b"], world["ids"]
    with _db(world) as db:
        before = _library_counts(db, ids["lib"])
    # Catena causale interamente sulla Biblioteca.
    r = a.post("/api/discovery/causal/chains", json={"start": ids["Shock petrolifero"], "end": ids["Recessione"]})
    assert r.status_code == 201, r.text
    res = r.json()["result"]
    assert res["paths"] and res["paths"][0]["nodes"] == ["Shock petrolifero", "Inflazione", "Recessione"]
    assert res["paths"][0]["strength"] == "causal_documented" and "Storia economica" in res["paths"][0]["links"][0]["evidence"]
    # Una relazione propria di Anna verso la Biblioteca allunga la catena solo per lei.
    mine = a.post("/api/graph/entities", json={"entity_type": "institution", "name": "Guerra del Kippur"}).json()["id"]
    assert a.post("/api/graph/relations", json={"source_entity_id": mine, "target_entity_id": ids["Shock petrolifero"],
                                                "relation_type": "caused", "provenance": "user_hypothesis"}).status_code == 201
    r = a.post("/api/discovery/causal/chains", json={"start": mine, "end": ids["Recessione"]})
    assert r.status_code == 201 and r.json()["result"]["paths"][0]["strength"] == "causal_hypothesized"
    assert b.post("/api/discovery/causal/chains", json={"start": mine, "end": ids["Recessione"]}).status_code == 404
    rb = b.post("/api/discovery/causal/chains", json={"start": ids["Shock petrolifero"], "end": ids["Recessione"]}).json()["result"]
    assert "Guerra del Kippur" not in str(rb)
    # Trasmissione e scenari con serie della Biblioteca.
    r = a.post("/api/discovery/causal/transmission", json={"series_ids": [ids["s1"], ids["s2"]]})
    assert r.status_code == 201, r.text
    assert len(r.json()["result"]["steps"]) == 1
    r = a.post("/api/discovery/foresight", json={"variables": [{"series_id": ids["s1"]}], "horizon_years": 2})
    assert r.status_code == 201, r.text
    assert r.json()["result"]["variables"][0]["name"] == "Prezzo del petrolio"
    # Le analisi sono di Anna: Bruno non le vede; la Biblioteca non è cambiata.
    titles_a = [x["title"] for x in a.get("/api/discovery/analyses").json()]
    assert len(titles_a) == 4 and "Catena della Biblioteca" not in titles_a
    assert all(x["title"] != "Guerra del Kippur → Recessione" for x in b.get("/api/discovery/analyses").json())
    with _db(world) as db:
        assert _library_counts(db, ids["lib"]) == before


def test_library_discovery_results_are_read_only_for_everyone(world):
    ids = world["ids"]
    with _db(world) as db:
        before = _library_counts(db, ids["lib"])
        h0 = db.get(DiscoveryHypothesis, ids["hyp"])
        snap = (h0.title, h0.status, h0.archived, h0.verification, h0.graph_entity_id)
    attempts = [
        ("POST", f"/api/discovery/connections/{ids['conn']}/status", {"status": "accepted"}),
        ("POST", f"/api/discovery/connections/{ids['conn']}/hypothesis", None),
        ("POST", f"/api/discovery/hypotheses/{ids['hyp']}/verify", None),
        ("POST", f"/api/discovery/hypotheses/{ids['hyp']}/decision", {"status": "rejected", "note": "motivo"}),
        ("PATCH", f"/api/discovery/hypotheses/{ids['hyp']}", {"title": "Ipotesi riscritta"}),
        ("POST", f"/api/discovery/hypotheses/{ids['hyp']}/archive", None),
        ("POST", f"/api/discovery/hypotheses/{ids['hyp']}/graph", None),
        ("POST", f"/api/discovery/anomalies/{ids['anom']}", {"status": "dismissed", "note": "motivo"}),
        ("POST", f"/api/discovery/sessions/{ids['sess']}/resume", None),
        ("POST", f"/api/discovery/sessions/{ids['sess']}/stop", None),
    ]
    for who in ("a", "b"):
        c = world[who]
        for method, url, body in attempts:
            r = c.request(method, url, json=body)
            assert r.status_code == 403 and r.json()["error"]["code"] == "read_only", (who, method, url, r.status_code, r.text[:200])
        r = c.delete(f"/api/discovery/analyses/{ids['ana']}")
        assert r.status_code in (403, 404), r.text
    with _db(world) as db:
        assert _library_counts(db, ids["lib"]) == before
        h1 = db.get(DiscoveryHypothesis, ids["hyp"])
        assert (h1.title, h1.status, h1.archived, h1.verification, h1.graph_entity_id) == snap
        assert db.get(DiscoverySession, ids["sess"]).status == "paused"
        assert db.get(DiscoveryConnection, ids["conn"]).status == "new"
        assert db.get(DiscoveryAnomaly, ids["anom"]).status == "open"


def test_origin_filters_never_mix_users_or_library(world):
    a, b, ids = world["a"], world["b"], world["ids"]
    with _db(world) as db:
        anna = world["ua"]["id"]
        s = DiscoverySession(owner_id=anna, mode="guided", query="SEGRETO-ANNA", status="completed", limits={}, steps=[], result={})
        db.add(s)
        db.flush()
        c = DiscoveryConnection(owner_id=anna, session_id=s.id, fingerprint="anna-f1", kind="shared_actors", title="Connessione SEGRETO-ANNA",
                                elements=[], period="", evidence=[], sources=[], reliability="low", reliability_reasons=[], explanation="",
                                caveats=[], score=1.0)
        an = DiscoveryAnomaly(owner_id=anna, session_id=s.id, fingerprint="anna-a1", kind="series_change", title="Anomalia SEGRETO-ANNA",
                              what_changed="", reference="", period="", data={}, alternatives=[], refs={}, relevance=1.0, verifiability="low")
        db.add_all([c, an])
        db.flush()
        h = DiscoveryHypothesis(owner_id=anna, session_id=s.id, connection_id=c.id, fingerprint="anna-f1", origin="rules", title="Ipotesi SEGRETO-ANNA",
                                description="", phenomena=[], motivation="", supporting=[], contrary=[], missing=[], method="", confidence="low")
        db.add(h)
        db.commit()
        mine_ids = {"sessions": s.id, "connections": c.id, "hypotheses": h.id, "anomalies": an.id}
    lib_ids = {"sessions": ids["sess"], "connections": ids["conn"], "hypotheses": ids["hyp"], "anomalies": ids["anom"]}
    for kind in ("sessions", "connections", "hypotheses", "anomalies"):
        a_mine = a.get(f"/api/discovery/{kind}?origin=mine").json()
        a_lib = a.get(f"/api/discovery/{kind}?origin=library").json()
        b_mine = b.get(f"/api/discovery/{kind}?origin=mine").json()
        b_lib = b.get(f"/api/discovery/{kind}?origin=library").json()
        assert [x["id"] for x in a_mine] == [mine_ids[kind]] and all(x["library"] is False for x in a_mine), kind
        assert [x["id"] for x in a_lib] == [lib_ids[kind]] and all(x["library"] is True for x in a_lib), kind
        assert b_mine == [] and [x["id"] for x in b_lib] == [lib_ids[kind]], kind
        assert a.get(f"/api/discovery/{kind}").json() == a_mine, kind  # predefinito: «mine»
        assert a.get(f"/api/discovery/{kind}?origin=all").status_code == 422, kind
        assert "SEGRETO-ANNA" not in b.get(f"/api/discovery/{kind}?origin=library").text
    for kind, oid in mine_ids.items():
        if kind == "anomalies":
            continue  # nessuna lettura singola: le anomalie si leggono dall'elenco
        r = b.get(f"/api/discovery/{kind}/{oid}")
        assert r.status_code == 404 and "SEGRETO-ANNA" not in r.text, kind
        assert b.get(f"/api/discovery/{kind}/{lib_ids[kind]}").json()["library"] is True, kind
    # La panoramica conta solo i dati propri; la Biblioteca è un riquadro a parte, uguale per tutti.
    ov_a, ov_b = a.get("/api/discovery/overview").json(), b.get("/api/discovery/overview").json()
    assert ov_a["connections"] == 1 and ov_b["connections"] == 0
    assert ov_a["library"] == ov_b["library"] and ov_b["library"]["connections"] == 1
    assert "SEGRETO-ANNA" not in str(ov_b)
    # Bruno non può agire sui risultati di Anna.
    for method, url, body in [("POST", f"/api/discovery/connections/{mine_ids['connections']}/status", {"status": "dismissed"}),
                              ("PATCH", f"/api/discovery/hypotheses/{mine_ids['hypotheses']}", {"title": "rubata"}),
                              ("POST", f"/api/discovery/anomalies/{mine_ids['anomalies']}", {"status": "dismissed", "note": "x"}),
                              ("POST", f"/api/discovery/sessions/{mine_ids['sessions']}/stop", None)]:
        r = b.request(method, url, json=body)
        assert r.status_code == 404, (url, r.status_code)
