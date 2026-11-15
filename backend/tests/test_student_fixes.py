"""Correzioni emerse dal test di uno studente (ricerca sulla plastica 1950–2025)."""

import pandas as pd
import pytest

from nexus.finance import analytics
from nexus.research.citations import _norm as _same_title


def test_project_research_design_roundtrip(client):
    r = client.post("/api/projects", json={"title": "Plastica", "research_question": "Come è cresciuta?", "objectives": "a\nb",
                                           "scope": "mondo", "period_start": 1950, "period_end": 2025})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["research_question"] == "Come è cresciuta?" and p["period_start"] == 1950 and p["period_end"] == 2025
    u = client.patch(f"/api/projects/{p['id']}", json={"period_end": None}).json()
    assert u["period_end"] is None and u["period_start"] == 1950
    bad = client.patch(f"/api/projects/{p['id']}", json={"period_end": 1900})
    assert bad.status_code == 422


def test_crossref_title_ignores_typographic_quotes():
    assert _same_title("Plastics’ fate — a review.") == _same_title("plastics' fate - a review")
    assert _same_title("Plastics") != _same_title("Plastic waste")


def test_anomalies_on_exponential_series_use_percent_changes():
    # Crescita costante del 5% l'anno per 75 anni: in variazioni assolute gli ultimi anni sembrerebbero anomali.
    idx = pd.date_range("1950-01-01", periods=75, freq="YS")
    import numpy as np

    noise = np.random.default_rng(1).normal(0, 0.01, 75)
    s = pd.Series([2 * 1.05 ** i * (1 + noise[i]) for i in range(75)], index=idx)
    assert analytics.scale_free(s)
    assert analytics.anomalies(s, z=4.0) == []
    shock = s.copy()
    shock.iloc[40:] *= 0.6  # crollo del 40% in un anno
    found = analytics.anomalies(shock, z=4.0)
    assert [a["date"][:4] for a in found] == ["1990"]


def test_lab_scenarios_and_rename(client):
    csv = "anno,v\n" + "\n".join(f"{y},{100 * 1.04 ** (y - 2000):.4f}" for y in range(2000, 2021))
    sid = client.post("/api/finance/series/upload", files={"file": ("p.csv", csv.encode())},
                      data={"name": "Produzione", "source_label": "Test", "unit": "Mt"}).json()["id"]
    r = client.post("/api/lab/simulations/scenarios", json={
        "series_id": sid, "horizon": 10, "uncertainty": 0.02, "title": "Plastica al 2030",
        "scenarios": [{"name": "Base", "growth": 0.03}, {"name": "Riduzione", "growth": -0.02}]})
    assert r.status_code == 201, r.text
    sim = r.json()
    assert sim["title"] == "Plastica al 2030"
    res = sim["result"]["results"]
    assert res["years"][0] == 2020 and res["years"][-1] == 2030
    assert res["history"]["cagr"] == pytest.approx(0.04, abs=1e-4)
    base = res["paths"]["Base"]
    assert base["value"][-1] == pytest.approx(base["value"][0] * 1.03 ** 10, rel=1e-6)
    assert base["low"][-1] < base["value"][-1] < base["high"][-1]
    ren = client.patch(f"/api/lab/simulations/{sim['id']}", json={"title": "Nuovo titolo"})
    assert ren.status_code == 200 and ren.json()["title"] == "Nuovo titolo"
    dup = client.post("/api/lab/simulations/scenarios", json={"base_value": 10, "base_year": 2020,
                                                              "scenarios": [{"name": "A", "growth": 0.1}, {"name": "A", "growth": 0.2}]})
    assert dup.status_code == 422
    noseries = client.post("/api/lab/simulations/scenarios", json={"scenarios": [{"name": "A", "growth": 0.1}]})
    assert noseries.status_code == 422


def test_unhandled_error_returns_json_with_cors(settings):
    from fastapi.testclient import TestClient

    from nexus.main import create_app

    app = create_app(settings)

    @app.get("/api/_boom")
    def boom():
        raise RuntimeError("x")

    origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:5173"
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/_boom", headers={"Origin": origin})
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    if settings.cors_origins:
        assert r.headers.get("access-control-allow-origin") == origin


def test_interrupted_warroom_runs_are_marked_failed(client):
    from datetime import timedelta

    from nexus.database.base import utcnow
    from nexus.models import ResearchRun
    from nexus.services import warroom

    db = client.app.state.database.session_factory()
    try:
        from nexus.models import User

        u = db.query(User).first()
        run = ResearchRun(owner_id=u.id, question="q", status="running", mode="local")
        db.add(run)
        db.commit()
        db.commit()
        assert warroom.fail_interrupted_runs(db) >= 1
        db.refresh(run)
        assert run.status == "queued"  # torna in coda e riprende dall'ultima fase completata
    finally:
        db.close()


def test_search_matches_word_starts(client):
    from nexus.services.search import _word_match

    ok = _word_match("oil")
    assert ok("Oil crisis") and ok("vegetable oils") and not ok("turmoil") and not ok("soil erosion")


def test_italian_query_finds_english_content(client):
    from nexus.research.crosslang import text_matcher, variants

    assert "oil crisis 1973" in variants("crisi petrolifera 1973")
    assert "piano marshall" in variants("Marshall Plan")
    ok = text_matcher("produzione di plastica")
    assert ok("Global plastic production, 1950–2015") and not ok("Steel production")

    csv = "anno,v\n" + "\n".join(f"{y},{y - 1949}" for y in range(1950, 1965))
    client.post("/api/finance/series/upload", files={"file": ("p.csv", csv.encode())},
                data={"name": "Global plastic production", "source_label": "Test", "unit": "Mt"})
    names = [s["name"] for s in client.get("/api/finance/series", params={"q": "produzione di plastica"}).json()]
    assert "Global plastic production" in names
    src = client.post("/api/sources", json={"source_type": "article", "title": "Production, use, and fate of all plastics ever made",
                                              "authors": ["Geyer, Roland"], "year": 2017})
    assert src.status_code in (200, 201), src.text
    found = [s["title"] for s in client.get("/api/sources", params={"q": "plastiche"}).json()]
    assert any("plastics ever made" in t for t in found)
    hits = client.get("/api/search", params={"q": "produzione di plastica"}).json()["hits"]
    assert any(h["type"] == "series" and h["title"] == "Global plastic production" for h in hits)


def test_archive_text_search_is_bilingual(client):
    up = client.post("/api/documents", files={"file": ("plastics.txt", b"Plastic waste reached the oceans in large quantities after 1980.\n" * 3)},
                     data={"title": "Ocean plastics", "category": "source_material"})
    assert up.status_code == 201, up.text
    r = client.get("/api/research/search", params={"q": "rifiuti di plastica", "mode": "text"}).json()
    assert r["hits"] and "Plastic waste" in r["hits"][0]["text"]
