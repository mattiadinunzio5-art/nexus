"""Discovery: correlazione ≠ associazione temporale ≠ ipotesi ≠ causalità; controlli statistici; decisioni dell'utente."""

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from nexus.discovery import connections as cx
from nexus.discovery import hypotheses as hy
from nexus.discovery import stats_checks as sc
from nexus.models import DiscoveryConnection, DiscoveryHypothesis, User

from .test_discovery import _archive, _series


@pytest.fixture
def user(db):
    return db.scalar(select(User))


def _idx(n, start=1950):
    return pd.date_range(f"{start}-01-01", periods=n, freq="YS")


def test_benjamini_hochberg_matches_reference():
    # Esempio di riferimento: q = min_{k>=i} p_(k) * m / k
    assert sc.benjamini_hochberg([0.01, 0.04, 0.03, 0.5]) == pytest.approx([0.04, 0.05333, 0.05333, 0.5], rel=1e-3)
    assert sc.benjamini_hochberg([]) == []


def test_common_trend_is_flagged_as_spurious():
    rng = np.random.default_rng(1)
    a = pd.Series(np.arange(60) * 2 + rng.normal(0, 1, 60), _idx(60))
    b = pd.Series(np.arange(60) * 3 + rng.normal(0, 1, 60), _idx(60))
    rob = sc.robustness(a, "A", b, "A")
    assert rob["levels_r"] > 0.99 and abs(rob["diff_r"]) < 0.3 and rob["spurious_trend"]
    outcome, text = sc.verdict(rob)
    assert outcome == "contradicts" and "trend comune" in text


def test_autocorrelation_reduces_effective_sample():
    rng = np.random.default_rng(5)
    n = 80
    e1, e2 = rng.normal(size=n), rng.normal(size=n)
    # variazioni fortemente autocorrelate (AR(1) con φ=0.8) e lievemente legate tra loro
    x, y = np.zeros(n), np.zeros(n)
    for t in range(1, n):
        x[t] = 0.8 * x[t - 1] + e1[t]
        y[t] = 0.8 * y[t - 1] + 0.3 * e1[t] + e2[t]
    rob = sc.robustness(pd.Series(np.cumsum(x), _idx(n)), "A", pd.Series(np.cumsum(y), _idx(n)), "A")
    assert rob["autocorr_a"] > 0.5 and rob["autocorr_b"] > 0.5
    assert rob["n_eff"] < rob["n"] * 0.6 and rob["p_eff"] > rob["p"]


def test_confounder_detected_by_partial_correlation():
    rng = np.random.default_rng(2)
    z = pd.Series(np.cumsum(rng.normal(0, 1, 60)), _idx(60))
    a = z * 2 + rng.normal(0, 0.2, 60)
    b = z * -1 + rng.normal(0, 0.2, 60)
    rob = sc.robustness(a, "A", b, "A", controls=[("Ciclo economico", z, "A")])
    assert abs(rob["diff_r"]) > 0.8 and abs(rob["confounders"][0]["partial_r"]) < 0.2
    outcome, text = sc.verdict(rob)
    assert outcome == "contradicts" and "Ciclo economico" in text and "confondente" in text


def test_series_connections_corrected_for_multiple_pairs(db, user):
    rng = np.random.default_rng(3)
    x = np.cumsum(rng.normal(size=48))
    linked = [_series(db, user, "Tassi", x), _series(db, user, "Dollaro", np.concatenate([[0], x[:-1]]) + rng.normal(scale=0.2, size=48))]
    noise = [_series(db, user, f"Rumore {i}", np.cumsum(rng.normal(size=48))) for i in range(8)]
    cands = cx.series_connections(db, linked + noise)
    titles = {c.title for c in cands}
    assert "Tassi ↔ Dollaro" in titles
    sig = next(e["detail"] for c in cands if c.title == "Tassi ↔ Dollaro" for e in c.evidence if e["label"] == "Significatività")
    assert "45 coppie" in sig and "Benjamini–Hochberg" in sig


def test_evidence_levels_are_distinct():
    assert hy.evidence_level("statistical_association", "to_verify", [])["level"] == "correlation"
    assert hy.evidence_level("event_data_change", "verifying", [])["level"] == "temporal_association"
    assert hy.evidence_level(None, "to_verify", [])["level"] == "hypothesis"
    # Confermata senza relazione causale documentata: resta un'ipotesi confermata, non causalità.
    docs = [{"checks": [{"check": "Passaggi nei documenti", "outcome": "supports"}, {"check": "Fonti indipendenti", "outcome": "supports"}]}]
    assert hy.evidence_level("statistical_association", "confirmed", docs)["level"] == "hypothesis"
    kg = [{"checks": [{"check": "Knowledge Graph", "outcome": "supports", "causal": True}, {"check": "Fonti indipendenti", "outcome": "supports"}]}]
    assert hy.evidence_level("statistical_association", "confirmed", kg)["level"] == "causal"


