"""Componente D — Anomaly Detection.

Quattro controlli: variazioni anomale, deviazioni dal trend storico, discrepanze tra fonti
sullo stesso indicatore, incongruenze cronologiche. Sotto le soglie minime di dati non
viene segnalato nulla: il conteggio dei casi esclusi è restituito a parte.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..finance import analytics
from ..models import Entity, HistoricalEvent, KnowledgeItem, Relation, Series
from .connections import country_key, fingerprint, series_frame

MIN_CHANGES = 10
MIN_TREND = 20


@dataclass
class AnomalyCandidate:
    kind: str
    title: str
    what_changed: str
    reference: str
    period: str
    data: dict
    alternatives: list[str]
    refs: dict
    relevance: float
    verifiability: str
    keys: list[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.kind, self.keys)


def _year_index(events: list[HistoricalEvent]) -> dict[int, list[tuple[int, HistoricalEvent]]]:
    idx: dict[int, list[tuple[int, HistoricalEvent]]] = {}
    for i, e in enumerate(events):
        idx.setdefault(e.start_year, []).append((i, e))
    return idx


def _events_near(events: list[HistoricalEvent], year: int, country: str, index: dict | None = None) -> list[str]:
    """Eventi entro un anno, nello stesso paese. Con `index` (anno → eventi) non scorre tutto l'archivio."""
    ck = country_key(country) if country else ""
    if index is None:
        pool = list(enumerate(events))
    else:
        pool = sorted((p for y in (year - 1, year, year + 1) for p in index.get(y, ())), key=lambda p: p[0])
    return [e.title for _, e in pool if abs(e.start_year - year) <= 1 and (not ck or ck in {country_key(c) for c in e.countries or []})]


def series_anomalies(series: list[Series], events: list[HistoricalEvent], skipped: dict) -> list[AnomalyCandidate]:
    out = []
    years = _year_index(events)
    for s in series:
        v = series_frame(s)
        if len(v) < MIN_CHANGES + 1:
            skipped["series_too_short"] = skipped.get("series_too_short", 0) + 1
            continue
        d = v.diff().dropna()
        med = float(d.median())
        mad = float((d - med).abs().median() * 1.4826)
        official = s.connector != "upload"
        for a in analytics.anomalies(v, z=4.0):
            year = int(a["date"][:4])
            near = _events_near(events, year, s.country, years)
            alts = ["Revisione o cambio di metodologia della fonte", "Cambio di base o di definizione dell'indicatore",
                    "Errore di trascrizione nei dati (da controllare sulla fonte)"]
            if near:
                alts.insert(0, f"Eventi nel tuo archivio nello stesso periodo: {', '.join(near[:3])}")
            else:
                alts.insert(0, "Un evento reale non ancora registrato nel tuo archivio")
            out.append(AnomalyCandidate(
                kind="series_change", title=f"Variazione anomala in «{s.name}» ({a['date'][:7]})",
                what_changed=f"Variazione di {a['change']:+.4g} {s.unit} rispetto al periodo precedente",
                reference=f"Variazione tipica della serie: mediana {med:+.4g}, dispersione robusta (MAD) {mad:.4g}; z robusto {a['z']:+.1f}",
                period=a["date"], data={"date": a["date"], "change": a["change"], "z": a["z"], "unit": s.unit, "source": s.source_label},
                alternatives=alts, refs={"series_id": s.id}, relevance=min(abs(a["z"]), 20.0),
                verifiability="high" if official else "medium", keys=[f"series:{s.id}", a["date"]],
            ))
        if len(v) >= MIN_TREND:
            hist = v.iloc[:-1]
            x = np.arange(len(hist))
            slope, intercept = np.polyfit(x, hist.values, 1)
            resid = hist.values - (slope * x + intercept)
            sd = resid.std(ddof=2)
            pred = slope * len(hist) + intercept
            last = float(v.iloc[-1])
            if sd > 0 and abs(last - pred) / sd >= 3:
                z = (last - pred) / sd
                out.append(AnomalyCandidate(
                    kind="trend_deviation", title=f"«{s.name}» si discosta dal trend storico",
                    what_changed=f"Ultimo valore {last:.4g} {s.unit} ({v.index[-1].strftime('%Y-%m-%d')})",
                    reference=f"Trend lineare sulle {len(hist)} osservazioni precedenti: atteso {pred:.4g}; scarto di {z:+.1f} deviazioni standard dei residui",
                    period=v.index[-1].strftime("%Y-%m-%d"), data={"last": last, "expected": float(pred), "z": float(z), "n": len(hist)},
                    alternatives=["Il trend lineare può essere un riferimento inadatto (serie non lineare o con rotture strutturali)",
                                  "Cambio di regime reale", "Revisione dell'ultimo dato"],
                    refs={"series_id": s.id}, relevance=min(abs(float(z)), 20.0), verifiability="medium",
                    keys=[f"series:{s.id}", "trend", v.index[-1].strftime("%Y-%m-%d")],
                ))
    return out


