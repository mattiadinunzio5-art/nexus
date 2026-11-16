"""Economic Laboratory: esecuzione e archiviazione delle simulazioni."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api import schemas_lab as S
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..finance import analytics
from ..models import SimulationRun, User
from ..simulations import models as M
from . import activity, finance


def _save(db: Session, user: User, res: M.SimulationResult, params: dict) -> SimulationRun:
    run = SimulationRun(owner_id=user.id, kind=res.kind, title=res.title[:300], params=params, result=res.to_dict(), counterfactual=res.counterfactual)
    db.add(run)
    db.flush()
    activity.record(db, user=user, actor="user", action="simulation.run", entity_type="simulation", entity_id=run.id,
                    summary=f"Simulazione «{run.title}»" + (" (controfattuale)" if run.counterfactual else ""))
    db.commit()
    db.refresh(run)
    return run


def _guard(fn):
    try:
        return fn()
    except M.SimulationError as exc:
        raise ValidationFailedError(str(exc)) from exc


SECTORS = ("industrial_production", "employment", "trade", "consumption")


def run(db: Session, user: User, kind: str, data, settings=None) -> SimulationRun:
    from ..simulations.engine import DEFAULT, Limits

    lim = Limits.from_settings(settings) if settings is not None else DEFAULT
    params = data.model_dump()
    if kind == "monte_carlo":
        res = _guard(lambda: M.monte_carlo_gbm(data.s0, data.mu, data.sigma, data.years, data.steps_per_year, data.n_paths, data.seed, data.threshold,
                                               limits=lim))
    elif kind in SECTORS:
        from ..simulations import sectors

        res = _guard(lambda: sectors.run_sector(kind, data.base_params(), {"optimistic": data.optimistic, "pessimistic": data.pessimistic}, data.unit))
    elif kind == "monte_carlo_bootstrap":
        s = finance.get_series(db, user, data.series_id)
        obs = [(o.date, o.value) for o in s.observations if o.value is not None]
        res = _guard(lambda: M.monte_carlo_bootstrap(s.name, [d for d, _ in obs], [v for _, v in obs], analytics.PERIODS_PER_YEAR[s.frequency],
                                                     data.years, data.n_paths, data.block, data.seed, limits=lim, freq=s.frequency))
    elif kind == "debt":
        res = _guard(lambda: M.debt_dynamics(**{k: v for k, v in params.items() if k != "title"}, limits=lim))
    elif kind == "sensitivity":
        b = data.base.model_dump()
        base = {k: b[k] for k in ("d0", "r_eff0", "r_market", "avg_maturity", "g", "pb", "years")}
        for k, (lo, hi) in data.ranges.items():
            if lo > hi:
                raise ValidationFailedError(f"Intervallo non valido per {k}: minimo > massimo.")
        res = _guard(lambda: M.sensitivity(base, dict(data.ranges)))
    elif kind == "inflation":
        res = _guard(lambda: M.inflation_scenarios(data.amount, data.nominal_rate, data.years, data.inflation_levels))
    elif kind == "monetary_policy":
        res = _guard(lambda: M.taylor_rules(data.inflation, data.output_gap, data.labels, [r.model_dump() for r in data.rules],
                                            data.r_star, data.pi_target, data.actual_rate))
    elif kind == "regression":
        res = _regression(db, user, data)
    elif kind == "backtest":
        s = finance.get_series(db, user, data.series_id)
        obs = [(o.date, o.value) for o in s.observations if o.value is not None]
        p = {"fast": data.fast, "slow": data.slow} if data.strategy == "ma_cross" else {"lookback": data.lookback} if data.strategy == "momentum" else {}
        res = _guard(lambda: M.backtest(s.name, [d for d, _ in obs], [v for _, v in obs], analytics.PERIODS_PER_YEAR[s.frequency],
                                        data.strategy, p, data.cost_bps, data.rf))
        res.data_used.append(f"Fonte: {s.source_label}")
    elif kind == "scenarios":
        res = _scenarios(db, user, data)
    else:
        raise NotFoundError("Tipo di simulazione sconosciuto.")
    if getattr(data, "title", None) and data.title.strip():
        res.title = data.title.strip()
    res.results["reproducibility"] = _reproducibility(db, user, data, params)
    return _save(db, user, res, params)


def _reproducibility(db: Session, user: User, data, params: dict) -> dict:
    """Ciò che serve per rifare la simulazione e ottenere lo stesso risultato: parametri (salvati con la simulazione),
    seme e generatore casuale, versione di numpy, impronta dei dati delle serie usate."""
    import numpy as np

    from ..discovery.foresight import fingerprint

    ids = [getattr(data, "series_id", None), getattr(data, "y_series_id", None), *(getattr(data, "x_series_ids", None) or [])]
    out: dict = {"numpy": np.__version__}
    if "seed" in params:
        out.update(seed=params["seed"], generator="numpy.random.default_rng (PCG64)")
    series = [finance.get_series(db, user, i) for i in ids if i is not None]
    if series:
        out["data"] = {s.name: fingerprint(s) for s in series}
        out["note"] = "Stessi parametri, stesso seme e stessa impronta dei dati = stesso risultato."
    return out


def _annual(s, aggregation: str | None) -> tuple[list[tuple[int, float]], list[str]]:
    """Valori annuali della serie. Frequenze diverse dall'annuale richiedono un metodo esplicito;
    l'ultimo anno incompleto viene escluso (dichiarato nella procedura)."""
    obs = [(o.date, o.value) for o in s.observations if o.value is not None]
    if s.frequency == "A":
        return [(int(str(d)[:4]), v) for d, v in obs], []
    if aggregation is None:
        raise ValidationFailedError(f"La serie «{s.name}» ha frequenza {s.frequency}: scegli come passare ad anni "
                                    "(media, somma o ultimo valore dell'anno).")
    series = analytics.to_pandas(obs)
    counts = series.groupby(series.index.year).count()
    annual = analytics.resample(series, s.frequency, "A", aggregation)
    need = analytics.PERIODS_PER_YEAR[s.frequency]
    full = [(int(ix.year), float(v)) for ix, v in annual.items() if v == v and counts.get(ix.year, 0) >= (need if s.frequency != "D" else 200)]
    dropped = [int(ix.year) for ix, _ in annual.items() if int(ix.year) not in {y for y, _ in full}]
    note = [f"«{s.name}»: da frequenza {s.frequency} ad annuale con «{ {'mean': 'media', 'sum': 'somma', 'last': 'ultimo valore'}[aggregation] }» dei periodi"]
    if dropped:
        note.append(f"Anni incompleti esclusi: {', '.join(map(str, dropped[-5:]))}")
    return full, note


