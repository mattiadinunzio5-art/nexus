"""NEXUS Discovery Intelligence: connessioni, ipotesi, anomalie, catene causali, scenari, sessioni."""

import numpy as np
import pytest
from sqlalchemy import select

from nexus.api.schemas_history import EntityIn, EventIn, RelationIn
from nexus.api.schemas_research import SourceIn
from nexus.discovery import anomalies as an
from nexus.discovery import connections as cx
from nexus.discovery import evidence as ev
from nexus.models import DiscoverySession, Entity, Observation, Series, User
from nexus.services import graph, history, sources


@pytest.fixture
def user(db):
    return db.scalar(select(User))


def _series(db, user, name, values, start=2000, freq="A", connector="upload", category="other", country="Italy", unit="%"):
    s = Series(owner_id=user.id, name=name, category=category, country=country, connector=connector, source_series_id=name,
               source_label=f"Fonte di prova ({name})", unit=unit, frequency=freq, params={})
    if freq == "A":
        dates = [f"{start + i}-01-01" for i in range(len(values))]
    else:
        dates = [f"{start + i // 12}-{i % 12 + 1:02d}-01" for i in range(len(values))]
    s.observations = [Observation(date=d, value=float(v)) for d, v in zip(dates, values)]
    s.observation_count = len(values)
    db.add(s)
    db.commit()
    return s


def _event(db, user, title, year, **kw):
    return history.create_event(db, user, EventIn(title=title, start_year=year, **kw))


# --- Valutazione delle fonti ------------------------------------------------------------------------


def test_independence_counts_sources_sharing_a_primary_source_once(db, user):
    primary = sources.create_source(db, user, SourceIn(source_type="document", title="Rapporto ufficiale", publisher="Banca d'Italia", year=2009))
    a = sources.create_source(db, user, SourceIn(source_type="article", title="Articolo A", year=2010, primary_source_id=primary.id))
    b = sources.create_source(db, user, SourceIn(source_type="article", title="Articolo B", year=2010, primary_source_id=primary.id))
    other = sources.create_source(db, user, SourceIn(source_type="book", title="Libro indipendente", year=2012))
    assert len(ev.independent_groups(db, [a, b])) == 1
    assert len(ev.independent_groups(db, [a, b, other])) == 2
    level, reasons, assessed = ev.grade(db, [a, b])
    assert "2 fonti, 1 indipendenti" in reasons[0] and level != "high"
    assert ev.assess_source(primary)["authority"] == "high" and ev.assess_source(primary)["originality"] == "primary"
    assert ev.assess_source(a)["originality"] == "derived"
    with pytest.raises(Exception, match="ciclo"):
        sources.update_source(db, user, primary.id, SourceIn(source_type="document", title="Rapporto ufficiale", primary_source_id=a.id))


# --- Knowledge Graph: niente duplicati --------------------------------------------------------------


def test_graph_rejects_duplicate_entities_by_name_and_alias(db, user):
    graph.create_entity(db, user, EntityIn(entity_type="institution", name="Banca Centrale Europea", aliases=["BCE", "ECB"]))
    for name in ("banca centrale europea", "ECB", "Banca  Centrale  Europea!"):
        with pytest.raises(Exception, match="già presente"):
            graph.create_entity(db, user, EntityIn(entity_type="institution", name=name))
    graph.create_entity(db, user, EntityIn(entity_type="person", name="Mario Rossi"))  # tipo diverso, nome diverso: ok


# --- Discovery Engine ------------------------------------------------------------------------------


def test_event_connections_shared_actors_and_textual_reference(db, user):
    bw = _event(db, user, "Fine di Bretton Woods", 1971, countries=["United States"], categories=["monetary"], people=["Richard Nixon"])
    oil = _event(db, user, "Primo shock petrolifero", 1973, countries=["United States"], categories=["economic"], people=["Richard Nixon"])
    fx = _event(db, user, "Cambi flessibili", 1973, causes="Conseguenza della fine di Bretton Woods e della crisi del dollaro.")
    unrelated = _event(db, user, "Rivoluzione industriale", 1760)
    cands = cx.event_connections(db, [bw, oil, fx, unrelated], set())
    kinds = {(c.kind, frozenset(e["id"] for e in c.elements)) for c in cands}
    assert ("shared_actors", frozenset({bw.id, oil.id})) in kinds
    assert ("textual_reference", frozenset({bw.id, fx.id})) in kinds
    assert not any(unrelated.id in {e["id"] for e in c.elements} for c in cands)
    for c in cands:
        assert any("causa" in x.lower() for x in c.caveats)  # mai presentata come causalità
        assert c.reliability == "low"  # nessuna fonte collegata
    # Se il grafo li collega già, non è una scoperta.
    assert not cx.event_connections(db, [bw, oil], {frozenset((("event", bw.id), ("event", oil.id)))})


