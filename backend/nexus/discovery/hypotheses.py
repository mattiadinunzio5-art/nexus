"""Componente C — Hypothesis Generator.

Da ogni connessione nasce un'ipotesi strutturata: motivazione, evidenze a favore e contro,
informazioni mancanti, metodo di verifica, confidenza. La confidenza non è mai «alta»
per un'ipotesi generata: al massimo «media». La verifica automatica raccoglie elementi
(stabilità statistica, passaggi nei documenti, fonti indipendenti) ma non decide: lo stato
finale (confermata / respinta / inconcludente) lo sceglie l'utente.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..models import DiscoveryConnection, Entity, HistoricalEvent, Relation, Series, User
from . import evidence as ev
from .connections import lagged_association, series_frame

DISCLAIMER = "Ipotesi generata da NEXUS a partire dai dati del tuo archivio: non è una scoperta dimostrata."


def _labels(c: DiscoveryConnection) -> list[str]:
    return [e["label"] for e in c.elements]


def from_connection(db: Session, c: DiscoveryConnection) -> dict:
    a, b = (_labels(c) + ["", ""])[:2]
    supporting = [f"{x['label']}: {x['detail']}" for x in c.evidence]
    contrary: list[str] = []
    missing: list[str] = []
    method: list[str] = []
    if c.kind == "statistical_association":
        title = f"Le variazioni di «{a}» e «{b}» sono legate da un meccanismo economico"
        desc = c.explanation
        contrary.append("Una correlazione sulle variazioni può nascere da un fattore comune non osservato.")
        missing += ["Un meccanismo economico documentato in letteratura", "Una verifica su sottoperiodi e su altri paesi"]
        method += ["Verifica automatica: stabilità della correlazione nelle due metà del campione",
                   "Economic Laboratory: regressione con variabili di controllo e ritardi",
                   "Bibliografia: cercare studi che descrivano il canale di trasmissione"]
    elif c.kind == "event_data_change":
        title = f"«{a}» ha contribuito alla variazione osservata in «{b}»"
        desc = c.explanation
        similar = next((x["detail"] for x in c.evidence if x["label"].startswith("Variazioni altrettanto")), "")
        if similar:
            contrary.append(f"Variazioni simili si sono verificate anche in altri momenti ({similar}).")
        missing += ["Una serie di confronto (un altro paese o settore non toccato dall'evento)", "Fonti che documentino il canale d'impatto"]
        method += ["Confrontare con una serie di controllo nello stesso periodo", "Time Machine: cosa si sapeva prima e dopo l'evento",
                   "Verifica automatica: passaggi nei documenti che citano l'evento e l'indicatore"]
    elif c.kind == "graph_proximity":
        title = f"Esiste un legame diretto tra «{a}» e «{b}»"
        desc = c.explanation
        missing += ["Una fonte che colleghi direttamente i due elementi"]
        method += ["Verifica automatica: passaggi nei documenti che citano entrambi", "Knowledge Graph: aggiungere la relazione con la sua fonte se trovata"]
    else:  # shared_actors, textual_reference
        title = f"«{a}» e «{b}» sono collegati" + (" da una relazione di influenza" if c.kind == "textual_reference" else " attraverso gli stessi attori")
        desc = c.explanation
        missing += ["Una fonte che documenti esplicitamente il collegamento", "Conoscenze datate (cosa si sapeva all'epoca)"]
        method += ["Verifica automatica: passaggi nei documenti che citano entrambi gli eventi",
                   "Controllare l'ordine cronologico e la fonte di ciascun evento", "Historical Intelligence: aggiungere fonti verificate agli eventi"]
    if c.reliability == "low":
        contrary.append("Le evidenze disponibili hanno affidabilità bassa: " + "; ".join(c.reliability_reasons[:3]))
    contrary += [x for x in c.caveats if "causa" not in x.lower()]
    confidence = "medium" if c.reliability in ("medium", "high") and len(c.evidence) >= 2 else "low"
    return {"title": title[:500], "description": f"{desc}\n\n{DISCLAIMER}", "phenomena": _labels(c),
            "motivation": f"Connessione «{c.title}» individuata dal Discovery Engine ({c.kind}).",
            "supporting": supporting, "contrary": contrary, "missing": missing, "method": method, "confidence": confidence}


# --- Verifica ---------------------------------------------------------------------------------------


def _stability(db: Session, c: DiscoveryConnection) -> dict | None:
    ids = [e["id"] for e in c.elements if e["type"] == "series"]
    if len(ids) != 2:
        return None
    a, b = db.get(Series, ids[0]), db.get(Series, ids[1])
    if not a or not b:
        return {"check": "Stabilità nei sottoperiodi", "outcome": "not_possible", "detail": "Una delle serie è stata eliminata."}
    fa, fb = series_frame(a), series_frame(b)
    start, end = max(fa.index[0], fb.index[0]), min(fa.index[-1], fb.index[-1])
    mid = start + (end - start) / 2
    halves = []
    for lo, hi in ((start, mid), (mid, end)):
        r = lagged_association(fa[(fa.index >= lo) & (fa.index <= hi)], fb[(fb.index >= lo) & (fb.index <= hi)], a.frequency, b.frequency)
        halves.append(r)
    if any(h is None for h in halves):
        return {"check": "Stabilità nei sottoperiodi", "outcome": "insufficient_data", "detail": "Troppe poche osservazioni in una metà del campione."}
    same_sign = (halves[0]["r"] > 0) == (halves[1]["r"] > 0)
    strong = all(abs(h["r"]) >= 0.4 for h in halves)
    outcome = "supports" if same_sign and strong else "contradicts" if not same_sign else "weak"
    return {"check": "Stabilità nei sottoperiodi", "outcome": outcome,
            "detail": f"Prima metà: r = {halves[0]['r']:+.2f} (n = {halves[0]['n']}, ritardo {halves[0]['lag']}); "
                      f"seconda metà: r = {halves[1]['r']:+.2f} (n = {halves[1]['n']}, ritardo {halves[1]['lag']})."}


def _element_names(db: Session, c: DiscoveryConnection) -> list[list[str]]:
    names = []
    for e in c.elements:
        if e["type"] == "event" and (x := db.get(HistoricalEvent, e["id"])):
            names.append([x.title])
        elif e["type"] == "entity" and (x := db.get(Entity, e["id"])):
            names.append([x.name, *(x.aliases or [])])
        elif e["type"] == "series" and (x := db.get(Series, e["id"])):
            names.append([x.name.split(" — ")[0].split(",")[0]])
        else:
            names.append([e["label"]])
    return names


def _documents(db: Session, user: User, settings: Settings, c: DiscoveryConnection) -> dict:
    from ..research.text import terms
    from ..services import research

    names = _element_names(db, c)
    query = " ".join(n[0] for n in names)
    passages, _ = research.retrieve(db, user, settings, query, "text", 20, None)
    keys = [[set(terms(n)) for n in group] for group in names]
    both = []
    for p in passages:
        pt = set(terms(p.text))
        if all(any(k and len(k & pt) >= max(1, int(len(k) * 0.6)) for k in group) for group in keys):
            both.append({"label": f"{p.document_title}, {p.locator}".strip(", "), "text": p.text[:400], "chunk_id": p.chunk_id,
                         "document_id": p.document_id})
    if not both:
        return {"check": "Passaggi nei documenti", "outcome": "nothing_found",
                "detail": "Nessun passaggio dell'archivio cita insieme gli elementi dell'ipotesi."}
    docs = {b["document_id"] for b in both}
    return {"check": "Passaggi nei documenti", "outcome": "supports",
            "detail": f"{len(both)} passaggi in {len(docs)} documenti citano insieme gli elementi (da leggere: la co-occorrenza non conferma il legame).",
            "passages": both[:6]}


def _sources(db: Session, c: DiscoveryConnection) -> dict:
    from ..models import Source

    srcs = [s for i in c.sources if (s := db.get(Source, i))]
    if not srcs:
        return {"check": "Fonti indipendenti", "outcome": "nothing_found", "detail": "Nessuna fonte bibliografica collegata agli elementi."}
    groups = ev.independent_groups(db, srcs)
    verified = sum(1 for s in srcs if s.verification_status in ev.VERIFIED)
    outcome = "supports" if len(groups) >= 2 and verified >= 2 else "weak"
    return {"check": "Fonti indipendenti", "outcome": outcome,
            "detail": f"{len(srcs)} fonti in {len(groups)} gruppi indipendenti; {verified} verificate."}


def _graph(db: Session, user: User, c: DiscoveryConnection) -> dict | None:
    ents = []
    for e in c.elements:
        if e["type"] == "event":
            ents.append(db.scalar(select(Entity.id).where(Entity.event_id == e["id"])))
        elif e["type"] == "entity":
            ents.append(e["id"])
        elif e["type"] == "series":
            ents.append(db.scalar(select(Entity.id).where(Entity.series_id == e["id"])))
    if len(ents) != 2 or None in ents:
        return None
    rels = list(db.scalars(select(Relation).where(Relation.owner_id == user.id, Relation.source_entity_id.in_(ents), Relation.target_entity_id.in_(ents))))
    sourced = [r for r in rels if r.provenance == "sourced"]
    if sourced:
        return {"check": "Knowledge Graph", "outcome": "supports", "detail": f"{len(sourced)} relazioni documentate collegano ora i due elementi."}
    return {"check": "Knowledge Graph", "outcome": "nothing_found", "detail": "Nessuna relazione documentata tra i due elementi nel grafo."}


def verify(db: Session, user: User, settings: Settings, c: DiscoveryConnection | None) -> list[dict]:
    if c is None:
        return [{"check": "Connessione di origine", "outcome": "not_possible", "detail": "La connessione da cui nasce l'ipotesi è stata eliminata."}]
    checks = [x for x in (_stability(db, c), _documents(db, user, settings, c), _sources(db, c), _graph(db, user, c)) if x]
    return checks


def suggested_outcome(checks: list[dict]) -> str:
    """Suggerimento (non decisione): inconcludente se mancano conferme, respinta se c'è una contraddizione."""
    outs = [c["outcome"] for c in checks]
    if "contradicts" in outs:
        return "rejected"
    if outs.count("supports") >= 2:
        return "confirmed"
    return "inconclusive"
