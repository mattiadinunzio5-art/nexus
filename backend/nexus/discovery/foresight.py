"""Componente F — Strategic Foresight.

Tre scenari (ottimistico, centrale, avverso) per le variabili scelte, costruiti con un
bootstrap a blocchi delle VARIAZIONI storiche (funziona anche per tassi e valori negativi).
Le bande sono i percentili 10, 50 e 90 della distribuzione simulata: è l'unica
quantificazione presentata, ed è dichiarata come prodotto del modello. Nessuna probabilità
viene attribuita agli scenari in sé.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core import library
from ..core.errors import NotFoundError, ValidationFailedError
from ..models import DiscoveryAnomaly, DiscoveryHypothesis, Entity, Relation, Series, User
from .connections import series_frame

PPY = {"A": 1, "Q": 4, "M": 12, "W": 52, "D": 252}
MIN_OBS = 20


N_PATHS, BLOCK, SEED = 2000, 3, 7


def fingerprint(s: Series) -> str:
    """Impronta dei dati usati (date e valori): due esecuzioni con la stessa impronta e gli stessi parametri danno lo stesso risultato."""
    import hashlib

    h = hashlib.sha256()
    for o in sorted(s.observations, key=lambda o: o.date):
        h.update(f"{o.date}={o.value!r};".encode())
    return h.hexdigest()[:16]


def bootstrap_changes(values: np.ndarray, n_steps: int, n_paths: int = N_PATHS, block: int = BLOCK, seed: int = SEED,
                      changes: np.ndarray | None = None, multiplicative: bool = False) -> np.ndarray:
    """Traiettorie dal bootstrap a blocchi delle variazioni storiche.

    ``changes`` sono le variazioni tra periodi consecutivi (senza quelle a cavallo di buchi); se assenti si usano le
    differenze dei valori. Con ``multiplicative`` le variazioni sono logaritmiche e i livelli = ultimo valore · exp(somma).
    """
    d = np.diff(values) if changes is None else np.asarray(changes, dtype=float)
    rng = np.random.default_rng(seed)
    block = max(1, min(block, len(d)))
    out = np.empty((n_paths, n_steps))
    for k in range(n_paths):
        buf: list[float] = []
        while len(buf) < n_steps:
            s = rng.integers(0, len(d) - block + 1)
            buf.extend(d[s:s + block])
        out[k] = buf[:n_steps]
    cum = np.cumsum(out, axis=1)
    return values[-1] * np.exp(cum) if multiplicative else values[-1] + cum


def scenarios(db: Session, user: User, variables: list[dict], horizon_years: float, triggers: list[str] | None = None) -> dict:
    if not 1 <= len(variables) <= 6:
        raise ValidationFailedError("Scegli da 1 a 6 variabili.")
    if not 0.25 <= horizon_years <= 10:
        raise ValidationFailedError("Orizzonte tra 3 mesi e 10 anni.")
    owners = library.visible_owner_ids(db, user)  # serie proprie o della Biblioteca NEXUS (sola lettura), mai di altri utenti
    from ..finance import analytics

    rows, excluded, data_notes, used = [], [], [], {}
    for var in variables:
        s = db.get(Series, var["series_id"])
        if s is None or s.owner_id not in owners:
            raise NotFoundError(f"Serie {var['series_id']} non trovata.")
        v = series_frame(s)
        if len(v) < MIN_OBS:
            excluded.append(f"«{s.name}»: {len(v)} osservazioni, ne servono almeno {MIN_OBS}.")
            continue
        # Serie positive che crescono di ordini di grandezza: variazioni percentuali (log), come nel resto della Discovery.
        multiplicative = analytics.scale_free(v)
        d, info = analytics.changes(v, s.frequency, "log" if multiplicative else "diff")
        if len(d) < MIN_OBS - 1:
            excluded.append(f"«{s.name}»: {len(d)} variazioni tra periodi consecutivi, ne servono almeno {MIN_OBS - 1}.")
            continue
        if note := analytics.gaps_note(s.name, info):
            data_notes.append(note)
        missing = sum(1 for o in s.observations if o.value is None)
        if missing:
            data_notes.append(f"«{s.name}»: {missing} osservazioni senza valore ignorate.")
        used[s.id] = s
        ppy = PPY.get(s.frequency, 12)
        n = max(1, int(round(horizon_years * ppy)))
        paths = bootstrap_changes(v.values.astype(float), n, changes=d.values, multiplicative=multiplicative)
        final = paths[:, -1]
        p10, p50, p90 = (float(np.percentile(final, q)) for q in (10, 50, 90))
        up_good = var.get("favorable", "up") == "up"
        fan = [{"step": i + 1, "p10": float(np.percentile(paths[:, i], 10)), "p50": float(np.percentile(paths[:, i], 50)),
                "p90": float(np.percentile(paths[:, i], 90))} for i in range(0, n, max(1, n // 24))]
        rows.append({"series_id": s.id, "name": s.name, "unit": s.unit, "frequency": s.frequency, "favorable": "up" if up_good else "down",
                     "initial": {"date": v.index[-1].strftime("%Y-%m-%d"), "value": float(v.iloc[-1])},
                     "history": {"n": len(v), "from": v.index[0].strftime("%Y-%m-%d"), "to": v.index[-1].strftime("%Y-%m-%d")},
                     "optimistic": p90 if up_good else p10, "central": p50, "adverse": p10 if up_good else p90, "fan": fan,
                     "source": s.source_label, "changes": "percentuali (log)" if multiplicative else "assolute",
                     "n_changes": len(d), "data_fingerprint": fingerprint(s)})
    if not rows:
        raise ValidationFailedError("Nessuna variabile ha dati sufficienti. " + " ".join(excluded))
    ids = [r["series_id"] for r in rows]
    dependencies, inconsistent = _dependencies(rows, used)
    # Eventi scatenanti: anomalie aperte e ipotesi in corso che riguardano le variabili, più quelli indicati dall'utente.
    auto_triggers = []
    for a in db.scalars(select(DiscoveryAnomaly).where(DiscoveryAnomaly.owner_id == user.id, DiscoveryAnomaly.status == "open")):
        sid = a.refs.get("series_id")
        if sid in ids or set(a.refs.get("series_ids", [])) & set(ids):
            auto_triggers.append(f"Anomalia aperta: {a.title}")
    for h in db.scalars(select(DiscoveryHypothesis).where(DiscoveryHypothesis.owner_id == user.id, DiscoveryHypothesis.archived.is_(False),
                                                           DiscoveryHypothesis.status.in_(("to_verify", "verifying")))):
        if any(r["name"] in h.phenomena for r in rows):
            auto_triggers.append(f"Ipotesi da verificare: {h.title}")
    # Conseguenze documentate nel grafo a partire dagli indicatori.
    consequences = []
    ent = {e.series_id: e for e in db.scalars(select(Entity).where(Entity.owner_id.in_(owners), Entity.series_id.in_(ids)))}
    for sid, e in ent.items():
        for r in db.scalars(select(Relation).where(Relation.owner_id.in_(owners), Relation.source_entity_id == e.id,
                                                   Relation.relation_type.in_(("caused", "influenced")))):
            tgt = db.get(Entity, r.target_entity_id)
            consequences.append({"from": e.name, "to": tgt.name if tgt else "?", "relation": r.relation_type,
                                 "documented": r.provenance == "sourced"})

    def describe(kind: str) -> list[str]:
        out = []
        for r in rows:
            val = r[kind]
            out.append(f"{r['name']}: {val:.4g} {r['unit']} (oggi {r['initial']['value']:.4g})")
        return out

    return {
        "horizon_years": horizon_years,
        "variables": rows,
        "excluded": excluded,
        "scenarios": {
            "optimistic": {"title": "Scenario ottimistico", "definition": "Percentile favorevole (90° o 10°, secondo la direzione indicata) di ogni variabile", "values": describe("optimistic")},
            "central": {"title": "Scenario centrale", "definition": "Mediana (50° percentile) della distribuzione simulata", "values": describe("central")},
            "adverse": {"title": "Scenario avverso", "definition": "Percentile sfavorevole (10° o 90°) di ogni variabile", "values": describe("adverse")},
        },
        "initial_conditions": [f"{r['name']}: {r['initial']['value']:.4g} {r['unit']} al {r['initial']['date']} (fonte: {r['source']})" for r in rows],
        "triggers": (triggers or []) + auto_triggers,
        "consequences": consequences,
        "indicators_to_monitor": [{"series_id": r["series_id"], "name": r["name"], "adverse_threshold": r["adverse"], "optimistic_threshold": r["optimistic"]} for r in rows],
        "dependencies": dependencies,
        "data_notes": data_notes,
        "reproducibility": {"seed": SEED, "n_paths": N_PATHS, "block": BLOCK, "generator": "numpy.random.default_rng (PCG64)",
                            "numpy": np.__version__, "data": {r["name"]: r["data_fingerprint"] for r in rows}},
        "uncertainties": [
            "Il modello ricampiona variazioni già osservate: non può produrre shock più grandi di quelli presenti nella storia della serie.",
            "Le variabili sono simulate separatamente: le relazioni tra di loro non sono modellate, quindi gli estremi possono non verificarsi insieme.",
            *inconsistent,
            "Cambi strutturali successivi al campione non sono considerati.",
            "I dati sono la versione attuale delle serie (possibili revisioni).",
        ],
        "method": "Bootstrap a blocchi (3 periodi) delle variazioni storiche, 2000 traiettorie, seme fisso 7 (risultati riproducibili).",
        "probability_note": "Le bande corrispondono ai percentili 10/50/90 del modello; agli scenari non sono attribuite altre probabilità.",
    }


def _dependencies(rows: list[dict], used: dict[int, Series]) -> tuple[list[dict], list[str]]:
    """Legami storici tra le variabili: correlazione delle variazioni nello stesso periodo (ritardo 0).

    Il modello non li usa (simula ogni variabile da sola): servono a dire quando gli scenari ottimistico e avverso,
    che combinano gli estremi favorevoli o sfavorevoli di tutte le variabili, uniscono valori che in passato tendevano
    a NON verificarsi insieme. È una descrizione del passato, non un modello delle dipendenze.
    """
    from .connections import lagged_association, series_frame

    out, warn = [], []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            sa, sb = used[a["series_id"]], used[b["series_id"]]
            try:
                res = lagged_association(series_frame(sa), series_frame(sb), sa.frequency, sb.frequency, max_lag=0)
            except Exception:  # noqa: BLE001 — frequenze non confrontabili o dati insufficienti: nessuna stima
                res = None
            if not res:
                out.append({"a": a["name"], "b": b["name"], "r": None, "note": "Periodo comune insufficiente per stimare il legame."})
                continue
            same = (a["favorable"] == "up") == (b["favorable"] == "up")
            significant = res["p"] <= 0.05
            # Gli scenari estremi assumono che le due variabili vadano insieme nella direzione favorevole (o sfavorevole):
            # co-movimento positivo se le direzioni favorevoli coincidono, negativo altrimenti.
            conflict = significant and ((res["r"] > 0) != same)
            row = {"a": a["name"], "b": b["name"], "r": round(res["r"], 3), "p": round(res["p"], 4), "n": res["n"], "freq": res["freq"],
                   "gaps_excluded": res.get("gaps_excluded", 0), "significant": significant, "conflict": conflict}
            if conflict:
                row["note"] = ("In passato si sono mosse in senso opposto a quanto assumono gli scenari ottimistico e avverso: "
                               "è improbabile che i loro estremi si verifichino insieme.")
                warn.append(f"«{a['name']}» e «{b['name']}»: variazioni storicamente correlate (r = {res['r']:+.2f}, n = {res['n']}) "
                            "in senso opposto a quello combinato negli scenari estremi, che quindi sono poco coerenti per questa coppia.")
            else:
                row["note"] = ("Legame storico compatibile con gli scenari estremi." if significant
                               else "Nessun legame statisticamente significativo nel periodo comune.")
            out.append(row)
    return out, warn
