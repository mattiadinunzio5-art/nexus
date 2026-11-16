"""Modelli settoriali semplici: produzione industriale, occupazione, commercio internazionale, consumi.

Ogni modello è una regola esplicita (formula scritta nel risultato), con ipotesi e limiti dichiarati.
I parametri (elasticità, tassi, valori di partenza) li inserisce l'utente: NEXUS non fornisce valori
predefiniti, perché ogni numero deve venire da una fonte che l'utente cita.

Ogni modello si esegue per tre scenari: base, ottimistico e pessimistico. Gli scenari alternativi
cambiano solo i parametri indicati dall'utente; il confronto riporta la differenza dalla base.
"""

from __future__ import annotations

from .models import SimulationError, SimulationResult, _r

SCENARIO_LABEL = {"base": "Base", "optimistic": "Ottimistico", "pessimistic": "Pessimistico"}


def _industrial(p: dict) -> dict:
    """IP_t = min(IP_{t−1}·(1+g_t), Cap_t);  g_t = g_trend + ε_d·g_domanda − ε_e·Δp_energia;  Cap_t = k·IP_0·(1+g_cap)^t."""
    g = p["trend_growth"] + p["demand_elasticity"] * p["demand_growth"] - p["energy_elasticity"] * p["energy_price_change"]
    if g <= -1:
        raise SimulationError("La crescita implicita della produzione è ≤ −100%: controlla elasticità e shock.")
    ip, out_ip, out_cap, out_u = p["ip0"], [p["ip0"]], [p["capacity_ratio"] * p["ip0"]], [1 / p["capacity_ratio"]]
    bound = 0
    for t in range(1, p["years"] + 1):
        cap = p["capacity_ratio"] * p["ip0"] * (1 + p["capacity_growth"]) ** t
        want = ip * (1 + g)
        ip = min(want, cap)
        bound += want > cap
        out_ip.append(ip), out_cap.append(cap), out_u.append(ip / cap)
    return {"series": {"Produzione industriale (indice)": out_ip, "Capacità produttiva": out_cap, "Utilizzo della capacità": out_u},
            "headline": "Produzione industriale (indice)", "implied_growth": g, "capacity_bound_years": bound}


def _employment(p: dict) -> dict:
    """Legge di Okun: u_t = u_{t−1} − β·(g − g*);  LF_t = LF_0·(1+n)^t;  E_t = LF_t·(1 − u_t)."""
    u, lf = p["u0"], p["labour_force0"]
    us, es, lfs = [u], [lf * (1 - u)], [lf]
    floor = 0
    for t in range(1, p["years"] + 1):
        u = u - p["okun_beta"] * (p["gdp_growth"] - p["potential_growth"])
        if u < 0.01:
            u, floor = 0.01, floor + 1
        u = min(u, 0.6)
        lf = p["labour_force0"] * (1 + p["labour_force_growth"]) ** t
        us.append(u), lfs.append(lf), es.append(lf * (1 - u))
    return {"series": {"Occupati": es, "Forze di lavoro": lfs, "Tasso di disoccupazione": us}, "headline": "Occupati", "floor_years": floor}


def _trade(p: dict) -> dict:
    """g_X = ε_X·g_mondo − η_X·Δq;  g_M = ε_M·g_interna + η_M·Δq;  saldo = (X − M)/PIL (Δq>0: apprezzamento reale)."""
    gx = p["income_elasticity_exports"] * p["world_growth"] - p["price_elasticity_exports"] * p["reer_change"]
    gm = p["income_elasticity_imports"] * p["domestic_growth"] + p["price_elasticity_imports"] * p["reer_change"]
    if gx <= -1 or gm <= -1:
        raise SimulationError("Crescita implicita di esportazioni o importazioni ≤ −100%.")
    x, m, y = p["exports0"], p["imports0"], p["gdp0"]
    xs, ms, bal = [x], [m], [(x - m) / y]
    for _ in range(p["years"]):
        x, m, y = x * (1 + gx), m * (1 + gm), y * (1 + p["domestic_growth"])
        xs.append(x), ms.append(m), bal.append((x - m) / y)
    return {"series": {"Esportazioni": xs, "Importazioni": ms, "Saldo commerciale (quota del PIL)": bal}, "headline": "Saldo commerciale (quota del PIL)",
            "marshall_lerner": p["price_elasticity_exports"] + p["price_elasticity_imports"] > 1, "export_growth": gx, "import_growth": gm}


def _consumption(p: dict) -> dict:
    """Y_t = Y_0·(1+g)^t;  Yd_t = Y_t·(1−τ);  W_t = W_0·(1+g_W)^t;  C_t = a + c·Yd_t + w·W_t;  risparmio = 1 − C_t/Yd_t."""
    cs, yds, sav = [], [], []
    for t in range(p["years"] + 1):
        yd = p["income0"] * (1 + p["income_growth"]) ** t * (1 - p["tax_rate"])
        w = p["wealth0"] * (1 + p["wealth_growth"]) ** t
        c = p["autonomous"] + p["mpc"] * yd + p["wealth_effect"] * w
        cs.append(c), yds.append(yd), sav.append(1 - c / yd if yd else None)
    return {"series": {"Consumi": cs, "Reddito disponibile": yds, "Tasso di risparmio": sav}, "headline": "Consumi",
            "dissaving_years": sum(1 for s in sav if s is not None and s < 0)}