def _comparable_units(a: str, b: str) -> bool:
    a, b = (a or "").lower(), (b or "").lower()
    return a == b or ("%" in a and "%" in b)


def source_discrepancies(series: list[Series], skipped: dict, tolerance_abs: float = 0.5, tolerance_rel: float = 0.1) -> list[AnomalyCandidate]:
    """Stesso indicatore (categoria, paese, unità comparabili) da fonti diverse: differenze oltre la tolleranza."""
    out = []
    # Solo coppie dello stesso indicatore (categoria e paese): le altre sono escluse subito qui sotto.
    groups: dict[tuple, list[int]] = {}
    for i, s in enumerate(series):
        if s.category != "other" and s.country:
            groups.setdefault((s.category, country_key(s.country)), []).append(i)
    pairs = sorted(p for idx in groups.values() for p in combinations(idx, 2))
    for i, j in pairs:
        a, b = series[i], series[j]
        if a.category != b.category or a.category == "other" or a.connector == b.connector:
            continue
        if not a.country or not b.country or country_key(a.country) != country_key(b.country) or not _comparable_units(a.unit, b.unit):
            continue
        try:
            target = a.frequency if analytics.FREQ_ORDER[a.frequency] >= analytics.FREQ_ORDER[b.frequency] else b.frequency
            x = analytics.resample(series_frame(a), a.frequency, target, "mean")
            y = analytics.resample(series_frame(b), b.frequency, target, "mean")
        except analytics.AnalysisError:
            continue
        x, y = x.align(y, join="inner")
        both = pd.DataFrame({"a": x, "b": y}).dropna()
        if len(both) < 3:
            skipped["discrepancy_no_overlap"] = skipped.get("discrepancy_no_overlap", 0) + 1
            continue
        diff = (both["a"] - both["b"]).abs()
        tol = np.maximum(tolerance_abs, tolerance_rel * both[["a", "b"]].abs().max(axis=1))
        bad = both[diff > tol]
        if bad.empty:
            continue
        worst = (diff[bad.index]).idxmax()
        out.append(AnomalyCandidate(
            kind="source_discrepancy", title=f"Fonti in disaccordo: «{a.name}» e «{b.name}»",
            what_changed=f"{len(bad)} periodi su {len(both)} differiscono oltre la tolleranza; massimo nel {worst.strftime('%Y-%m')}: "
                         f"{both.loc[worst, 'a']:.4g} contro {both.loc[worst, 'b']:.4g}",
            reference=f"Tolleranza: {tolerance_abs} punti o {int(tolerance_rel * 100)}% del valore; periodi comuni {both.index[0].year}–{both.index[-1].year}",
            period=f"{bad.index[0].strftime('%Y-%m')}–{bad.index[-1].strftime('%Y-%m')}",
            data={"periods": [{"date": d.strftime("%Y-%m-%d"), "a": float(r.a), "b": float(r.b)} for d, r in bad.head(20).iterrows()],
                  "sources": [a.source_label, b.source_label]},
            alternatives=["Definizioni diverse dello stesso fenomeno (es. indice armonizzato e nazionale)",
                          "Revisioni pubblicate in tempi diversi", "Basi o ricampionamenti diversi"],
            refs={"series_ids": [a.id, b.id]}, relevance=float(len(bad)) / len(both) * 10, verifiability="high",
            keys=[f"series:{min(a.id, b.id)}", f"series:{max(a.id, b.id)}"],
        ))
    return out


