"""Economic Laboratory: memoria del Monte Carlo, limiti configurabili, modelli settoriali, frequenze e tre scenari."""

import math
import tracemalloc

import numpy as np
import pytest

from nexus.simulations import engine
from nexus.simulations import models as M
from nexus.simulations import sectors


def test_gbm_memory_does_not_grow_with_steps():
    """20.000 traiettorie × 2.268 passi: la matrice completa occuperebbe ~360 MB; a blocchi si resta molto sotto."""
    tracemalloc.start()
    r = M.monte_carlo_gbm(100, 0.05, 0.2, 9, 252, 20000, 1)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    full_matrix = 20000 * (9 * 252 + 1) * 8
    assert peak < full_matrix / 6, f"picco {peak / 1e6:.0f} MB"
    comp = r.results["computation"]
    assert comp["computed_values"] == 20000 * 2268 and comp["stored_values"] <= 20000 * 121 and comp["blocks"] > 1
    assert len(r.results["fan"]) <= 121 and r.results["fan"][-1]["t"] == 9.0
    # Media analitica e^{μT}: il risultato a blocchi resta corretto.
    assert r.results["final"]["mean"] == pytest.approx(100 * math.exp(0.45), rel=0.02)


def test_block_results_equal_full_matrix_percentiles():
    """Stessa estrazione casuale: percentili identici calcolando tutto insieme o a blocchi."""
    rng_full = np.random.default_rng(7)
    steps, n = 50, 3000
    z = rng_full.standard_normal((n, steps))
    lvl = 100 * np.exp(np.concatenate([np.zeros((n, 1)), np.cumsum((0.05 - 0.02) / 10 + 0.2 * math.sqrt(0.1) * z, axis=1)], axis=1))
    small = engine.Limits(block_cells=steps * 7)  # blocchi da 7 traiettorie
    col = engine.gbm(100, 0.05, 0.2, steps, 0.1, n, np.random.default_rng(7), small)
    assert col.blocks == math.ceil(n / 7)
    assert np.allclose(np.percentile(col.final, [5, 50, 95]), np.percentile(lvl[:, -1], [5, 50, 95]))


def test_limits_are_configurable_and_enforced(client):
    client.app.state.settings.lab_max_cells = 1_000_000
    r = client.post("/api/lab/simulations/monte_carlo", json={"s0": 100, "mu": 0.05, "sigma": 0.2, "years": 10, "steps_per_year": 252, "n_paths": 1000})
    assert r.status_code == 422 and "Calcolo troppo grande" in r.json()["error"]["message"]
    client.app.state.settings.lab_max_paths = 500
    r = client.post("/api/lab/simulations/monte_carlo", json={"s0": 100, "mu": 0.05, "sigma": 0.2, "years": 1, "n_paths": 600})
    assert r.status_code == 422 and "Troppe traiettorie" in r.json()["error"]["message"]
    assert client.post("/api/lab/simulations/monte_carlo", json={"s0": 100, "mu": 0.05, "sigma": 0.2, "years": 1, "n_paths": 400}).status_code == 201
    assert client.get("/api/lab/limits").json()["max_paths"] == 500
    with pytest.raises(M.SimulationError, match="Orizzonte troppo lungo"):
        M.debt_dynamics(100, 0.03, 0.03, 7, 0.03, 0, 60, stochastic={"n_paths": 100}, limits=engine.Limits(max_years=50))


def test_debt_stochastic_blocks():
    r = M.debt_dynamics(140, 0.03, 0.035, 7, 0.03, 1.0, 30, stochastic={"n_paths": 5000, "sd_r": 0.01, "sd_g": 0.02, "corr": -0.3}, seed=3,
                        limits=engine.Limits(block_cells=600))
    assert r.results["computation"]["blocks"] == math.ceil(5000 / 10)
    fan = r.results["fan"]
    assert len(fan) == 31 and fan[0]["p50"] == 140 and fan[-1]["p5"] < fan[-1]["p50"] < fan[-1]["p95"]


def test_employment_okun_formula():
    base = {"labour_force0": 100.0, "u0": 0.08, "years": 3, "gdp_growth": 0.03, "potential_growth": 0.01, "okun_beta": 0.5, "labour_force_growth": 0.0}
    r = sectors.run_sector("employment", base, {"optimistic": {"gdp_growth": 0.04}, "pessimistic": {"gdp_growth": -0.01}})
    u = r.results["scenarios"]["Base"]["Tasso di disoccupazione"]
    assert u == pytest.approx([0.08, 0.07, 0.06, 0.05])  # −0,5·(3%−1%) all'anno
    assert r.results["scenarios"]["Base"]["Occupati"][-1] == pytest.approx(95.0)
    comp = {c["key"]: c for c in r.results["comparison"]}
    assert comp["optimistic"]["delta_vs_base"] > 0 > comp["pessimistic"]["delta_vs_base"]
    assert "Okun" in r.method and r.limitations and r.hypotheses


