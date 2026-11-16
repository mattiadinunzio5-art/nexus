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


def _robustness(db: Session, user: User, c: DiscoveryConnection) -> dict | None:
    """Trend comune, autocorrelazione e confondenti (le altre serie dell'archivio come controlli)."""
    from .stats_checks import robustness, verdict

    ids = [e["id"] for e in c.elements if e["type"] == "series"]
    if len(ids) != 2:
        return None
    a, b = db.get(Series, ids[0]), db.get(Series, ids[1])
    if not a or not b:
        return None
    fa, fb = series_frame(a), series_frame(b)
    try:
        best = lagged_association(fa, fb, a.frequency, b.frequency)
    except Exception:  # noqa: BLE001
        best = None
    lag = best["lag"] if best else 0
    others = list(db.scalars(select(Series).where(Series.owner_id == a.owner_id, Series.id.not_in(ids)).limit(40)))
    controls = []
    for o in others:
        fo = series_frame(o)
        if len(fo) >= 12:
            controls.append((o.name, fo, o.frequency))
        if len(controls) >= 8:
            break
    try:
        rob = robustness(fa, a.frequency, fb, b.frequency, lag=lag, controls=controls)
    except Exception:  # noqa: BLE001 - dati irregolari: il controllo non è possibile, non deve fermare la verifica
        rob = None
    if rob is None:
        return {"check": "Robustezza statistica", "outcome": "insufficient_data", "detail": "Dati insufficienti per i controlli di trend, autocorrelazione e confondenti."}
    outcome, detail = verdict(rob)
    return {"check": "Robustezza statistica", "outcome": outcome, "detail": detail, "statistics": rob}


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
    """Fonti indipendenti collegate agli elementi. Conta come «a favore» solo con almeno due gruppi indipendenti che
    contengono una fonte con identità accertata e autorevolezza almeno media; resta una verifica sulle fonti, non sul
    contenuto: il sostegno dell'affermazione va letto nelle fonti."""
    from ..models import Source

    srcs = [s for i in c.sources if (s := db.get(Source, i))]
    if not srcs:
        return {"check": "Fonti indipendenti", "outcome": "nothing_found", "detail": "Nessuna fonte bibliografica collegata agli elementi."}
    assessed = {a["source_id"]: a for a in (ev.assess_source(s) for s in srcs)}
    usable = [s for s in srcs if not assessed[s.id]["doubtful"]]
    groups, notes = ev.independence(db, usable)
    qualified = sum(1 for g in groups if any(assessed[s.id]["qualified"] for s in g))
    outcome = "supports" if qualified >= 2 else "weak"
    detail = (f"{len(srcs)} fonti in {len(groups)} gruppi indipendenti; {qualified} gruppi con una fonte con identità accertata "
              f"e autorevolezza almeno media" + (f"; {len(srcs) - len(usable)} escluse per identità dubbia" if len(usable) < len(srcs) else "")
              + ". Controllo sulle fonti, non sul contenuto: va letto se sostengono il legame.")
    return {"check": "Fonti indipendenti", "outcome": outcome, "detail": detail, "common_origin": notes[:5]}


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
        causal = [r for r in sourced if r.relation_type in ("caused", "consequence_of")]
        return {"check": "Knowledge Graph", "outcome": "supports", "causal": bool(causal),
                "detail": f"{len(sourced)} relazioni documentate collegano ora i due elementi"
                          + (f", di cui {len(causal)} causali con fonte." if causal else " (nessuna di tipo causale).")}
    return {"check": "Knowledge Graph", "outcome": "nothing_found", "detail": "Nessuna relazione documentata tra i due elementi nel grafo."}


def verify(db: Session, user: User, settings: Settings, c: DiscoveryConnection | None) -> list[dict]:
    if c is None:
        return [{"check": "Connessione di origine", "outcome": "not_possible", "detail": "La connessione da cui nasce l'ipotesi è stata eliminata."}]
    checks = [x for x in (_stability(db, c), _robustness(db, user, c), _documents(db, user, settings, c), _sources(db, c), _graph(db, user, c)) if x]
    return checks


DOCUMENTARY = ("Passaggi nei documenti", "Fonti indipendenti", "Knowledge Graph")


def suggested_outcome(checks: list[dict]) -> str:
    """Suggerimento (non decisione): inconcludente se mancano conferme, respinta se c'è una contraddizione.

    «Confermata» richiede almeno una conferma documentaria (documenti, fonti o relazioni con fonte):
    la sola stabilità statistica di una correlazione non dimostra un meccanismo.
    """
    outs = [c["outcome"] for c in checks]
    if "contradicts" in outs:
        return "rejected"
    if can_confirm(checks):
        return "confirmed"
    return "inconclusive"


def can_confirm(checks: list[dict]) -> bool:
    """Almeno 2 controlli a favore, di cui almeno uno documentario: la sola statistica non basta mai."""
    documentary = any(c["outcome"] == "supports" and c["check"] in DOCUMENTARY for c in checks)
    return sum(1 for c in checks if c["outcome"] == "supports") >= 2 and documentary


# --- Livello dell'evidenza ---------------------------------------------------------------------------

EVIDENCE_LEVELS = {
    "correlation": ("Correlazione", "Due serie si muovono insieme: non dice quale influenzi l'altra, né se esista un legame."),
    "temporal_association": ("Associazione temporale", "Un fatto e una variazione dei dati sono vicini nel tempo: la vicinanza non prova il legame."),
    "association": ("Associazione", "Elementi collegati da attori, citazioni o vicinanza nel grafo: legame da documentare."),
    "hypothesis": ("Ipotesi", "Spiegazione proposta, da verificare con le fonti."),
    "causal": ("Causalità documentata", "Relazione causale sostenuta da fonti verificabili nel Knowledge Graph e confermata dall'utente."),
}
KIND_LEVEL = {"statistical_association": "correlation", "event_data_change": "temporal_association",
              "graph_proximity": "association", "shared_actors": "association", "textual_reference": "association"}


def evidence_level(kind: str | None, status: str, verification: list[dict]) -> dict:
    """Che cosa dimostra davvero l'ipotesi. «Causalità» solo con una relazione causale documentata e una conferma."""
    base = KIND_LEVEL.get(kind or "", "hypothesis")
    last = (verification or [{}])[-1].get("checks", []) if verification else []
    documented_causal = any(c.get("check") == "Knowledge Graph" and c.get("outcome") == "supports" and c.get("causal") for c in last)
    level = "causal" if status == "confirmed" and documented_causal else ("hypothesis" if status == "confirmed" else base)
    label, explanation = EVIDENCE_LEVELS[level]
    return {"level": level, "label": label, "explanation": explanation, "basis": base, "basis_label": EVIDENCE_LEVELS[base][0]}
