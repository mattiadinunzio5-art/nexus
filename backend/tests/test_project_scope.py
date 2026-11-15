"""Ambito di progetto: elementi propri e della Biblioteca collegati a un progetto, filtri «solo progetto», panoramica."""

import pytest


@pytest.fixture
def setup(client):
    p = client.post("/api/projects", json={"title": "Plastica", "research_question": "Quanto è cresciuta?"}).json()
    other = client.post("/api/projects", json={"title": "Altro"}).json()
    s1 = client.post("/api/sources", json={"source_type": "article", "title": "Plastics ever made", "authors": ["Geyer, R."], "year": 2017}).json()
    s2 = client.post("/api/sources", json={"source_type": "book", "title": "Steel history", "year": 1990}).json()
    ev = client.post("/api/history/events", json={"title": "Invenzione della bachelite", "start_year": 1907}).json()
    ev2 = client.post("/api/history/events", json={"title": "Crisi del 1929", "start_year": 1929}).json()
    return p, other, s1, s2, ev, ev2


def test_only_project_items_are_listed(client, setup):
    p, other, s1, s2, ev, ev2 = setup
    assert client.post(f"/api/projects/{p['id']}/items", json={"item_type": "source", "item_id": s1["id"]}).status_code == 201
    client.post(f"/api/projects/{p['id']}/items", json={"item_type": "event", "item_id": ev["id"]})
    client.post(f"/api/projects/{p['id']}/items", json={"item_type": "event", "item_id": ev["id"]})  # idempotente
    titles = [s["title"] for s in client.get("/api/sources", params={"project_id": p["id"]}).json()]
    assert titles == ["Plastics ever made"]
    events = [e["title"] for e in client.get("/api/history/events", params={"project_id": p["id"]}).json()]
    assert events == ["Invenzione della bachelite"]
    # L'entità dell'evento entra nel progetto con lui.
    ents = client.get("/api/graph/entities", params={"project_id": p["id"]}).json()
    assert [e["event_id"] for e in ents] == [ev["id"]]
    assert client.get("/api/sources", params={"project_id": other["id"]}).json() == []
    assert client.get(f"/api/projects/linked/source/{s1['id']}").json() == [p["id"]]
    assert client.delete(f"/api/projects/{p['id']}/items/source/{s1['id']}").status_code == 204
    assert client.get("/api/sources", params={"project_id": p["id"]}).json() == []


def test_document_uploaded_with_project_is_in_scope(client, setup):
    p = setup[0]
    d = client.post("/api/documents", files={"file": ("a.txt", b"Plastic production grew fast.\n" * 3)},
                    data={"title": "Doc del progetto", "category": "source_material", "project_id": str(p["id"])}).json()
    client.post("/api/documents", files={"file": ("b.txt", b"Unrelated text here.\n" * 3)}, data={"title": "Altro doc", "category": "source_material"})
    assert [x["title"] for x in client.get("/api/documents", params={"project_id": p["id"]}).json()] == ["Doc del progetto"]
    assert client.delete(f"/api/projects/{p['id']}/items/document/{d['id']}").status_code == 204
    assert client.get("/api/documents", params={"project_id": p["id"]}).json() == []


def test_overview_lists_what_is_missing(client, setup):
    p, _, s1, s2, ev, _ = setup
    for s in (s1, s2):
        client.post(f"/api/projects/{p['id']}/items", json={"item_type": "source", "item_id": s["id"]})
    ov = client.get(f"/api/projects/{p['id']}/overview").json()
    assert ov["counts"]["source"] == 2 and ov["counts"]["event"] == 0
    checks = {c["key"]: c["ok"] for c in ov["checks"]}
    assert checks["question"] and not checks["objectives"] and not checks["sources"] and not checks["data"]
    assert 0 < ov["progress"] < 1


def test_items_of_other_users_cannot_be_linked(client, setup, db):
    from nexus.models import Source, User

    p = setup[0]
    stranger = User(email="x@example.org", display_name="X")
    db.add(stranger)
    db.flush()
    foreign = Source(owner_id=stranger.id, title="Privata", source_type="other")
    db.add(foreign)
    db.commit()
    r = client.post(f"/api/projects/{p['id']}/items", json={"item_type": "source", "item_id": foreign.id})
    assert r.status_code == 404


def test_graph_explore_restricted_to_project(client, setup):
    p, _, _, _, ev, ev2 = setup
    client.post(f"/api/projects/{p['id']}/items", json={"item_type": "event", "item_id": ev["id"]})
    g = client.get("/api/graph", params={"project_id": p["id"]}).json()
    assert [n["name"] for n in g["nodes"]] == ["Invenzione della bachelite"]
