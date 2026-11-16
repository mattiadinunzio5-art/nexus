"""Motore Monte Carlo a blocchi, con memoria limitata.

Le traiettorie si generano a blocchi di poche migliaia: di ciascun blocco si conservano solo
i valori sui punti della griglia del grafico (al massimo ``fan_points``) e il valore finale.
La matrice completa traiettorie × passi non esiste mai in memoria: la memoria cresce con
``n_paths × fan_points``, non con ``n_paths × passi``. I percentili sui punti della griglia
sono esatti (calcolati su tutte le traiettorie), non approssimati.

I limiti (traiettorie, orizzonte, celle calcolate) sono configurabili da ``Settings``
(variabili d'ambiente NEXUS_LAB_*).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


class LimitError(ValueError):
    pass


@dataclass(frozen=True)
class Limits:
    max_paths: int = 20_000
    max_years: int = 100
    # celle calcolate in tutto (traiettorie × passi): limita il tempo di calcolo
    max_cells: int = 50_000_000
    # celle per blocco (traiettorie del blocco × passi): limita la memoria di picco (~8 byte a cella, ×3 array temporanei)
    block_cells: int = 1_000_000
    fan_points: int = 121

    @classmethod
    def from_settings(cls, s) -> "Limits":
        return cls(max_paths=s.lab_max_paths, max_years=s.lab_max_years, max_cells=s.lab_max_cells,
                   block_cells=s.lab_block_cells, fan_points=s.lab_fan_points)

    def check(self, n_paths: int, steps: int, years: float) -> None:
        if n_paths > self.max_paths:
            raise LimitError(f"Troppe traiettorie: {n_paths} (massimo {self.max_paths}).")
        if years > self.max_years:
            raise LimitError(f"Orizzonte troppo lungo: {years:g} anni (massimo {self.max_years}).")
        if n_paths * steps > self.max_cells:
            def fmt(x: int) -> str:
                return f"{x:,}".replace(",", ".")

            raise LimitError(f"Calcolo troppo grande: {n_paths} traiettorie × {steps} passi = {fmt(n_paths * steps)} valori "
                             f"(massimo {fmt(self.max_cells)}). Riduci traiettorie, passi per anno o orizzonte.")

    def block_size(self, steps: int) -> int:
        return max(1, self.block_cells // max(1, steps))


DEFAULT = Limits()


def grid(steps: int, points: int) -> np.ndarray:
    """Indici dei passi conservati per il grafico (sempre inclusi l'inizio e la fine)."""
    if steps + 1 <= points:
        return np.arange(steps + 1)
    return np.unique(np.linspace(0, steps, points).round().astype(int))


class Collector:
    """Raccoglie, blocco per blocco, i valori sulla griglia, i finali e qualche traiettoria d'esempio."""

    def __init__(self, n_paths: int, idx: np.ndarray, samples: int = 10):
        self.idx = idx
        self.on_grid = np.empty((n_paths, len(idx)))
        self.final = np.empty(n_paths)
        self.samples: list[np.ndarray] = []
        self.n_samples = samples
        self.pos = 0
        self.blocks = 0

    def add(self, levels_on_grid: np.ndarray, final: np.ndarray) -> None:
        b = len(final)
        self.on_grid[self.pos:self.pos + b] = levels_on_grid
        self.final[self.pos:self.pos + b] = final
        if len(self.samples) < self.n_samples:
            self.samples.extend(levels_on_grid[: self.n_samples - len(self.samples)])
        self.pos += b
        self.blocks += 1


def gbm(s0: float, mu: float, sigma: float, steps: int, dt: float, n_paths: int, rng: np.random.Generator, lim: Limits) -> Collector:
    idx = grid(steps, lim.fan_points)
    col = Collector(n_paths, idx)
    drift, vol = (mu - 0.5 * sigma**2) * dt, sigma * math.sqrt(dt)
    bs = lim.block_size(steps)
    for start in range(0, n_paths, bs):
        b = min(bs, n_paths - start)
        log_lvl = np.empty((b, steps + 1))
        log_lvl[:, 0] = 0.0
        np.cumsum(drift + vol * rng.standard_normal((b, steps)), axis=1, out=log_lvl[:, 1:])
        lvl_grid = s0 * np.exp(log_lvl[:, idx])
        col.add(lvl_grid, s0 * np.exp(log_lvl[:, -1]))
        del log_lvl
    return col


def bootstrap(s0: float, rets: np.ndarray, steps: int, block: int, n_paths: int, rng: np.random.Generator, lim: Limits) -> Collector:
    idx = grid(steps, lim.fan_points)
    col = Collector(n_paths, idx)
    k = math.ceil(steps / block)
    offs = np.arange(block)
    bs = lim.block_size(k * block)
    for start in range(0, n_paths, bs):
        b = min(bs, n_paths - start)
        starts = rng.integers(0, len(rets) - block + 1, size=(b, k))
        draws = rets[(starts[:, :, None] + offs).reshape(b, k * block)[:, :steps]]
        log_lvl = np.empty((b, steps + 1))
        log_lvl[:, 0] = 0.0
        np.cumsum(draws, axis=1, out=log_lvl[:, 1:])
        col.add(s0 * np.exp(log_lvl[:, idx]), s0 * np.exp(log_lvl[:, -1]))
    return col


def debt_paths(d0: float, eff: np.ndarray, g: float, pb: float, cov: list[list[float]], n_paths: int,
               rng: np.random.Generator, lim: Limits) -> Collector:
    years = len(eff)
    idx = grid(years, lim.fan_points)
    col = Collector(n_paths, idx)
    bs = lim.block_size(years * 2)
    for start in range(0, n_paths, bs):
        b = min(bs, n_paths - start)
        shocks = rng.multivariate_normal([0, 0], cov, size=(b, years))
        r = eff[None, :] + shocks[:, :, 0]
        gg = g + shocks[:, :, 1]
        if (gg <= -0.99).any():
            col.clipped = getattr(col, "clipped", 0) + int((gg < -0.99).sum())
            gg = np.maximum(gg, -0.99)
        path = np.empty((b, years + 1))
        path[:, 0] = d0
        for t in range(years):
            path[:, t + 1] = path[:, t] * (1 + r[:, t]) / (1 + gg[:, t]) - pb
        col.add(path[:, idx], path[:, -1])
    return col


def fan(col: Collector, times: list, percentiles=(5, 25, 50, 75, 95)) -> list[dict]:
    pct = np.percentile(col.on_grid, percentiles, axis=0)
    out = []
    for j, i in enumerate(col.idx):
        row = {"t": times[i]}
        for k, p in enumerate(percentiles):
            v = float(pct[k, j])
            row[f"p{p}"] = None if math.isnan(v) or math.isinf(v) else round(v, 6)
        out.append(row)
    return out