def _scenarios(db: Session, user: User, data: S.ScenariosIn) -> M.SimulationResult:
    history, used = None, ["Crescite degli scenari scelte dall'utente"]
    name, unit = "valore inserito", data.unit
    if data.series_id is not None:
        s = finance.get_series(db, user, data.series_id)
        annual, procedure = _annual(s, data.aggregation)
        obs = [(y, v) for y, v in annual if v > 0]
        if len(obs) < 2:
            raise ValidationFailedError("La serie non ha abbastanza valori annuali positivi per una proiezione.")
        y_last, last_v = obs[-1]
        name, unit = s.name, data.unit or s.unit
        base_value = data.base_value or last_v
        base_year = data.base_year or y_last
        past = [(y, v) for y, v in obs if y <= y_last - data.history_years]
        if past:
            y0, v0 = past[-1]
            span = y_last - y0
            if span > 0:
                history = {"from": y0, "to": y_last, "cagr": round((last_v / v0) ** (1 / span) - 1, 6),
                           "years": [y for y, _ in obs if y >= y_last - 3 * data.history_years],
                           "values": [round(v, 4) for y, v in obs if y >= y_last - 3 * data.history_years]}
        used.insert(0, f"Serie «{s.name}» — {s.source_label} (ultimo anno usato {y_last}: {last_v:.4g} {s.unit})")
        used[1:1] = procedure
    else:
        if data.base_value is None or data.base_year is None:
            raise ValidationFailedError("Indica una serie oppure valore e anno di partenza.")
        base_value, base_year = data.base_value, data.base_year
        used.insert(0, "Valore di partenza inserito dall'utente")
    scenarios = [x.model_dump() for x in data.scenarios]
    if data.three_scenarios:
        g = history["cagr"] if history else scenarios[0]["growth"]
        origin = (f"crescita media storica {history['from']}–{history['to']}" if history else f"crescita dello scenario «{scenarios[0]['name']}»")
        scenarios = [{"name": "Base", "growth": round(g, 6)}, {"name": "Ottimistico", "growth": round(g + data.spread, 6)},
                     {"name": "Pessimistico", "growth": round(g - data.spread, 6)}]
        used.append(f"Scenari generati: base = {origin} ({g * 100:+.2f}%), ottimistico e pessimistico ±{data.spread * 100:.1f} punti")
    return _guard(lambda: M.scenario_projection(name, unit, base_value, base_year, data.horizon, scenarios,
                                                data.uncertainty, history, used))


