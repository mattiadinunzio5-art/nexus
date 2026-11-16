"""Modelli quantitativi del laboratorio economico.

Ogni funzione restituisce un ``SimulationResult`` con ipotesi, variabili,
parametri, metodo, dati usati, risultati e limiti: nulla viene presentato come
previsione certa. Gli scenari controfattuali sono marcati come tali.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

PERCENTILES = (5, 25, 50, 75, 95)


class SimulationError(ValueError):
    pass


@dataclass
class SimulationResult:
    kind: str
    title: str
    hypotheses: list[str]
    variables: dict[str, str]
    parameters: dict
    method: str
    data_used: list[str]
    results: dict
    limitations: list[str]
    counterfactual: bool = False
    label: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d["label"]:
            d["label"] = ("Scenario ipotetico (controfattuale): non è una ricostruzione della storia." if self.counterfactual
                          else "Simulazione basata su ipotesi esplicite: non è una previsione.")
        return d


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else round(x, n)


def _fan(paths: np.ndarray, times: list) -> list[dict]:
    pct = np.percentile(paths, PERCENTILES, axis=0)
    return [{"t": times[i], **{f"p{p}": _r(pct[j, i]) for j, p in enumerate(PERCENTILES)}} for i in range(paths.shape[1])]


# --- Monte Carlo -----------------------------------------------------------------------


def _limits(limits):
    from .engine import DEFAULT

    return limits or DEFAULT


def _check(lim, n_paths: int, steps: int, years: float) -> None:
    from .engine import LimitError

    try:
        lim.check(n_paths, steps, years)
    except LimitError as exc:
        raise SimulationError(str(exc)) from exc


def _compute_note(col, n_paths: int, steps: int) -> dict:
    return {"blocks": col.blocks, "computed_values": n_paths * steps, "stored_values": int(col.on_grid.size),
            "note": f"Calcolo a {col.blocks} blocchi: in memoria solo {len(col.idx)} punti per traiettoria (griglia del grafico) invece di {steps + 1}."}


def monte_carlo_gbm(s0: float, mu: float, sigma: float, years: float, steps_per_year: int, n_paths: int, seed: int,
                    threshold: float | None = None, limits=None) -> SimulationResult:
    from . import engine

    if s0 <= 0 or sigma < 0 or years <= 0:
        raise SimulationError("Valore iniziale > 0, volatilità ≥ 0 e orizzonte > 0 sono obbligatori.")
    lim = _limits(limits)
    n = int(round(years * steps_per_year))
    _check(lim, n_paths, n, years)
    dt = 1 / steps_per_year
    col = engine.gbm(s0, mu, sigma, n, dt, n_paths, np.random.default_rng(seed), lim)
    final = col.final
    res = {
        "fan": engine.fan(col, [_r(i * dt, 4) for i in range(n + 1)]),
        "final": {"mean": _r(final.mean()), "median": _r(np.median(final)), **{f"p{p}": _r(np.percentile(final, p)) for p in PERCENTILES},
                  "analytic_mean": _r(s0 * math.exp(mu * years))},
        "sample_paths": [[_r(v, 4) for v in p] for p in col.samples],
        "computation": _compute_note(col, n_paths, n),
    }
    if threshold is not None:
        res["final"]["prob_below_threshold"] = _r((final < threshold).mean())
    return SimulationResult(
        kind="monte_carlo", title="Monte Carlo — moto browniano geometrico",
        hypotheses=["Rendimenti logaritmici normali, indipendenti e identicamente distribuiti", "Drift e volatilità costanti nel tempo",
                    "Nessun salto, nessun cambio di regime, nessuna correlazione seriale"],
        variables={"S(t)": "valore simulato", "μ": "drift annuo", "σ": "volatilità annua"},
        parameters={"s0": s0, "mu": mu, "sigma": sigma, "years": years, "steps_per_year": steps_per_year, "n_paths": n_paths, "seed": seed, "threshold": threshold},
        method="S(t+Δt) = S(t)·exp((μ − σ²/2)Δt + σ√Δt·Z), Z ~ N(0,1); percentili empirici sulle traiettorie, calcolate a blocchi",
        data_used=["Nessun dato storico: parametri inseriti dall'utente"], results=res,
        limitations=["Le code reali dei mercati sono più spesse della normale", "Parametri stimati dal passato non garantiscono il futuro",
                     f"Errore Monte Carlo: con {n_paths} traiettorie i percentili estremi sono instabili"],
    )


def monte_carlo_bootstrap(series_name: str, dates: list[str], values: list[float], ppy: int, years: float, n_paths: int,
                          block: int, seed: int, limits=None, freq: str | None = None) -> SimulationResult:
    from ..finance import analytics
    from . import engine

    v = np.array(values, dtype=float)
    if len(v) < 24 or (v <= 0).any():
        raise SimulationError("Il bootstrap richiede almeno 24 valori positivi (prezzi o indici).")
    lim = _limits(limits)
    # Rendimenti tra periodi consecutivi: quelli a cavallo di periodi mancanti sono esclusi (con la frequenza nota).
    if freq:
        r, info = analytics.changes(pd.Series(v, index=pd.to_datetime(dates)), freq, "log")
        rets = np.asarray(r, dtype=float)
    else:  # senza frequenza le date sono solo etichette: osservazioni consecutive
        rets, info = np.diff(np.log(v)), {"gaps": 0, "irregular": False}
    if len(rets) < 23:
        raise SimulationError(f"Solo {len(rets)} rendimenti tra periodi consecutivi: ne servono almeno 23.")
    gaps_note = analytics.gaps_note(series_name, info)
    n = int(round(years * ppy))
    _check(lim, n_paths, n, years)
    block = max(1, min(block, len(rets)))
    s0 = v[-1]
    col = engine.bootstrap(s0, rets, n, block, n_paths, np.random.default_rng(seed), lim)
    final = col.final
    return SimulationResult(
        kind="monte_carlo_bootstrap", title=f"Monte Carlo bootstrap — {series_name}",
        hypotheses=["Il futuro ricampiona blocchi di rendimenti storici osservati", "La distribuzione storica è rappresentativa"],
        variables={"r": "rendimento logaritmico per periodo"},
        parameters={"years": years, "n_paths": n_paths, "block": block, "seed": seed, "periods_per_year": ppy},
        method="Block bootstrap dei rendimenti logaritmici storici (blocchi contigui per preservare parte dell'autocorrelazione), traiettorie calcolate a blocchi",
        data_used=[f"{series_name}: {len(v)} osservazioni dal {dates[0]} al {dates[-1]}", *([gaps_note] if gaps_note else [])],
        results={"fan": engine.fan(col, [_r(i / ppy, 4) for i in range(n + 1)]),
                 "final": {"start": _r(s0), "mean": _r(final.mean()), **{f"p{p}": _r(np.percentile(final, p)) for p in PERCENTILES}},
                 "historical": {"mean_log_return": _r(rets.mean()), "std_log_return": _r(rets.std(ddof=1)), "n_returns": len(rets)},
                 "computation": _compute_note(col, n_paths, n)},
        limitations=["Non può generare eventi più estremi di quelli già osservati", "Ignora cambi strutturali successivi al campione",
                     "I dati sono la versione attuale della serie (possibili revisioni)"],
    )


# --- Debito pubblico ------------------------------------------------------------------------


def debt_path(d0: float, r: list[float], g: list[float], pb: list[float]) -> list[float]:
    """d(t+1) = d(t)·(1+r)/(1+g) − pb, tutto in % del PIL (r e g nominali, decimali)."""
    path = [d0]
    for rt, gt, pbt in zip(r, g, pb):
        if gt <= -1:
            raise SimulationError("Crescita nominale ≤ −100%: non definita.")
        path.append(path[-1] * (1 + rt) / (1 + gt) - pbt)
    return path


def debt_dynamics(d0: float, r_eff0: float, r_market: float, avg_maturity: float, g: float, pb: float, years: int,
                  rate_shock: float = 0.0, shock_start: int = 1, crisis: dict | None = None, stochastic: dict | None = None,
                  seed: int = 0, counterfactual: bool = False, limits=None) -> SimulationResult:
    if years < 1 or years > 100:
        raise SimulationError("Orizzonte tra 1 e 100 anni.")
    if avg_maturity <= 0:
        raise SimulationError("La vita media del debito deve essere > 0.")

    def scenario(shock: float, crisis_on: bool) -> dict:
        r_eff, rs, gs, pbs, reff_path = r_eff0, [], [], [], []
        for t in range(1, years + 1):
            market = r_market + (shock if t >= shock_start else 0.0)
            gt, pbt = g, pb
            if crisis_on and crisis and crisis["start"] <= t < crisis["start"] + crisis["years"]:
                gt += crisis.get("g_shock", 0.0)
                market += crisis.get("r_shock", 0.0)
                pbt += crisis.get("pb_shock", 0.0)
            # Il costo medio del debito converge al tasso di mercato via rifinanziamento (1/vita media all'anno).
            r_eff = r_eff + (market - r_eff) / avg_maturity
            rs.append(r_eff), gs.append(gt), pbs.append(pbt), reff_path.append(r_eff)
        path = debt_path(d0, rs, gs, pbs)
        interest = [path[i] * rs[i] for i in range(years)]
        return {"debt": [_r(x, 4) for x in path], "effective_rate": [_r(x, 5) for x in reff_path], "interest_pct_gdp": [_r(x, 4) for x in interest]}

    base = scenario(0.0, False)
    res = {"years": list(range(0, years + 1)), "baseline": base}
    if rate_shock:
        res["rate_shock"] = scenario(rate_shock, False)
        res["rate_shock_delta_final"] = _r(res["rate_shock"]["debt"][-1] - base["debt"][-1], 4)
    if crisis:
        res["crisis"] = scenario(rate_shock, True)
    stable_pb = d0 * (r_market - g) / (1 + g)
    res["debt_stabilizing_primary_balance"] = _r(stable_pb, 4)
    if stochastic:
        from . import engine

        lim = _limits(limits)
        n = int(stochastic.get("n_paths", 2000))
        _check(lim, n, years, years)
        sd_r, sd_g, rho = stochastic.get("sd_r", 0.01), stochastic.get("sd_g", 0.02), stochastic.get("corr", 0.0)
        cov = [[sd_r**2, rho * sd_r * sd_g], [rho * sd_r * sd_g, sd_g**2]]
        eff = np.array(base["effective_rate"], dtype=float)
        col = engine.debt_paths(d0, eff, g, pb, cov, n, np.random.default_rng(seed), lim)
        res["fan"] = engine.fan(col, list(range(years + 1)))
        res["prob_final_above_start"] = _r((col.final > d0).mean())
        res["computation"] = _compute_note(col, n, years)
        if getattr(col, "clipped", 0):
            res["clipped_growth_draws"] = col.clipped
    hyp = ["Debito e saldo primario in % del PIL", "Il costo medio del debito converge al tasso di mercato al ritmo 1/vita media",
           "Crescita nominale e saldo primario costanti salvo shock dichiarati", "Nessun effetto di retroazione (tassi→crescita, debito→spread)"]
    warn = []
    if stochastic:
        hyp.append("Incertezza: shock normali su tasso e crescita, correlati tra loro ma indipendenti da un anno all'altro (nessuna persistenza)")
        if res.get("clipped_growth_draws"):
            warn.append(f"{res['clipped_growth_draws']} estrazioni della crescita nominale sotto −99% sono state portate a −99%: "
                        "la deviazione standard indicata è troppo ampia per il modello.")
    return SimulationResult(
        kind="debt", title="Dinamica del debito pubblico",
        hypotheses=hyp, warnings=warn,
        variables={"d": "debito/PIL", "r": "costo medio effettivo del debito (nominale)", "g": "crescita del PIL nominale", "pb": "saldo primario/PIL"},
        parameters={"d0": d0, "r_eff0": r_eff0, "r_market": r_market, "avg_maturity": avg_maturity, "g": g, "pb": pb, "years": years,
                    "rate_shock": rate_shock, "shock_start": shock_start, "crisis": crisis, "stochastic": stochastic, "seed": seed},
        method="Equazione di accumulazione: d(t+1) = d(t)·(1+r)/(1+g) − pb; saldo primario stabilizzante = d·(r−g)/(1+g)"
               + ("; incertezza: shock normali correlati su r e g (Monte Carlo)" if stochastic else ""),
        data_used=["Parametri inseriti dall'utente"], results=res, counterfactual=counterfactual,
        limitations=["Modello contabile: non stima effetti macroeconomici dei tassi sulla crescita", "Ignora aggiustamenti stock-flussi, privatizzazioni, inflazione inattesa",
                     "La regola di rifinanziamento è un'approssimazione della struttura per scadenze"],
    )


def sensitivity(base_params: dict, ranges: dict[str, tuple[float, float]]) -> SimulationResult:
    """Sensitività one-at-a-time del debito finale rispetto ai parametri (diagramma a tornado)."""
    allowed = {"r_market", "g", "pb", "avg_maturity", "r_eff0", "d0"}
    bad = set(ranges) - allowed
    if bad:
        raise SimulationError(f"Parametri non ammessi nella sensitività: {', '.join(sorted(bad))}")
    keys = ("d0", "r_eff0", "r_market", "avg_maturity", "g", "pb", "years")

    def final(p):
        return debt_dynamics(**{k: p[k] for k in keys}).results["baseline"]["debt"][-1]

    base = final(base_params)
    rows = []
    for k, (lo, hi) in ranges.items():
        lo_v, hi_v = final({**base_params, k: lo}), final({**base_params, k: hi})
        rows.append({"parameter": k, "low": lo, "high": hi, "result_low": lo_v, "result_high": hi_v, "swing": _r(abs(hi_v - lo_v), 4)})
    rows.sort(key=lambda x: -x["swing"])
    return SimulationResult(
        kind="sensitivity", title="Analisi di sensitività — debito/PIL finale",
        hypotheses=["Un parametro alla volta varia nel suo intervallo, gli altri restano al valore base"],
        variables={"output": "debito/PIL all'ultimo anno"}, parameters={"base": base_params, "ranges": {k: list(v) for k, v in ranges.items()}},
        method="Sensitività one-at-a-time (OAT) sul modello di dinamica del debito", data_used=["Parametri inseriti dall'utente"],
        results={"base_result": base, "tornado": rows},
        limitations=["Non cattura le interazioni tra parametri", "Il risultato dipende dagli intervalli scelti"],
    )


# --- Inflazione e politiche monetarie --------------------------------------------------------------


def inflation_scenarios(amount: float, nominal_rate: float, years: int, inflation_levels: list[float]) -> SimulationResult:
    if not inflation_levels or len(inflation_levels) > 8:
        raise SimulationError("Indica da 1 a 8 livelli di inflazione.")
    rows, paths = [], {}
    for pi in inflation_levels:
        if pi <= -1:
            raise SimulationError("Inflazione ≤ −100% non ammessa.")
        real = (1 + nominal_rate) / (1 + pi) - 1
        pp = [amount / (1 + pi) ** t for t in range(years + 1)]
        nominal_inv = [amount * (1 + nominal_rate) ** t for t in range(years + 1)]
        real_inv = [nominal_inv[t] / (1 + pi) ** t for t in range(years + 1)]
        paths[str(pi)] = {"purchasing_power": [_r(x, 2) for x in pp], "real_value_of_investment": [_r(x, 2) for x in real_inv]}
        rows.append({"inflation": pi, "real_rate": _r(real), "purchasing_power_end": _r(pp[-1], 2), "real_investment_end": _r(real_inv[-1], 2),
                     "halving_years": _r(math.log(2) / math.log(1 + pi), 1) if pi > 0 else None})
    return SimulationResult(
        kind="inflation", title="Effetto di diversi livelli di inflazione",
        hypotheses=["Inflazione e tasso nominale costanti per tutto l'orizzonte", "Nessuna tassazione"],
        variables={"π": "inflazione annua", "i": "tasso nominale annuo", "r": "tasso reale (Fisher)"},
        parameters={"amount": amount, "nominal_rate": nominal_rate, "years": years, "inflation_levels": inflation_levels},
        method="Potere d'acquisto = A/(1+π)^t; tasso reale r = (1+i)/(1+π) − 1 (equazione di Fisher esatta)",
        data_used=["Parametri inseriti dall'utente"], results={"years": list(range(years + 1)), "summary": rows, "paths": paths},
        limitations=["L'inflazione reale varia nel tempo e tra panieri di consumo", "Non considera tasse, commissioni né indicizzazioni"],
    )


def taylor_rules(inflation: list[float], output_gap: list[float], labels: list[str], rules: list[dict], r_star: float, pi_target: float,
                 actual_rate: list[float] | None = None, counterfactual: bool = True) -> SimulationResult:
    if not (len(inflation) == len(output_gap) == len(labels)) or not labels:
        raise SimulationError("Inflazione, output gap ed etichette devono avere la stessa lunghezza (> 0).")
    if actual_rate is not None and len(actual_rate) != len(labels):
        raise SimulationError("Il tasso effettivo deve avere la stessa lunghezza delle altre serie.")
    out = {}
    for rule in rules[:6]:
        a, b, floor = rule.get("a", 0.5), rule.get("b", 0.5), rule.get("floor")
        rates = [r_star + pi + a * (pi - pi_target) + b * gap for pi, gap in zip(inflation, output_gap)]
        if floor is not None:
            rates = [max(floor, x) for x in rates]
        out[rule.get("name", f"a={a}, b={b}")] = [_r(x, 4) for x in rates]
    res = {"labels": labels, "prescribed": out}
    if actual_rate is not None:
        res["actual"] = actual_rate
        res["gap_vs_actual"] = {k: [_r(p - a, 4) for p, a in zip(v, actual_rate)] for k, v in out.items()}
    return SimulationResult(
        kind="monetary_policy", title="Confronto tra regole di politica monetaria (regola di Taylor)",
        hypotheses=["La banca centrale seguirebbe meccanicamente la regola indicata", "Tasso reale neutrale e obiettivo d'inflazione costanti",
                    "Nessun effetto della politica sui dati di inflazione e output gap usati (analisi statica)"],
        variables={"i": "tasso prescritto", "π": "inflazione", "π*": "obiettivo", "r*": "tasso reale neutrale", "gap": "output gap"},
        parameters={"r_star": r_star, "pi_target": pi_target, "rules": rules},
        method="i = r* + π + a·(π − π*) + b·gap (Taylor, 1993), con eventuale limite inferiore",
        data_used=["Serie di inflazione e output gap fornite dall'utente"], results=res, counterfactual=counterfactual,
        limitations=["Le stime di r* e dell'output gap sono molto incerte e vengono riviste", "Le regole prescrittive non descrivono le decisioni effettive",
                     "Confronto controfattuale: non indica cosa sarebbe successo all'economia con tassi diversi"],
    )


# --- Regressione -------------------------------------------------------------------------------------------


PERIOD_CODE = {"W": "W", "M": "M", "Q": "Q", "A": "Y"}


def regression(y_name: str, y: pd.Series, xs: dict[str, pd.Series], transform: str, lags: int, data_used: list[str], procedure: list[str],
               freq: str | None = None) -> SimulationResult:
    import statsmodels.api as sm
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.tsa.stattools import adfuller

    df = pd.concat({"y": y, **{f"x_{k}": v for k, v in xs.items()}}, axis=1)
    if freq in PERIOD_CODE and len(df):
        # Calendario regolare: i periodi mancanti restano righe vuote, così differenze e ritardi non li scavalcano.
        code = PERIOD_CODE[freq]
        df.index = df.index.to_period(code)
        df = df.groupby(level=0).last()
        full = pd.period_range(df.index.min(), df.index.max(), freq=code)
        missing = len(full) - len(df.dropna())
        df = df.reindex(full)
        df.index = df.index.to_timestamp()
        if missing and transform != "levels":
            procedure = [*procedure, f"{missing} periodi senza dati per tutte le variabili nel periodo comune: le variazioni a cavallo sono escluse"]
    if transform == "diff":
        df = df.diff()
    elif transform == "pct":
        if (df <= 0).any().any():
            raise SimulationError("Variazioni percentuali non definite per valori ≤ 0: usa le differenze.")
        df = df.pct_change()
    if lags:
        for k in xs:
            df[f"x_{k}"] = df[f"x_{k}"].shift(lags)
    df = df.dropna()
    if len(df) < len(xs) + 5:
        raise SimulationError(f"Osservazioni comuni insufficienti ({len(df)}) per {len(xs)} regressori.")
    X = sm.add_constant(df[[c for c in df.columns if c != "y"]])
    hac_lags = max(1, int(4 * (len(df) / 100) ** (2 / 9)))
    model = sm.OLS(df["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    coefs = [{"name": n.replace("x_", ""), "coef": _r(model.params[n]), "std_err": _r(model.bse[n]), "t": _r(model.tvalues[n], 3), "p_value": _r(model.pvalues[n], 4),
              "ci_low": _r(model.conf_int().loc[n, 0]), "ci_high": _r(model.conf_int().loc[n, 1])} for n in model.params.index]
    warnings = []
    if transform == "levels":
        for col in df.columns:
            try:
                if adfuller(df[col].values, autolag="AIC", result_object=False)[1] > 0.05:
                    warnings.append(f"«{col.replace('x_', '')}» probabilmente non stazionaria in livelli: rischio di regressione spuria (usa differenze).")
            except ValueError:
                pass
    dw = durbin_watson(model.resid)
    if dw < 1.5 or dw > 2.5:
        warnings.append(f"Durbin-Watson {dw:.2f}: residui autocorrelati (errori standard HAC già applicati).")
    return SimulationResult(
        kind="regression", title=f"Regressione OLS — {y_name}",
        hypotheses=["Relazione lineare", "Regressori esogeni", "Errori con media zero (eteroschedasticità e autocorrelazione gestite con HAC)"],
        variables={"y": y_name, **{k: "regressore" for k in xs}},
        parameters={"transform": transform, "lags": lags, "hac_maxlags": hac_lags},
        method="Minimi quadrati ordinari (statsmodels) con errori standard Newey-West (HAC)", data_used=data_used + procedure,
        results={"n": int(model.nobs), "r2": _r(model.rsquared), "r2_adj": _r(model.rsquared_adj), "coefficients": coefs,
                 "durbin_watson": _r(dw, 3), "f_pvalue": _r(model.f_pvalue, 4),
                 "fitted": [{"date": d.strftime("%Y-%m-%d"), "actual": _r(a), "fitted": _r(f)} for d, a, f in zip(df.index, df["y"], model.fittedvalues)]},
        limitations=["Associazione statistica, non causalità", "Variabili omesse possono distorcere i coefficienti", "Dati nella versione attuale (possibili revisioni)"],
        warnings=warnings,
    )


# --- Backtesting -------------------------------------------------------------------------------------------


def backtest(name: str, dates: list[str], prices: list[float], ppy: int, strategy: str, params: dict, cost_bps: float, rf: float,
             first_available: str | None = None) -> SimulationResult:
    """Backtest senza look-ahead: il segnale calcolato con i dati fino a t determina la posizione da t+1."""
    p = pd.Series(prices, index=pd.to_datetime(dates), dtype=float).dropna()
    if len(p) < 30 or (p <= 0).any():
        raise SimulationError("Servono almeno 30 prezzi positivi.")
    ret = p.pct_change().fillna(0.0)
    if strategy == "buy_hold":
        signal = pd.Series(1.0, index=p.index)
    elif strategy == "ma_cross":
        fast, slow = int(params.get("fast", 10)), int(params.get("slow", 50))
        if not 1 <= fast < slow < len(p):
            raise SimulationError("Serve 1 ≤ fast < slow < numero di osservazioni.")
        signal = (p.rolling(fast).mean() > p.rolling(slow).mean()).astype(float)
        signal[p.rolling(slow).mean().isna()] = 0.0
    elif strategy == "momentum":
        lb = int(params.get("lookback", 12))
        if not 1 <= lb < len(p):
            raise SimulationError("Lookback non valido.")
        signal = (p / p.shift(lb) - 1 > 0).astype(float)
        signal[p.shift(lb).isna()] = 0.0
    else:
        raise SimulationError("Strategia sconosciuta.")
    position = signal.shift(1).fillna(0.0)  # nessun look-ahead
    turnover = position.diff().abs().fillna(position.abs())
    strat_ret = position * ret - turnover * cost_bps / 10000 + (1 - position) * rf / ppy
    equity = (1 + strat_ret).cumprod()
    bench = (1 + ret).cumprod()

    def metrics(r: pd.Series, eq: pd.Series) -> dict:
        years = len(r) / ppy
        dd = eq / eq.cummax() - 1
        vol = r.std(ddof=1) * math.sqrt(ppy)
        cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else None
        return {"total_return": _r(eq.iloc[-1] - 1), "cagr": _r(cagr), "volatility": _r(vol), "sharpe": _r((r.mean() * ppy - rf) / vol) if vol > 0 else None,
                "max_drawdown": _r(dd.min())}

    warnings = ["Bias di sopravvivenza: lo strumento è stato scelto oggi, sapendo che esiste ancora; i risultati possono essere ottimistici.",
                "Dati nella versione attuale: eventuali revisioni non erano note all'epoca (nessun archivio point-in-time).",
                "Parametri della strategia scelti a posteriori: rischio di sovra-adattamento (data snooping)."]
    if first_available and first_available > dates[0]:
        warnings.append(f"La serie è stata resa disponibile solo dal {first_available}.")
    step = max(1, len(p) // 400)
    return SimulationResult(
        kind="backtest", title=f"Backtest — {name}", hypotheses=["Esecuzione al prezzo del periodo successivo al segnale", "Costi proporzionali al turnover",
                                                                  "Liquidità remunerata al tasso privo di rischio indicato quando fuori mercato"],
        variables={"position(t)": "esposizione decisa con dati fino a t−1"},
        parameters={"strategy": strategy, **params, "cost_bps": cost_bps, "rf": rf, "periods_per_year": ppy},
        method="Segnale calcolato con dati fino a t, applicato da t+1 (shift di un periodo); rendimenti semplici; metriche annualizzate",
        data_used=[f"{name}: {len(p)} osservazioni dal {dates[0]} al {dates[-1]}"],
        results={"strategy": metrics(strat_ret, equity), "benchmark_buy_hold": metrics(ret, bench),
                 "trades": int((turnover > 0).sum()), "exposure": _r(position.mean()),
                 "equity": [{"date": d.strftime("%Y-%m-%d"), "strategy": _r(e, 5), "benchmark": _r(b, 5)} for d, e, b in list(zip(p.index, equity, bench))[::step]]},
        limitations=["Un backtest descrive il passato, non garantisce risultati futuri", "Non considera slippage, tasse, vincoli di liquidità"],
        warnings=warnings,
    )


# --- Proiezione a scenari ----------------------------------------------------------------


def scenario_projection(name: str, unit: str, base_value: float, base_year: int, horizon: int, scenarios: list[dict],
                        uncertainty: float, history: dict | None, data_used: list[str]) -> SimulationResult:
    """Valore_t = V0 · (1+g)^t per ogni scenario; con incertezza σ sulla crescita, banda al 90% log-normale."""
    if base_value <= 0:
        raise SimulationError("Il valore di partenza deve essere positivo.")
    names = [s["name"] for s in scenarios]
    if len(set(names)) != len(names):
        raise SimulationError("Ogni scenario deve avere un nome diverso.")
    years = [base_year + t for t in range(horizon + 1)]
    paths, rows = {}, []
    z = 1.6449  # quantile 95%: banda centrale al 90%
    for sc in scenarios:
        g = sc["growth"]
        if g <= -1:
            raise SimulationError("Crescita ≤ −100% non ammessa.")
        mid = [base_value * (1 + g) ** t for t in range(horizon + 1)]
        p = {"value": [_r(x, 4) for x in mid]}
        if uncertainty > 0:
            p["low"] = [_r(m * math.exp(-z * uncertainty * math.sqrt(t)), 4) for t, m in enumerate(mid)]
            p["high"] = [_r(m * math.exp(z * uncertainty * math.sqrt(t)), 4) for t, m in enumerate(mid)]
        paths[sc["name"]] = p
        rows.append({"scenario": sc["name"], "growth": g, "end_value": _r(mid[-1], 4), "multiple": _r(mid[-1] / base_value, 3),
                     "doubling_years": _r(math.log(2) / math.log(1 + g), 1) if g > 0 else None,
                     **({"end_low": p["low"][-1], "end_high": p["high"][-1]} if uncertainty > 0 else {})})
    hyp = ["Crescita annua costante in ciascuno scenario per tutto l'orizzonte",
           f"Valore di partenza: {base_value:.4g} {unit} nel {base_year}".strip()]
    if uncertainty > 0:
        hyp.append(f"Incertezza: deviazione standard annua della crescita {uncertainty * 100:.1f} punti (banda centrale al 90%)")
    lim = ["È una proiezione condizionata alle ipotesi, non una previsione: non stima la probabilità dei singoli scenari",
           "Non modella rotture strutturali, politiche, saturazione del mercato o shock",
           "Le crescite degli scenari sono scelte dall'utente: vanno motivate con fonti nel testo"]
    if history:
        hyp.append(f"Riferimento storico: crescita media annua {history['cagr'] * 100:+.2f}% tra {history['from']} e {history['to']} (dati della serie)")
    return SimulationResult(
        kind="scenarios", title=f"Scenari di proiezione: {name}",
        hypotheses=hyp, variables={"V0": "valore di partenza", "g": "crescita annua composta dello scenario", "t": "anni dal punto di partenza"},
        parameters={"base_value": base_value, "base_year": base_year, "horizon": horizon, "scenarios": scenarios, "uncertainty": uncertainty, "unit": unit},
        method="V(t) = V0 · (1+g)^t" + ("; banda: V(t) · exp(±1,645 · σ · √t)" if uncertainty > 0 else ""),
        data_used=data_used, results={"years": years, "paths": paths, "summary": rows, "history": history, "unit": unit,
                                      "comparison": [{"scenario": r["scenario"], "end_value": r["end_value"],
                                                      "delta_vs_reference": _r(r["end_value"] - rows[0]["end_value"], 4),
                                                      "pct_vs_reference": _r(r["end_value"] / rows[0]["end_value"] - 1, 4) if rows[0]["end_value"] else None}
                                                     for r in rows], "reference": rows[0]["scenario"]},
        limitations=lim,
    )