def test_statistical_association_on_changes_not_levels(db, user):
    rng = np.random.default_rng(1)
    x = np.cumsum(rng.normal(size=60))
    y = np.concatenate([[0], x[:-1]]) * 2 + rng.normal(scale=0.3, size=60)  # y segue x con un periodo di ritardo
    trend_a = np.arange(60) + rng.normal(scale=0.1, size=60)  # due trend indipendenti: correlati nei livelli, non nelle variazioni
    trend_b = np.arange(60) * 3 + rng.normal(scale=0.1, size=60)
    sa, sb = _series(db, user, "Tasso A", x, start=1950), _series(db, user, "Indice B", y, start=1950)
    ta, tb = _series(db, user, "Trend A", trend_a, start=1950), _series(db, user, "Trend B", trend_b, start=1950)
    out = cx.series_connections(db, [sa, sb, ta, tb])
    pairs = {frozenset(e["id"] for e in c.elements) for c in out}
    assert frozenset({sa.id, sb.id}) in pairs
    assert frozenset({ta.id, tb.id}) not in pairs
    c = next(c for c in out if frozenset(e["id"] for e in c.elements) == frozenset({sa.id, sb.id}))
    assert "anticipa di 1" in " ".join(e["detail"] for e in c.evidence) and "Correlazione, non causalità" in c.caveats[0]


def test_event_data_change_requires_country_and_a_real_jump(db, user):
    vals = [1.0 + 0.1 * (i % 3) for i in range(30)]
    vals[20:] = [v + 8 for v in vals[20:]]  # salto nel 2020
    s = _series(db, user, "Inflazione Italia", vals, start=2000, country="ITA")
    e_it = _event(db, user, "Shock in Italia", 2020, countries=["Italia"])
    e_fr = _event(db, user, "Shock in Francia", 2020, countries=["France"])
    e_quiet = _event(db, user, "Evento tranquillo", 2008, countries=["Italy"])
    out = cx.event_data_connections(db, [e_it, e_fr, e_quiet], [s])
    assert [c.elements[0]["id"] for c in out] == [e_it.id]


def test_graph_proximity_and_series_entity(db, user):
    mk = lambda n, t="institution": graph.create_entity(db, user, EntityIn(entity_type=t, name=n))  # noqa: E731
    a, b, c, d = mk("Banca A"), mk("Banca B"), mk("Mercato interbancario", "concept"), mk("Regolatore X")
    for src, tgt in ((a, c), (b, c), (a, d), (b, d)):
        graph.create_relation(db, user, RelationIn(source_entity_id=src.id, target_entity_id=tgt.id, relation_type="involved_in", provenance="user_hypothesis"))
    from nexus.models import Relation

    ents = {e.id: e for e in db.scalars(select(Entity))}
    out = cx.graph_connections(db, user, ents, list(db.scalars(select(Relation))), None)
    assert any({x["id"] for x in o.elements} == {a.id, b.id} for o in out)
    assert all(o.reliability == "low" for o in out)  # i collegamenti intermedi sono ipotesi


# --- Anomalie ---------------------------------------------------------------------------------------


def test_anomalies_series_discrepancy_chronology_and_insufficient_data(db, user):
    vals = [2.0 + 0.1 * np.sin(i) for i in range(40)]
    vals[30] = 15.0
    s = _series(db, user, "Inflazione (WB)", vals, start=1980, connector="world-bank", category="inflation")
    other = [v for v in vals]
    other[10] += 3.0
    s2 = _series(db, user, "Inflazione (Eurostat)", other, start=1980, connector="eurostat", category="inflation")
    short = _series(db, user, "Corta", [1, 2, 3], start=2000)
    skipped: dict = {}
    found = an.series_anomalies([s, short], [], skipped)
    assert any(a.kind == "series_change" and a.period.startswith("2010") for a in found)
    assert skipped["series_too_short"] == 1
    disc = an.source_discrepancies([s, s2], skipped)
    assert len(disc) == 1 and disc[0].data["periods"][0]["date"].startswith("1990")
    late = _event(db, user, "Effetto", 1990)
    early = _event(db, user, "Causa", 2000)
    ea, eb = (db.scalar(select(Entity).where(Entity.event_id == x.id)) for x in (early, late))
    r = graph.create_relation(db, user, RelationIn(source_entity_id=ea.id, target_entity_id=eb.id, relation_type="caused", provenance="user_hypothesis"))
    ents = {e.id: e for e in db.scalars(select(Entity))}
    chrono = an.chronology_issues(db, [late, early], [r], ents)
    assert len(chrono) == 1 and "Ordine temporale" in chrono[0].title


