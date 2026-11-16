"""Causal Engine e Scenario Simulator: dati mancanti, dipendenze, origine delle relazioni, riproducibilità.

Principi verificati:
* una variazione a cavallo di periodi mancanti non è una variazione di un periodo (né un'anomalia);
* le serie che crescono di ordini di grandezza si proiettano in variazioni percentuali;
* gli scenari estremi segnalano quando combinano variabili che storicamente non si muovono insieme in quel senso;
* nelle catene causali le ipotesi dell'AI sono distinte, e una fonte di identità dubbia non rende «documentata» una relazione;
* stessi parametri, stesso seme e stessi dati = stesso risultato, con l'impronta dei dati registrata.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from nexus.api.schemas_history import EntityIn, RelationIn
from nexus.discovery import causal, connections, foresight
from nexus.finance import analytics
from nexus.models import Entity, Observation, Series, Source, User
from nexus.services import graph


@pytest.fixture
def user(db):
    return db.scalar(select(User))


def _series(db, user, name, values, start=1950, freq="A", skip=(), unit="%"):
    s = Series(owner_id=user.id, name=name, connector="upload", source_series_id=name, source_label=f"Prova ({name})",
               unit=unit, frequency=freq, params={})
    obs = []
    for i, v in enumerate(values):
        year = start + i
        if year in skip:
            continue
        obs.append(Observation(date=f"{year}-01-01", value=float(v)))
    s.observations = obs
    s.observation_count = len(obs)
    db.add(s)
    db.commit()
    return s


# --- Dati mancanti -----------------------------------------------------------------------------------


def test_changes_never_bridge_missing_periods():
    years = [y for y in range(1980, 2001) if y not in (1990, 1991, 1992, 1993, 1994)]
    s = pd.Series([float(y) for y in years], index=pd.to_datetime([f"{y}-01-01" for y in years]))
    d, info = analytics.changes(s, "A")
    assert info == {"gaps": 1, "irregular": False}
    assert len(d) == len(years) - 2 and (d == 1.0).all()  # il salto 1989→1995 (6 punti) è escluso
    assert "1 variazioni escluse" in analytics.gaps_note("x", info)
    # Serie irregolare per costruzione (date dei cambiamenti di un tasso): nessuna esclusione, ma dichiarata.
    dates = pd.to_datetime(["2001-01-03", "2001-05-15", "2002-11-06", "2004-06-30", "2006-06-29"])
    d, info = analytics.changes(pd.Series([6.0, 4.0, 1.25, 1.25, 5.25], index=dates), "M")
    assert info["irregular"] is True and len(d) == 4 and "irregolari" in analytics.gaps_note("tasso", info)


def test_a_gap_is_not_reported_as_an_anomalous_jump():
    years = [y for y in range(1960, 2021) if not 1990 <= y <= 1999]
    vals = [100 + 0.5 * (y - 1960) + (0.05 if y % 2 else -0.05) for y in years]
    s = pd.Series(vals, index=pd.to_datetime([f"{y}-01-01" for y in years]))
    assert analytics.anomalies(s) != []  # senza frequenza: il «salto» di 10 anni sembra anomalo
    assert analytics.anomalies(s, freq="A") == []


def test_lagged_association_reports_excluded_changes(db, user):
    rng = np.random.default_rng(1)
    base = np.cumsum(rng.normal(size=40))
    a = _series(db, user, "A", base, skip={1970, 1971})
    b = _series(db, user, "B", base + rng.normal(scale=0.1, size=40))
    res = connections.lagged_association(connections.series_frame(a), connections.series_frame(b), "A", "A", max_lag=0)
    assert res["gaps_excluded"] == 1 and res["r"] > 0.9


# --- Scenari (Strategic Foresight) -------------------------------------------------------------------


def test_growing_series_are_projected_in_percentage_changes(db, user):
    s = _series(db, user, "PIL", [100 * 1.05 ** t for t in range(70)])
    r = foresight.scenarios(db, user, [{"series_id": s.id}], 2)
    v = r["variables"][0]
    assert v["changes"] == "percentuali (log)"
    last = 100 * 1.05 ** 69
    assert v["central"] == pytest.approx(last * 1.05 ** 2, rel=1e-6)  # con variazioni assolute sarebbe molto più basso


def test_extreme_scenarios_flag_variables_that_do_not_move_together(db, user):
    rng = np.random.default_rng(3)
    shocks = rng.normal(size=60)
    growth = _series(db, user, "Crescita", 2 + np.cumsum(shocks))
    jobs = _series(db, user, "Occupazione", 50 + np.cumsum(shocks + rng.normal(scale=0.2, size=60)))
    # Meglio se la crescita sale e se l'occupazione scende: in passato salivano insieme → estremi incoerenti.
    r = foresight.scenarios(db, user, [{"series_id": growth.id, "favorable": "up"}, {"series_id": jobs.id, "favorable": "down"}], 2)
    dep = r["dependencies"][0]
    assert dep["significant"] and dep["r"] > 0.8 and dep["conflict"] is True
    assert any("poco coerenti" in u for u in r["uncertainties"])
    r = foresight.scenarios(db, user, [{"series_id": growth.id, "favorable": "up"}, {"series_id": jobs.id, "favorable": "up"}], 2)
    assert r["dependencies"][0]["conflict"] is False and not any("poco coerenti" in u for u in r["uncertainties"])


def test_foresight_is_reproducible_and_fingerprints_the_data(db, user):
    s = _series(db, user, "Indice", 100 + np.cumsum(np.random.default_rng(5).normal(size=50)), skip={1980})
    r1 = foresight.scenarios(db, user, [{"series_id": s.id}], 3)
    r2 = foresight.scenarios(db, user, [{"series_id": s.id}], 3)
    assert r1["variables"] == r2["variables"]
    rep = r1["reproducibility"]
    assert rep["seed"] == foresight.SEED and rep["data"]["Indice"] == r1["variables"][0]["data_fingerprint"]
    assert any("1 variazioni escluse" in n for n in r1["data_notes"])
    s.observations[-1].value = s.observations[-1].value + 1
    db.commit()
    assert foresight.scenarios(db, user, [{"series_id": s.id}], 3)["reproducibility"]["data"]["Indice"] != rep["data"]["Indice"]


# --- Catene causali --------------------------------------------------------------------------------


def test_chain_links_show_who_proposed_them_and_doubtful_sources(db, user):
    def ent(n):
        return graph.create_entity(db, user, EntityIn(entity_type="theory", name=n))

    a, b, c = ent("Stretta monetaria"), ent("Credito"), ent("Investimenti")
    bad = Source(owner_id=user.id, title="Studio citato male", source_type="article", verification_status="registry_mismatch")
    db.add(bad)
    db.commit()
    graph.create_relation(db, user, RelationIn(source_entity_id=a.id, target_entity_id=b.id, relation_type="caused",
                                               provenance="sourced", source_id=bad.id))
    graph.create_relation(db, user, RelationIn(source_entity_id=b.id, target_entity_id=c.id, relation_type="caused",
                                               provenance="user_hypothesis"), provenance_override="ai_hypothesis")
    res = causal.chains(db, user, a.id, c.id)
    l1, l2 = res["paths"][0]["links"]
    assert l1["class"] == "causal_hypothesized" and "identità dubbia" in l1["caution"] and "attenzione" in l1["evidence"]
    assert l2["origin"] == "ai_hypothesis" and "generata dall'AI" in l2["label"]
    assert res["paths"][0]["strength"] != "causal_documented"
    notes = " ".join(res["notes"])
    assert "1 anelli sono ipotesi generate dall'AI" in notes and "1 anelli hanno una fonte con identità dubbia" in notes
    assert "non verifica che la fonte la sostenga" in notes


def test_transmission_corrects_for_the_number_of_steps(db, user):
    rng = np.random.default_rng(7)
    x = np.cumsum(rng.normal(size=60))
    ids = [_series(db, user, f"S{i}", x + np.cumsum(rng.normal(scale=0.3, size=60))).id for i in range(3)]
    res = causal.transmission(db, user, ids)
    for st in res["steps"]:
        assert st["class"] == "correlation"
        assert st["statistic"]["p_adj_chain"] == pytest.approx(min(1.0, st["statistic"]["p_adj"] * 2))
    assert any("numero di passaggi" in n for n in res["notes"])


# --- Laboratorio economico -------------------------------------------------------------------------


def test_lab_bootstrap_excludes_gaps_and_is_reproducible(client, db, user):
    vals = 100 * np.exp(np.cumsum(np.random.default_rng(2).normal(0.01, 0.05, 60)))
    s = _series(db, user, "Prezzo", vals, start=1950, skip={1990, 1991})
    body = {"series_id": s.id, "years": 5, "n_paths": 500, "block": 3, "seed": 11}
    r1 = client.post("/api/lab/simulations/monte_carlo_bootstrap", json=body).json()["result"]
    r2 = client.post("/api/lab/simulations/monte_carlo_bootstrap", json=body).json()["result"]
    assert r1["results"]["final"] == r2["results"]["final"]
    assert r1["results"]["historical"]["n_returns"] == 57 - 1  # 58 osservazioni, 1 variazione a cavallo del buco esclusa
    assert any("1 variazioni escluse" in x for x in r1["data_used"])
    rep = r1["results"]["reproducibility"]
    assert rep["seed"] == 11 and rep["generator"].startswith("numpy") and rep["data"]["Prezzo"] == foresight.fingerprint(s)


def test_lab_regression_does_not_difference_across_gaps(client, db, user):
    rng = np.random.default_rng(4)
    x = np.cumsum(rng.normal(size=40))
    y = 2 * x + rng.normal(scale=0.1, size=40)
    sx = _series(db, user, "X", x, start=1960, skip={1975, 1976})
    sy = _series(db, user, "Y", y, start=1960, skip={1975, 1976})
    r = client.post("/api/lab/simulations/regression", json={"y_series_id": sy.id, "x_series_ids": [sx.id], "transform": "diff"}).json()["result"]
    assert r["results"]["n"] == 39 - 2 - 1  # 38 osservazioni → 37 differenze, meno quella a cavallo del buco
    assert any("2 periodi senza dati" in x for x in r["data_used"])
    assert r["results"]["coefficients"][1]["coef"] == pytest.approx(2, abs=0.1)


def test_debt_uncertainty_declares_independent_shocks_and_clipping(client):
    body = {"d0": 130, "r_eff0": 0.03, "r_market": 0.04, "g": 0.02, "pb": 0.0, "years": 10,
            "stochastic": {"n_paths": 500, "sd_r": 0.01, "sd_g": 0.3, "corr": 0.2}, "seed": 1}
    r = client.post("/api/lab/simulations/debt", json=body).json()["result"]
    assert any("indipendenti da un anno all'altro" in h for h in r["hypotheses"])
    assert r["results"]["clipped_growth_draws"] > 0 and any("−99%" in w for w in r["warnings"])
    assert r["results"]["reproducibility"]["seed"] == 1
