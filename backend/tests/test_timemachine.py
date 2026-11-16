"""Time Machine: tre date distinte, disponibilità all'epoca, fonti e completezza della ricostruzione."""

from datetime import datetime, timezone

from nexus.models import Observation, Series, User

from .test_history import CRASH, DEPRESSION, ev


def _src(client, title, year, **kw):
    return client.post("/api/sources", json={"title": title, "year": year, **kw}).json()["id"]


def _k(client, eid, **data):
    return client.post(f"/api/history/events/{eid}/knowledge", json=data)


def test_knowledge_keeps_event_publication_and_availability_dates(client):
    crash = ev(client, CRASH)
    r = _k(client, crash["id"], content="Il New York Times riporta vendite di panico.", kind="contemporary",
           refers_to="1929-10-24", published_on="1929-10-25", available_on="1929-10-25")
    assert r.status_code == 200, r.text
    k = r.json()["knowledge"][0]
    assert (k["refers_to"], k["published_on"], k["available_on"], k["known_since_year"]) == ("1929-10-24", "1929-10-25", "1929-10-25", 1929)
    # Un dato ufficiale pubblicato anni dopo: disponibile dal 1932.
    r = _k(client, crash["id"], content="Stima ufficiale delle perdite.", kind="later_discovery", refers_to="1929", published_on="1932")
    assert r.json()["knowledge"][-1]["known_since_year"] == 1932
    # Incoerenze rifiutate: disponibile prima della pubblicazione, contemporanea pubblicata prima del fatto, nessuna data.
    assert _k(client, crash["id"], content="x", published_on="1935", available_on="1931").status_code == 422
    assert _k(client, crash["id"], content="x", refers_to="1929-10-24", published_on="1928", available_on="1929").status_code == 422
    assert _k(client, crash["id"], content="x").status_code == 422


def test_then_vs_later_with_sources_and_dates(client):
    crash = ev(client, CRASH)
    s_then = _src(client, "The New York Times, 25 ottobre 1929", 1929, evidence_class="primary")
    s_later = _src(client, "The Great Crash 1929", 1955, authors=["John Kenneth Galbraith"], evidence_class="secondary")
    client.post(f"/api/history/events/{crash['id']}/sources", json={"source_id": s_then, "pages": "1"})
    client.post(f"/api/history/events/{crash['id']}/sources", json={"source_id": s_later, "pages": ""})
    _k(client, crash["id"], content="Vendite di panico a Wall Street.", kind="contemporary", source_id=s_then,
       refers_to="1929-10-24", published_on="1929-10-25")
    _k(client, crash["id"], content="Il crollo ebbe cause strutturali.", kind="historiography", source_id=s_later, published_on="1955")
    strict = client.get("/api/history/timeline?as_of_year=1931").json()
    c = next(e for e in strict["events"] if e["title"] == CRASH["title"])
    assert [k["availability"] for k in c["known_then"]] == ["then"] and "The New York Times" in c["known_then"][0]["source_citation"]
    assert c["known_then"][0]["published_on"] == "1929-10-25" and c["hidden_later_count"] == 1
    # In vista rigorosa la fonte pubblicata dopo la data è nascosta; con il senno di poi compare, marcata.
    assert [s["source_id"] for s in c["sources"]] == [s_then] and c["date_precision"] == "day"
    hs = client.get("/api/history/timeline?as_of_year=1931&hindsight=true").json()
    c2 = next(e for e in hs["events"] if e["title"] == CRASH["title"])
    after = {s["source_id"]: s["published_after"] for s in c2["sources"]}
    assert after == {s_then: False, s_later: True}
    assert [k["availability"] for k in c2["known_later"]] == ["later"]


def test_completeness_indicator_and_gaps(client, db):
    crash = ev(client, CRASH)
    ev(client, DEPRESSION)  # nessuna fonte, nessuna informazione datata, solo anno
    s = _src(client, "The New York Times, 25 ottobre 1929", 1929)
    client.post(f"/api/history/events/{crash['id']}/sources", json={"source_id": s, "pages": "1"})
    _k(client, crash["id"], content="Vendite di panico.", kind="contemporary", published_on="1929-10-25")
    user = db.query(User).first()
    for name, published in (("Produzione industriale USA (versione 1931)", "1931-01-15"), ("PIL USA ricostruito", "2023-09-28")):
        x = Series(owner_id=user.id, name=name, category="other", country="United States", connector="upload", source_series_id=name,
                   source_label="Fonte di prova", unit="indice", frequency="A", params={}, source_last_updated=published,
                   retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        x.observations = [Observation(date="1929-01-01", value=100.0), Observation(date="1930-01-01", value=80.0)]
        db.add(x)
    db.commit()
    t = client.get("/api/history/timeline?as_of_year=1931").json()
    c = t["completeness"]
    comps = {x["key"]: (x["ok"], x["total"]) for x in c["components"]}
    assert comps == {"sources": (1, 2), "knowledge": (1, 2), "dates": (1, 2), "indicators": (1, 2)}
    assert c["score"] == 0.5 and c["level"] == "medium"
    assert any("Grande Depressione" in g for g in c["gaps"]) and any("ricostruzioni successive" in g for g in c["gaps"])
    ind = {i["name"]: i for i in t["indicators"]}
    assert ind["PIL USA ricostruito"]["availability"] == "retrospective" and ind["PIL USA ricostruito"]["published"] == 2023
    assert ind["Produzione industriale USA (versione 1931)"]["availability"] == "available"
    assert ind["PIL USA ricostruito"]["last_date"] == "1930-01-01" and ind["PIL USA ricostruito"]["retrieved_at"].startswith("2026-01-01")
    # Senza data scelta non c'è ricostruzione da valutare.
    assert client.get("/api/history/timeline").json()["completeness"] is None


def test_empty_reconstruction_scores_zero(client):
    t = client.get("/api/history/timeline?as_of_year=1800").json()
    assert t["completeness"]["score"] == 0 and t["completeness"]["level"] == "low" and len(t["completeness"]["gaps"]) == 2