# --- Sessioni, ipotesi, catene, scenari via API ------------------------------------------------------


def _archive(db, user):
    src = sources.create_source(db, user, SourceIn(source_type="book", title="Storia monetaria", publisher="University Press", year=1990))
    bw = _event(db, user, "Fine di Bretton Woods", 1971, countries=["United States"], categories=["monetary"], institutions=["Federal Reserve"],
                reliability="established")
    history.link_source(db, user, bw.id, src.id, "12", "")
    _event(db, user, "Crisi del dollaro", 1973, countries=["United States"], categories=["monetary"], institutions=["Federal Reserve"])
    rng = np.random.default_rng(3)
    x = np.cumsum(rng.normal(size=48))
    _series(db, user, "Tassi USA", x, start=1960, country="USA")
    _series(db, user, "Dollaro", np.concatenate([[0], x[:-1]]) + rng.normal(scale=0.2, size=48), start=1960, country="USA")


def test_guided_session_end_to_end(client, db, user):
    _archive(db, user)
    r = client.post("/api/discovery/sessions", json={"mode": "guided", "query": "Connessioni tra la fine di Bretton Woods, il dollaro e i tassi"})
    assert r.status_code == 201, r.text
    s = client.get(f"/api/discovery/sessions/{r.json()['id']}").json()
    assert s["status"] == "completed", s
    assert [x["step"] for x in s["steps"]] == ["understand", "connections", "anomalies", "hypotheses", "causal", "synthesis"]
    assert s["scope"]["restricted"] and len(s["scope"]["event_ids"]) == 2
    assert s["result"]["synthesis"]["executor"] == "local"
    conns = client.get("/api/discovery/connections").json()
    kinds = {c["kind"] for c in conns}
    assert {"shared_actors", "statistical_association"} <= kinds
    hyps = client.get("/api/discovery/hypotheses").json()
    assert hyps and all(h["status"] == "to_verify" and h["confidence"] in ("low", "medium") for h in hyps)
    assert all("non è una scoperta dimostrata" in h["description"] for h in hyps)
    # Deduplicazione: una seconda sessione non ricrea le stesse connessioni.
    r2 = client.post("/api/discovery/sessions", json={"mode": "guided", "query": "Bretton Woods dollaro tassi"}).json()
    s2 = client.get(f"/api/discovery/sessions/{r2['id']}").json()
    assert s2["steps"][1]["counts"]["new"] == 0 and len(client.get("/api/discovery/connections").json()) == len(conns)
    # Verifica, decisione motivata, archivio, nodo nel grafo.
    stat = next(h for h in hyps if "variazioni" in h["title"])
    v = client.post(f"/api/discovery/hypotheses/{stat['id']}/verify").json()
    assert v["status"] == "verifying" and v["verification"][-1]["checks"][0]["check"] == "Stabilità nei sottoperiodi"
    assert client.post(f"/api/discovery/hypotheses/{stat['id']}/decision", json={"status": "confirmed", "note": ""}).status_code == 422
    d = client.post(f"/api/discovery/hypotheses/{stat['id']}/decision", json={"status": "inconclusive", "note": "Manca un meccanismo documentato"}).json()
    assert d["status"] == "inconclusive" and d["decided_at"]
    g = client.post(f"/api/discovery/hypotheses/{stat['id']}/graph").json()
    assert db.get(Entity, g["graph_entity_id"]).entity_type == "hypothesis"
    # Accettare una connessione la salva nel grafo come ipotesi, mai come relazione documentata.
    acc = client.post(f"/api/discovery/connections/{conns[0]['id']}/status", json={"status": "accepted"}).json()
    from nexus.models import Relation

    assert db.get(Relation, acc["graph_relation_id"]).provenance == "ai_hypothesis"
    ov = client.get("/api/discovery/overview").json()
    assert ov["connections"] == len(conns) and ov["hypotheses_by_status"]["inconclusive"] == 1


def test_autonomous_session_with_empty_archive_reports_limits(client):
    r = client.post("/api/discovery/sessions", json={"mode": "autonomous"}).json()
    s = client.get(f"/api/discovery/sessions/{r['id']}").json()
    assert s["status"] == "completed" and s["result"]["counts"] == {"connections": 0, "hypotheses": 0, "anomalies": 0, "chains": 0}
    assert "non contiene ancora abbastanza materiale" in s["result"]["synthesis"]["text"]
    assert client.get("/api/discovery/connections").json() == []
    assert client.post("/api/discovery/sessions", json={"mode": "guided", "query": " "}).status_code == 422


