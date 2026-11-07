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

from ..core.errors import NotFoundError, ValidationFailedError
from ..models import DiscoveryAnomaly, DiscoveryHypothesis, Entity, Relation, Series, User
from .connections import series_frame

PPY = {"A": 1, "Q": 4, "M": 12, "W": 52, "D": 252}
MIN_OBS = 20


def bootstrap_changes(values: np.ndarray, n_steps: int, n_paths: int = 2000, block: int = 3, seed: int = 7) -> np.ndarray:
    d = np.diff(values)
    rng = np.random.default_rng(seed)
    block = max(1, min(block, len(d)))
    out = np.empty((n_paths, n_steps))
    for k in range(n_paths):
        buf: list[float] = []
        while len(buf) < n_steps:
            s = rng.integers(0, len(d) - block + 1)
            buf.extend(d[s:s + block])
        out[k] = buf[:n_steps]
    return values[-1] + np.cumsum(out, axis=1)


def scenarios(db: Session, user: User, variables: list[dict], horizon_years: float, triggers: list[str] | None = None) -> dict:
    if not 1 <= len(variables) <= 6:
        raise ValidationFailedError("Scegli da 1 a 6 variabili.")
    if not 0.25 <= horizon_years <= 10:
        raise ValidationFailedError("Orizzonte tra 3 mesi e 10 anni.")
    rows, excluded = [], []
    for var in variables:
        s = db.get(Series, var["series_id"])
        if s is None or s.owner_id != user.id:
            raise NotFoundError(f"Serie {var['series_id']} non trovata.")
        v = series_frame(s)
        if len(v) < MIN_OBS:
            excluded.append(f"«{s.name}»: {len(v)} osservazioni, ne servono almeno {MIN_OBS}.")
            continue
        ppy = PPY.get(s.frequency, 12)
        n = max(1, int(round(horizon_years * ppy)))
        paths = bootstrap_changes(v.values.astype(float), n)
        final = paths[:, -1]
        p10, p50, p90 = (float(np.percentile(final, q)) for q in (10, 50, 90))
        up_good = var.get("favorable", "up") == "up"
        fan = [{"step": i + 1, "p10": float(np.percentile(paths[:, i], 10)), "p50": float(np.percentile(paths[:, i], 50)),
                "p90": float(np.percentile(paths[:, i], 90))} for i in range(0, n, max(1, n // 24))]
        rows.append({"series_id": s.id, "name": s.name, "unit": s.unit, "frequency": s.frequency, "favorable": "up" if up_good else "down",
                     "initial": {"date": v.index[-1].strftime("%Y-%m-%d"), "value": float(v.iloc[-1])},
                     "history": {"n": len(v), "from": v.index[0].strftime("%Y-%m-%d"), "to": v.index[-1].strftime("%Y-%m-%d")},
                     "optimistic": p90 if up_good else p10, "central": p50, "adverse": p10 if up_good else p90, "fan": fan,
                     "source": s.source_label})
    if not rows:
        raise ValidationFailedError("Nessuna variabile ha dati sufficienti. " + " ".join(excluded))
    ids = [r["series_id"] for r in rows]
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
    ent = {e.series_id: e for e in db.scalars(select(Entity).where(Entity.owner_id == user.id, Entity.series_id.in_(ids)))}
    for sid, e in ent.items():
        for r in db.scalars(select(Relation).where(Relation.owner_id == user.id, Relation.source_entity_id == e.id,
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
        "uncertainties": [
            "Il modello ricampiona variazioni già osservate: non può produrre shock più grandi di quelli presenti nella storia della serie.",
            "Le variabili sono simulate separatamente: le relazioni tra di loro non sono modellate, quindi gli estremi possono non verificarsi insieme.",
            "Cambi strutturali successivi al campione non sono considerati.",
            "I dati sono la versione attuale delle serie (possibili revisioni).",
        ],
        "method": "Bootstrap a blocchi (3 periodi) delle variazioni storiche, 2000 traiettorie, seme fisso 7 (risultati riproducibili).",
        "probability_note": "Le bande corrispondono ai percentili 10/50/90 del modello; agli scenari non sono attribuite altre probabilità.",
    }
