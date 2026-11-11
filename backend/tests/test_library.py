"""Biblioteca NEXUS: dati aperti condivisi in sola lettura, visibili a ogni utente accanto ai propri."""

from nexus.api.schemas_history import EventIn, RelationIn
from nexus.core import library
from nexus.models import Entity
from nexus.services import graph, history


def _library_event(client, title="Panic of 1907", year=1907):
    with client.app.state.database.session_factory() as db:
        lib = library.ensure_library_user(db)
        e = history.create_event(db, lib, EventIn(title=title, start_year=year, categories=["financial_crisis"]))
        e.origin, e.external_id = "wikidata", f"Q{year}"
        db.commit()
        return e.id


def test_library_items_are_visible_but_read_only(client):
    library.reset_cache()
    eid = _library_event(client)
    own = client.post("/api/history/events", json={"title": "Mio evento", "start_year": 1910}).json()
    items = client.get("/api/history/events").json()
    assert {e["title"] for e in items} == {"Panic of 1907", "Mio evento"}
    lib_item = next(e for e in items if e["id"] == eid)
    assert lib_item["library"] is True and own["library"] is False
    assert [e["title"] for e in client.get("/api/history/events?origin=library").json()] == ["Panic of 1907"]
    assert [e["title"] for e in client.get("/api/history/events?origin=mine").json()] == ["Mio evento"]
    assert client.get(f"/api/history/events/{eid}").status_code == 200
    r = client.put(f"/api/history/events/{eid}", json={"title": "x", "start_year": 1907})
    assert r.status_code == 403 and r.json()["error"]["code"] == "read_only"
    assert client.delete(f"/api/history/events/{eid}?confirm=true").status_code == 403
    assert client.post(f"/api/history/events/{eid}/knowledge", json={"content": "x", "known_since_year": 1907}).status_code == 403
    # La ricerca globale trova anche la Biblioteca.
    assert any(h["type"] == "event" and h["title"] == "Panic of 1907" for h in client.get("/api/search?q=Panic").json()["hits"])
    library.reset_cache()


def test_library_graph_is_explored_without_loading_everything(client):
    library.reset_cache()
    a = _library_event(client, "A", 1900)
    b = _library_event(client, "B", 1901)
    with client.app.state.database.session_factory() as db:
        lib = library.ensure_library_user(db)
        ea = db.query(Entity).filter_by(event_id=a).one().id
        eb = db.query(Entity).filter_by(event_id=b).one().id
        src = history.Source(owner_id=lib.id, title="Wikidata", source_type="dataset")
        db.add(src)
        db.commit()
        graph.create_relation(db, lib, RelationIn(source_entity_id=ea, target_entity_id=eb, relation_type="preceded",
                                                  provenance="sourced", source_id=src.id))
    g = client.get("/api/graph").json()
    assert g["stats"]["relations"] == 1 and {n["name"] for n in g["nodes"]} == {"A", "B"}
    focus = client.get(f"/api/graph?focus={ea}&depth=1").json()
    assert {n["name"] for n in focus["nodes"]} == {"A", "B"}
    p = client.get(f"/api/graph/path?source={ea}&target={eb}").json()
    assert p["found"] and p["entity_ids"] == [ea, eb]
    library.reset_cache()


def test_library_discovery_results_are_listed_separately_and_read_only(client):
    from nexus.models import DiscoveryAnomaly, DiscoveryConnection, DiscoveryHypothesis, DiscoverySession

    library.reset_cache()
    eid = _library_event(client)
    with client.app.state.database.session_factory() as db:
        lib = library.ensure_library_user(db)
        s = DiscoverySession(owner_id=lib.id, mode="autonomous", query="", status="completed", limits={}, steps=[], result={})
        db.add(s)
        db.flush()
        c = DiscoveryConnection(owner_id=lib.id, session_id=s.id, fingerprint="f1", kind="event_data_change", title="Panic of 1907 — serie",
                                elements=[{"type": "event", "id": eid, "label": "Panic of 1907"}], period="1907", evidence=[], sources=[],
                                reliability="low", reliability_reasons=[], explanation="x", caveats=[], score=3.0)
        a = DiscoveryAnomaly(owner_id=lib.id, session_id=s.id, fingerprint="a1", kind="series_change", title="Salto", what_changed="x",
                             reference="x", period="1907", data={}, alternatives=[], refs={}, relevance=5.0, verifiability="high")
        db.add_all([c, a])
        db.flush()
        h = DiscoveryHypothesis(owner_id=lib.id, session_id=s.id, connection_id=c.id, fingerprint="f1", origin="rules", title="Ipotesi",
                                description="x", phenomena=[], motivation="x", supporting=[], contrary=[], missing=[], method="x", confidence="low")
        db.add(h)
        db.commit()
        cid, aid, hid, sid = c.id, a.id, h.id, s.id
    # Le liste dell'utente restano sue; la Biblioteca si chiede esplicitamente.
    assert client.get("/api/discovery/connections").json() == []
    lib_c = client.get("/api/discovery/connections?origin=library").json()
    assert [x["id"] for x in lib_c] == [cid] and lib_c[0]["library"] is True
    assert [x["id"] for x in client.get("/api/discovery/anomalies?origin=library").json()] == [aid]
    assert [x["id"] for x in client.get("/api/discovery/hypotheses?origin=library").json()] == [hid]
    assert [x["id"] for x in client.get("/api/discovery/sessions?origin=library").json()] == [sid]
    ov = client.get("/api/discovery/overview").json()
    assert ov["connections"] == 0 and ov["library"]["connections"] == 1 and ov["library"]["session_id"] == sid
    # Dettagli leggibili, azioni rifiutate.
    assert client.get(f"/api/discovery/connections/{cid}").json()["library"] is True
    assert client.get(f"/api/discovery/hypotheses/{hid}").status_code == 200
    for method, url, body in [("post", f"/api/discovery/connections/{cid}/status", {"status": "dismissed"}),
                              ("post", f"/api/discovery/connections/{cid}/hypothesis", None),
                              ("post", f"/api/discovery/hypotheses/{hid}/archive", None),
                              ("post", f"/api/discovery/hypotheses/{hid}/decision", {"status": "rejected", "note": ""}),
                              ("post", f"/api/discovery/anomalies/{aid}", {"status": "dismissed", "note": ""}),
                              ("post", f"/api/discovery/sessions/{sid}/stop", None)]:
        r = getattr(client, method)(url, json=body) if body is not None else getattr(client, method)(url)
        assert r.status_code == 403 and r.json()["error"]["code"] == "read_only", url
    library.reset_cache()


def test_library_summary_counts_shared_open_data(client):
    library.reset_cache()
    assert client.get("/api/library/summary").json() == {"available": False}
    _library_event(client)
    s = client.get("/api/library/summary").json()
    assert s["available"] is True and s["events"] == 1 and s["series"] == 0
    library.reset_cache()