def test_session_pause_resume_and_stop(client, db, user):
    s = DiscoverySession(owner_id=user.id, mode="autonomous", status="running", limits={"max_seconds": 60, "max_llm_calls": 0, "max_items": 10})
    db.add(s)
    db.commit()
    assert client.post("/api/discovery/sessions", json={"mode": "autonomous"}).status_code == 409  # una alla volta
    assert client.post(f"/api/discovery/sessions/{s.id}/pause").json()["status"] == "paused"
    assert client.post(f"/api/discovery/sessions/{s.id}/pause").status_code == 409
    done = client.post(f"/api/discovery/sessions/{s.id}/resume").json()
    assert client.get(f"/api/discovery/sessions/{done['id']}").json()["status"] == "completed"
    assert client.post(f"/api/discovery/sessions/{s.id}/stop").status_code == 409


def test_session_time_limit_stops_with_partial_results(client, db, user):
    _archive(db, user)
    s = DiscoverySession(owner_id=user.id, mode="autonomous", status="queued", limits={"max_seconds": 0, "max_llm_calls": 0, "max_items": 10})
    db.add(s)
    db.commit()
    from nexus.services import discovery

    discovery.run_in_background(client.app.state.database, client.app.state.settings, s.id)
    out = client.get(f"/api/discovery/sessions/{s.id}").json()
    assert out["status"] == "stopped" and "Limite di tempo" in out["error"]


def test_causal_chain_classification_and_alternatives(client, db, user):
    mk = lambda n, t="concept": graph.create_entity(db, user, EntityIn(entity_type=t, name=n))  # noqa: E731
    rates, credit, invest, shock = mk("Aumento dei tassi"), mk("Costo del credito"), mk("Investimenti"), mk("Shock di domanda")
    src = sources.create_source(db, user, SourceIn(source_type="book", title="Manuale di macroeconomia", year=2010))
    graph.create_relation(db, user, RelationIn(source_entity_id=rates.id, target_entity_id=credit.id, relation_type="caused", provenance="sourced", source_id=src.id))
    graph.create_relation(db, user, RelationIn(source_entity_id=invest.id, target_entity_id=credit.id, relation_type="consequence_of", provenance="user_hypothesis"))
    graph.create_relation(db, user, RelationIn(source_entity_id=shock.id, target_entity_id=invest.id, relation_type="influenced", provenance="sourced", source_id=src.id))
    a = client.post("/api/discovery/causal/chains", json={"start": rates.id, "end": invest.id}).json()
    path = a["result"]["paths"][0]
    assert path["nodes"] == ["Aumento dei tassi", "Costo del credito", "Investimenti"]
    assert [x["class"] for x in path["links"]] == ["causal_documented", "causal_hypothesized"]
    assert path["strength"] == "causal_hypothesized" and "Shock di domanda" in path["links"][1]["alternatives"]
    none = client.post("/api/discovery/causal/chains", json={"start": invest.id, "end": rates.id}).json()
    assert none["result"]["paths"] == [] and none["result"]["notes"]


def test_transmission_and_foresight(client, db, user):
    rng = np.random.default_rng(5)
    x = np.cumsum(rng.normal(size=40)) + 5
    a = _series(db, user, "Tasso di policy", x, start=1980)
    b = _series(db, user, "Disoccupazione", np.concatenate([[5], x[:-1]]) * 0.5 + rng.normal(scale=0.1, size=40), start=1980)
    t = client.post("/api/discovery/causal/transmission", json={"series_ids": [a.id, b.id], "labels": ["Tassi", "Disoccupazione"]}).json()
    step = t["result"]["steps"][0]
    assert step["class"] == "correlation" and step["statistic"]["lag"] == 1 and step["alternatives"]
    assert db.scalar(select(Entity).where(Entity.series_id == a.id)) is not None  # nodo indicatore creato una sola volta
    f = client.post("/api/discovery/foresight", json={"variables": [{"series_id": a.id, "favorable": "down"}, {"series_id": b.id, "favorable": "down"}],
                                                      "horizon_years": 3}).json()["result"]
    v = f["variables"][0]
    assert v["adverse"] >= v["central"] >= v["optimistic"]  # per una variabile «meglio se scende» lo scenario avverso è il più alto
    assert set(f["scenarios"]) == {"optimistic", "central", "adverse"}
    assert f["probability_note"] and f["uncertainties"] and f["indicators_to_monitor"]
    short = _series(db, user, "Poche osservazioni", [1, 2, 3, 4, 5], start=2000)
    r = client.post("/api/discovery/foresight", json={"variables": [{"series_id": short.id}], "horizon_years": 1})
    assert r.status_code == 422 and "almeno 20" in r.json()["error"]["message"]
    assert len(client.get("/api/discovery/analyses").json()) == 2