def test_industrial_production_capacity_bound():
    base = {"ip0": 100.0, "years": 5, "trend_growth": 0.01, "demand_growth": 0.04, "demand_elasticity": 1.0, "energy_price_change": 0.0,
            "energy_elasticity": 0.1, "capacity_ratio": 1.1, "capacity_growth": 0.01}
    r = sectors.run_sector("industrial_production", base, {"pessimistic": {"energy_price_change": 0.5}})
    ip = r.results["scenarios"]["Base"]["Produzione industriale (indice)"]
    cap = r.results["scenarios"]["Base"]["Capacità produttiva"]
    assert all(a <= b + 1e-9 for a, b in zip(ip, cap)) and any("capacità" in w for w in r.warnings)
    assert r.results["diagnostics"]["Pessimistico"]["implied_growth"] == pytest.approx(0.05 - 0.1 * 0.5)
    assert any("ottimistico" in w for w in r.warnings)  # manca uno scenario: segnalato


def test_trade_marshall_lerner_and_balance():
    base = {"exports0": 30.0, "imports0": 28.0, "gdp0": 100.0, "years": 2, "world_growth": 0.03, "domestic_growth": 0.01,
            "income_elasticity_exports": 1.0, "income_elasticity_imports": 1.5, "price_elasticity_exports": 0.3, "price_elasticity_imports": 0.4,
            "reer_change": 0.0}
    r = sectors.run_sector("trade", base, {"optimistic": {"world_growth": 0.04}, "pessimistic": {"world_growth": 0.0}})
    bal = r.results["scenarios"]["Base"]["Saldo commerciale (quota del PIL)"]
    assert bal[0] == pytest.approx(0.02) and bal[1] == pytest.approx((30 * 1.03 - 28 * 1.015) / 101, rel=1e-4)
    assert any("Marshall" in w for w in r.warnings)


def test_consumption_and_unknown_override():
    base = {"income0": 1000.0, "years": 1, "income_growth": 0.0, "tax_rate": 0.2, "mpc": 0.8, "autonomous": 50.0, "wealth0": 4000.0,
            "wealth_effect": 0.02, "wealth_growth": 0.0}
    r = sectors.run_sector("consumption", base, {"optimistic": {"mpc": 0.85}, "pessimistic": {"mpc": 0.7}})
    assert r.results["scenarios"]["Base"]["Consumi"][0] == pytest.approx(50 + 0.8 * 800 + 0.02 * 4000)
    with pytest.raises(M.SimulationError, match="sconosciuti"):
        sectors.run_sector("consumption", base, {"optimistic": {"inventato": 1}})


def test_sector_api_roundtrip(client):
    body = {"years": 5, "labour_force0": 25.9, "u0": 0.07, "gdp_growth": 0.01, "potential_growth": 0.007, "okun_beta": 0.4,
            "labour_force_growth": 0.0, "optimistic": {"gdp_growth": 0.02}, "pessimistic": {"gdp_growth": -0.01}, "unit": "milioni"}
    r = client.post("/api/lab/simulations/employment", json=body)
    assert r.status_code == 201, r.text
    res = r.json()["result"]
    assert [c["scenario"] for c in res["results"]["comparison"]] == ["Base", "Ottimistico", "Pessimistico"]
    assert "Parametri inseriti dall'utente" in res["data_used"][0]
    missing = {k: v for k, v in body.items() if k != "okun_beta"}
    assert client.post("/api/lab/simulations/employment", json=missing).status_code == 422  # nessun valore predefinito inventato


def _upload(client, name, rows, freq_note=""):
    csv = "data,valore\n" + "\n".join(f"{d},{v}" for d, v in rows)
    return client.post("/api/finance/series/upload", files={"file": ("s.csv", csv.encode())}, data={"name": name, "source_label": "Serie di prova del test"}).json()["id"]


def test_scenarios_monthly_series_need_explicit_aggregation_and_three_scenarios(client):
    rows = [(f"{2010 + i // 12}-{i % 12 + 1:02d}-01", 100 * 1.002 ** i) for i in range(12 * 10 + 5)]  # 10 anni + 5 mesi
    sid = _upload(client, "Indice mensile", rows)
    body = {"series_id": sid, "horizon": 5, "scenarios": [{"name": "x", "growth": 0.02}], "history_years": 5}
    r = client.post("/api/lab/simulations/scenarios", json=body)
    assert r.status_code == 422 and "frequenza M" in r.json()["error"]["message"]
    r = client.post("/api/lab/simulations/scenarios", json={**body, "aggregation": "mean", "three_scenarios": True, "spread": 0.01})
    assert r.status_code == 201, r.text
    res = r.json()["result"]
    used = " ".join(res["data_used"])
    assert "da frequenza M ad annuale" in used and "Anni incompleti esclusi: 2020" in used and "ultimo anno usato 2019" in used
    growth = {s["name"]: s["growth"] for s in res["parameters"]["scenarios"]}
    cagr = 1.002 ** 12 - 1
    assert growth["Base"] == pytest.approx(cagr, abs=1e-4)
    assert growth["Ottimistico"] == pytest.approx(growth["Base"] + 0.01) and growth["Pessimistico"] == pytest.approx(growth["Base"] - 0.01)
    comp = {c["scenario"]: c for c in res["results"]["comparison"]}
    assert comp["Base"]["delta_vs_reference"] == 0 and comp["Ottimistico"]["pct_vs_reference"] > 0 > comp["Pessimistico"]["pct_vs_reference"]