def chronology_issues(db: Session, events: list[HistoricalEvent], relations: list[Relation], entities: dict[int, Entity]) -> list[AnomalyCandidate]:
    out = []
    first_entity: dict[int, int] = {}
    for x in entities.values():  # come prima: per ogni evento, la prima entità collegata
        if x.event_id is not None:
            first_entity.setdefault(x.event_id, x.id)
    by_entity = {first_entity[ev.id]: ev for ev in events if ev.id in first_entity}
    for e in events:
        if e.end_year is not None and (e.end_year, e.end_month or 12) < (e.start_year, e.start_month or 1):
            out.append(AnomalyCandidate(
                kind="chronology", title=f"«{e.title}»: la fine precede l'inizio",
                what_changed=f"Inizio {e.start_year}, fine {e.end_year}", reference="Un evento non può terminare prima di iniziare",
                period=str(e.start_year), data={}, alternatives=["Errore di inserimento delle date", "Date in calendari diversi"],
                refs={"event_ids": [e.id]}, relevance=8.0, verifiability="high", keys=[f"event:{e.id}", "end_before_start"]))
        for k in e.knowledge or []:
            if k.kind == "contemporary" and k.known_since_year < e.start_year:
                out.append(AnomalyCandidate(
                    kind="chronology", title=f"«{e.title}»: conoscenza «contemporanea» datata prima dell'evento",
                    what_changed=f"Informazione nota dal {k.known_since_year}, evento iniziato nel {e.start_year}",
                    reference="Una conoscenza contemporanea non può precedere l'evento", period=str(k.known_since_year), data={"knowledge_id": k.id},
                    alternatives=["Si tratta di un antefatto, non di conoscenza sull'evento", "Data della conoscenza errata"],
                    refs={"event_ids": [e.id]}, relevance=5.0, verifiability="high", keys=[f"knowledge:{k.id}", "before_event"]))
    for r in relations:
        if r.relation_type not in ("caused", "preceded", "consequence_of"):
            continue
        a, b = by_entity.get(r.source_entity_id), by_entity.get(r.target_entity_id)
        if not a or not b:
            continue
        cause, effect = (b, a) if r.relation_type == "consequence_of" else (a, b)
        if (cause.start_year, cause.start_month or 1) > (effect.start_year, effect.start_month or 12):
            label = {"caused": "causa", "preceded": "precede", "consequence_of": "è conseguenza di"}[r.relation_type]
            out.append(AnomalyCandidate(
                kind="chronology", title=f"Ordine temporale incoerente: «{cause.title}» → «{effect.title}»",
                what_changed=f"La relazione «{label}» collega un evento del {cause.start_year} a uno del {effect.start_year}",
                reference="La causa (o l'evento precedente) deve iniziare prima dell'effetto", period=f"{effect.start_year}–{cause.start_year}",
                data={"relation_id": r.id, "provenance": r.provenance},
                alternatives=["Direzione della relazione invertita", "Date di uno dei due eventi errate", "Tipo di relazione non appropriato"],
                refs={"event_ids": [cause.id, effect.id], "relation_id": r.id}, relevance=9.0, verifiability="high",
                keys=[f"relation:{r.id}", "order"]))
    return out