MODELS = {
    "industrial_production": {
        "fn": _industrial, "title": "Produzione industriale",
        "variables": {"IP": "indice della produzione industriale", "g_trend": "crescita di fondo", "ε_d": "elasticità alla domanda",
                      "g_domanda": "crescita della domanda", "ε_e": "elasticità al prezzo dell'energia", "Δp_energia": "variazione annua del prezzo dell'energia",
                      "k": "capacità iniziale / produzione iniziale", "g_cap": "crescita della capacità"},
        "hypotheses": ["Crescita costante per tutto l'orizzonte, determinata da domanda ed energia con elasticità fisse",
                       "La produzione non può superare la capacità installata", "Nessun effetto di ritorno della produzione sulla domanda o sui prezzi"],
        "limitations": ["Modello a una equazione: non distingue i settori né le scorte", "Le elasticità vanno stimate o prese dalla letteratura (citandola)",
                        "Ignora shock d'offerta diversi dall'energia (materie prime, logistica, credito)"],
    },
    "employment": {
        "fn": _employment, "title": "Occupazione (legge di Okun)",
        "variables": {"u": "tasso di disoccupazione", "β": "coefficiente di Okun", "g": "crescita del PIL reale", "g*": "crescita potenziale",
                      "LF": "forze di lavoro", "n": "crescita delle forze di lavoro", "E": "occupati"},
        "hypotheses": ["Relazione lineare e stabile tra crescita e variazione della disoccupazione (Okun)",
                       "Partecipazione al lavoro indipendente dal ciclo", "Disoccupazione limitata tra 1% e 60%"],
        "limitations": ["Il coefficiente di Okun varia tra paesi e periodi: va stimato sui dati del paese",
                        "Non distingue tempo pieno e parziale, ore lavorate, lavoro irregolare", "Ignora politiche del lavoro e demografia dettagliata"],
    },
    "trade": {
        "fn": _trade, "title": "Commercio internazionale",
        "variables": {"X": "esportazioni", "M": "importazioni", "ε_X, ε_M": "elasticità al reddito (mondiale, interno)",
                      "η_X, η_M": "elasticità al prezzo (valori positivi)", "Δq": "variazione del tasso di cambio reale (+ = apprezzamento)"},
        "hypotheses": ["Domanda di esportazioni e importazioni con elasticità costanti al reddito e al cambio reale",
                       "Esportazioni, importazioni e PIL nella stessa unità di misura", "Nessuna risposta dei prezzi interni al cambio (pass-through nullo)"],
        "limitations": ["Ignora catene globali del valore e contenuto importato delle esportazioni", "Condizione di Marshall–Lerner solo indicativa",
                        "Non modella i servizi, i redditi e i trasferimenti (saldo di parte corrente)"],
    },
    "consumption": {
        "fn": _consumption, "title": "Consumi delle famiglie",
        "variables": {"C": "consumi", "a": "consumo autonomo", "c": "propensione marginale al consumo", "Yd": "reddito disponibile",
                      "τ": "aliquota media", "W": "ricchezza", "w": "effetto ricchezza (quota consumata ogni anno)"},
        "hypotheses": ["Funzione del consumo keynesiana con effetto ricchezza (parametri costanti)", "Reddito e ricchezza crescono a tassi costanti",
                       "Nessun vincolo di credito né aspettative sul reddito futuro"],
        "limitations": ["Non è un modello del ciclo di vita né del reddito permanente", "Propensione e effetto ricchezza vanno stimati sui dati",
                        "Ignora inflazione, tassi d'interesse e distribuzione del reddito"],
    },
}


def run_sector(kind: str, base: dict, overrides: dict[str, dict], units: str = "", data_used: list[str] | None = None) -> SimulationResult:
    spec = MODELS[kind]
    fn = spec["fn"]
    unknown = {k for o in overrides.values() for k in o} - set(base)
    if unknown:
        raise SimulationError(f"Parametri sconosciuti negli scenari: {', '.join(sorted(unknown))}.")
    runs = {"base": fn(base)}
    for name in ("optimistic", "pessimistic"):
        if overrides.get(name):
            runs[name] = fn({**base, **overrides[name]})
    years = list(range(base["years"] + 1))
    headline = runs["base"]["headline"]
    comparison = []
    for name, r in runs.items():
        end = r["series"][headline][-1]
        b_end = runs["base"]["series"][headline][-1]
        comparison.append({"scenario": SCENARIO_LABEL[name], "key": name, "end_value": _r(end, 6), "delta_vs_base": _r(end - b_end, 6),
                           "changed": overrides.get(name, {}) if name != "base" else {}})
    results = {"years": years, "headline": headline, "unit": units,
               "scenarios": {SCENARIO_LABEL[k]: {n: [_r(v, 6) for v in s] for n, s in r["series"].items()} for k, r in runs.items()},
               "comparison": comparison,
               "diagnostics": {SCENARIO_LABEL[k]: {d: v for d, v in r.items() if d not in ("series", "headline")} for k, r in runs.items()}}
    warnings = []
    if len(runs) < 3:
        warnings.append("Indica sia lo scenario ottimistico sia quello pessimistico per un confronto completo.")
    if kind == "trade" and not runs["base"]["marshall_lerner"]:
        warnings.append("Condizione di Marshall–Lerner non soddisfatta: un deprezzamento peggiorerebbe il saldo commerciale.")
    if kind == "industrial_production" and runs["base"]["capacity_bound_years"]:
        warnings.append(f"Nello scenario base la produzione tocca il limite di capacità per {runs['base']['capacity_bound_years']} anni.")
    return SimulationResult(
        kind=kind, title=spec["title"], hypotheses=spec["hypotheses"], variables=spec["variables"],
        parameters={"base": base, "scenarios": overrides, "unit": units},
        method=(fn.__doc__ or "").strip() + " Tre scenari: base, ottimistico, pessimistico (cambiano solo i parametri indicati).",
        data_used=data_used or ["Parametri inseriti dall'utente (da motivare con fonti)"], results=results,
        limitations=spec["limitations"], warnings=warnings,
    )