def rename(db: Session, user: User, sim_id: int, title: str) -> SimulationRun:
    r = get(db, user, sim_id)
    r.title = title.strip()[:300]
    res = dict(r.result or {})
    res["title"] = r.title
    r.result = res
    db.commit()
    db.refresh(r)
    return r


def _regression(db: Session, user: User, data: S.RegressionIn) -> M.SimulationResult:
    if data.y_series_id in data.x_series_ids:
        raise ValidationFailedError("La variabile dipendente non può essere anche un regressore.")
    ys = finance.get_series(db, user, data.y_series_id)
    xs = [finance.get_series(db, user, i) for i in data.x_series_ids]
    freqs = {s.frequency for s in [ys, *xs]}
    if len(freqs) > 1 and data.target_frequency is None:
        raise ValidationFailedError(f"Frequenze diverse ({', '.join(sorted(freqs))}): scegli esplicitamente una frequenza comune e un metodo.")
    target = data.target_frequency or freqs.pop()
    procedure = []

    def prep(s):
        series = analytics.to_pandas([(o.date, o.value) for o in s.observations])
        if s.frequency != target:
            try:
                series = analytics.resample(series, s.frequency, target, data.method)
            except analytics.AnalysisError as exc:
                raise ValidationFailedError(str(exc)) from exc
            procedure.append(f"«{s.name}» ricampionata da {s.frequency} a {target} ({data.method})")
        return series

    y = prep(ys)
    x_map = {s.name: prep(s) for s in xs}
    used = [f"{s.name} — {s.source_label}" for s in [ys, *xs]]
    return _guard(lambda: M.regression(ys.name, y, x_map, data.transform, data.lags, used, procedure, freq=target))


def list_runs(db: Session, user: User, kind: str | None = None) -> list[SimulationRun]:
    stmt = select(SimulationRun).where(SimulationRun.owner_id == user.id)
    if kind:
        stmt = stmt.where(SimulationRun.kind == kind)
    return list(db.scalars(stmt.order_by(SimulationRun.id.desc()).limit(200)))


def get(db: Session, user: User, sim_id: int) -> SimulationRun:
    r = db.get(SimulationRun, sim_id)
    if r is None or r.owner_id != user.id:
        raise NotFoundError("Simulazione non trovata.")
    return r


def delete(db: Session, user: User, sim_id: int, confirm: bool) -> None:
    r = get(db, user, sim_id)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare una simulazione richiede conferma (confirm=true).")
    db.delete(r)
    db.commit()
