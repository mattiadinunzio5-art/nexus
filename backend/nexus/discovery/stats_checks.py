"""Controlli statistici per le associazioni tra serie.

Una correlazione tra due serie storiche può essere spuria per tre motivi classici:

1. **trend comune**: due serie che crescono nel tempo risultano correlate anche se indipendenti.
   Controllo: correlazione dei livelli dopo aver rimosso un trend lineare, e correlazione delle
   differenze prime (le variazioni);
2. **autocorrelazione**: osservazioni consecutive non sono indipendenti, quindi il p-value classico
   sovrastima la significatività. Controllo: dimensione campionaria effettiva di Bartlett
   n_eff = n · (1 − ρa·ρb) / (1 + ρa·ρb), con ρ l'autocorrelazione al primo ritardo delle variazioni;
3. **variabili confondenti**: un terzo fattore muove entrambe le serie. Controllo: correlazione
   parziale delle variazioni tenendo fisse, una alla volta, le altre serie dell'archivio che coprono
   lo stesso periodo.

Per i confronti multipli (molte coppie provate nella stessa analisi) si usa la correzione di
Benjamini–Hochberg (tasso di falsi positivi, FDR).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from ..finance import analytics


def benjamini_hochberg(pvalues: list[float]) -> list[float]:
    """q-value (FDR) per ogni p-value, nello stesso ordine."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvalues[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, pvalues[i] * m / rank)
        q[i] = min(1.0, prev)
    return q


def _common(a: pd.Series, fa: str, b: pd.Series, fb: str) -> tuple[pd.Series, pd.Series, str]:
    target = fa if analytics.FREQ_ORDER[fa] >= analytics.FREQ_ORDER[fb] else fb
    ra = analytics.resample(a, fa, target, "mean")
    rb = analytics.resample(b, fb, target, "mean")
    x, y = ra.align(rb, join="inner")
    mask = x.notna() & y.notna()
    return x[mask], y[mask], target


def _detrend(s: pd.Series) -> np.ndarray:
    t = np.arange(len(s), dtype=float)
    v = s.to_numpy(dtype=float)
    slope, intercept = np.polyfit(t, v, 1)
    return v - (slope * t + intercept)


def autocorr1(v: np.ndarray) -> float:
    if len(v) < 3 or np.std(v[:-1]) == 0 or np.std(v[1:]) == 0:
        return 0.0
    return float(np.corrcoef(v[:-1], v[1:])[0, 1])


def p_from_r(r: float, n_eff: float) -> float:
    """p-value bilaterale di una correlazione con n_eff osservazioni effettive."""
    if n_eff <= 3 or abs(r) >= 1:
        return 0.0 if abs(r) >= 1 else 1.0
    t = r * math.sqrt((n_eff - 2) / (1 - r * r))
    return float(2 * stats.t.sf(abs(t), n_eff - 2))


def partial_corr(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:
    """Correlazione tra x e y al netto di z (residui delle regressioni lineari su z)."""
    Z = np.column_stack([np.ones(len(z)), z])
    rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    if np.std(rx) == 0 or np.std(ry) == 0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def robustness(a: pd.Series, fa: str, b: pd.Series, fb: str, lag: int = 0,
               controls: list[tuple[str, pd.Series, str]] | None = None, min_obs: int = 12) -> dict | None:
    """Controlli di robustezza di un'associazione tra due serie (al ritardo indicato)."""
    x, y, freq = _common(a, fa, b, fb)
    if lag:
        y = y.shift(-lag)
        mask = y.notna()
        x, y = x[mask], y[mask]
    if len(x) < min_obs:
        return None
    levels_r = float(np.corrcoef(x, y)[0, 1]) if np.std(x) and np.std(y) else 0.0
    det_r = float(np.corrcoef(_detrend(x), _detrend(y))[0, 1]) if len(x) >= 3 else 0.0
    dx, dy = np.diff(x.to_numpy(dtype=float)), np.diff(y.to_numpy(dtype=float))
    if np.std(dx) == 0 or np.std(dy) == 0:
        return None
    diff_r = float(np.corrcoef(dx, dy)[0, 1])
    n = len(dx)
    ra, rb = autocorr1(dx), autocorr1(dy)
    n_eff = max(3.0, n * (1 - ra * rb) / (1 + ra * rb)) if ra * rb > -1 else float(n)
    p_naive = p_from_r(diff_r, n)
    p_eff = p_from_r(diff_r, n_eff)
    out = {"freq": freq, "n": n, "lag": lag, "levels_r": round(levels_r, 3), "detrended_r": round(det_r, 3), "diff_r": round(diff_r, 3),
           "autocorr_a": round(ra, 3), "autocorr_b": round(rb, 3), "n_eff": round(n_eff, 1), "p": p_naive, "p_eff": p_eff,
           "spurious_trend": abs(levels_r) >= 0.7 and abs(diff_r) < 0.3, "confounders": []}
    idx = x.index[1:]
    for name, s, f in controls or []:
        try:
            if analytics.FREQ_ORDER[f] > analytics.FREQ_ORDER[freq]:
                continue  # non si ricampiona verso una frequenza più alta
            zs = analytics.resample(s, f, freq, "mean").diff()
        except analytics.AnalysisError:
            continue
        zs = zs.reindex(idx)
        mask = zs.notna().to_numpy()
        if mask.sum() < min_obs:
            continue
        pr = partial_corr(dx[mask], dy[mask], zs.to_numpy(dtype=float)[mask])
        out["confounders"].append({"name": name, "partial_r": round(pr, 3), "n": int(mask.sum())})
    out["confounders"].sort(key=lambda c: abs(c["partial_r"]))
    return out


def verdict(rob: dict) -> tuple[str, str]:
    """(outcome, testo) del controllo di robustezza: supports | weak | contradicts."""
    parts = [f"variazioni: r = {rob['diff_r']:+.2f} (n = {rob['n']}, frequenza {rob['freq']}, ritardo {rob['lag']})",
             f"livelli: r = {rob['levels_r']:+.2f}; livelli senza trend: r = {rob['detrended_r']:+.2f}",
             f"autocorrelazione delle variazioni: {rob['autocorr_a']:+.2f} e {rob['autocorr_b']:+.2f}, osservazioni effettive ≈ {rob['n_eff']:.0f}, "
             f"p = {rob['p']:.2g} → p corretto per autocorrelazione = {rob['p_eff']:.2g}"]
    outcome = "supports"
    if rob["spurious_trend"]:
        parts.append("la correlazione dei livelli scompare sulle variazioni: probabile trend comune (correlazione spuria)")
        outcome = "contradicts"
    elif rob["p_eff"] > 0.05:
        parts.append("non significativa una volta considerata l'autocorrelazione")
        outcome = "weak"
    if rob["confounders"]:
        worst = rob["confounders"][0]
        parts.append(f"al netto di «{worst['name']}»: r parziale = {worst['partial_r']:+.2f}")
        if abs(worst["partial_r"]) < 0.2 or (worst["partial_r"] > 0) != (rob["diff_r"] > 0):
            parts.append("l'associazione si annulla controllando questa variabile: possibile confondente")
            outcome = "contradicts" if outcome != "contradicts" else outcome
    else:
        parts.append("nessuna altra serie dell'archivio disponibile come controllo per i confondenti")
    return outcome, "; ".join(parts) + "."