def test_correlation_alone_never_confirmed(client, db, user):
    _archive(db, user)
    client.post("/api/discovery/sessions", json={"mode": "guided", "query": "Bretton Woods dollaro tassi"})
    stat = next(h for h in client.get("/api/discovery/hypotheses").json() if "variazioni" in h["title"])
    assert stat["evidence_level"]["level"] == "correlation" and not stat["can_confirm"]
    v = client.post(f"/api/discovery/hypotheses/{stat['id']}/verify").json()
    checks = {c["check"]: c for c in v["verification"][-1]["checks"]}
    assert "Robustezza statistica" in checks
    rob = checks["Robustezza statistica"]
    assert "autocorrelazione" in rob["detail"] and "senza trend" in rob["detail"] and "statistics" in rob
    # La sola statistica (anche se stabile e robusta) non basta: il server rifiuta la conferma.
    statistical_only = [c for c in v["verification"][-1]["checks"] if c["check"] not in hy.DOCUMENTARY or c["outcome"] != "supports"]
    if len(statistical_only) == len(v["verification"][-1]["checks"]):
        r = client.post(f"/api/discovery/hypotheses/{stat['id']}/decision", json={"status": "confirmed", "note": "Mi sembra convincente"})
        assert r.status_code == 422 and "correlazione da sola non basta" in r.json()["error"]["message"]
    # Simulazione: l'ultima verifica ha solo controlli statistici a favore.
    h = db.get(DiscoveryHypothesis, stat["id"])
    h.verification = [*h.verification, {"at": "x", "checks": [{"check": "Stabilità nei sottoperiodi", "outcome": "supports"},
                                                              {"check": "Robustezza statistica", "outcome": "supports"}], "suggested": "inconclusive"}]
    db.commit()
    assert hy.suggested_outcome(h.verification[-1]["checks"]) == "inconclusive"
    r = client.post(f"/api/discovery/hypotheses/{stat['id']}/decision", json={"status": "confirmed", "note": "Statistica solida"})
    assert r.status_code == 422
    # Con un riscontro documentario la conferma è possibile, ma resta un'ipotesi (non causalità documentata).
    h.verification = [*h.verification, {"at": "y", "checks": [{"check": "Robustezza statistica", "outcome": "supports"},
                                                              {"check": "Fonti indipendenti", "outcome": "supports"}], "suggested": "confirmed"}]
    db.commit()
    d = client.post(f"/api/discovery/hypotheses/{stat['id']}/decision", json={"status": "confirmed", "note": "Due fonti indipendenti"}).json()
    assert d["status"] == "confirmed" and d["evidence_level"]["level"] == "hypothesis"


def test_user_can_edit_reject_and_reapprove_hypothesis(client, db, user):
    _archive(db, user)
    client.post("/api/discovery/sessions", json={"mode": "guided", "query": "Bretton Woods dollaro tassi"})
    h = client.get("/api/discovery/hypotheses").json()[0]
    client.post(f"/api/discovery/hypotheses/{h['id']}/verify")
    rej = client.post(f"/api/discovery/hypotheses/{h['id']}/decision", json={"status": "rejected", "note": "Le fonti la contraddicono"}).json()
    assert rej["status"] == "rejected"
    e = client.patch(f"/api/discovery/hypotheses/{h['id']}", json={"title": "Riformulazione più prudente dell'ipotesi",
                                                                     "missing": ["Serie di controllo di un altro paese"]})
    assert e.status_code == 200, e.text
    e = e.json()
    assert e["title"] == "Riformulazione più prudente dell'ipotesi" and e["missing"] == ["Serie di controllo di un altro paese"]
    assert e["status"] == "to_verify" and e["decided_at"] is None  # la modifica annulla l'esito
    assert e["verification"][-1]["edited"] == ["title", "missing"]
    # Nessuna modifica effettiva: nessun cambiamento.
    same = client.patch(f"/api/discovery/hypotheses/{h['id']}", json={"title": "Riformulazione più prudente dell'ipotesi"}).json()
    assert len(same["verification"]) == len(e["verification"])
    assert client.patch(f"/api/discovery/hypotheses/{h['id']}", json={"title": "x"}).status_code == 422
