"""Componente E — Causal Intelligence.

1) Catene nel Knowledge Graph tra due entità, con ogni anello classificato:
   - «causale documentata»: relazione causale (causato, conseguenza di) con fonte;
   - «causale ipotizzata»: relazione causale dichiarata come ipotesi;
   - «influenza documentata / ipotizzata»: relazione «ha influenzato»;
   - «associazione»: legame non causale (contemporaneo, correlato, precedente…).
   La forza della catena è quella dell'anello più debole. Per ogni effetto si elencano le
   altre cause note (spiegazioni alternative) e le cause comuni ai due estremi (confondenti).
2) Catene di trasmissione tra serie (es. tassi → credito → investimenti → PIL → disoccupazione):
   per ogni passaggio la correlazione ritardata delle variazioni, classificata come
   correlazione, salvo relazioni documentate nel grafo tra gli indicatori.
"""

from __future__ import annotations

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core import library
from ..core.errors import NotFoundError, ValidationFailedError
from ..models import Entity, Relation, Series, Source, User
from ..research.citations import format_citation
from .connections import lagged_association, series_frame

CAUSAL = {"caused", "consequence_of"}
INFLUENCE = {"influenced", "financed"}
LINK_RANK = {"causal_documented": 4, "influence_documented": 3, "causal_hypothesized": 2, "influence_hypothesized": 1, "association": 0}
LINK_LABEL = {
    "causal_documented": "Relazione causale documentata",
    "influence_documented": "Influenza documentata",
    "causal_hypothesized": "Relazione causale ipotizzata",
    "influence_hypothesized": "Influenza ipotizzata",
    "association": "Associazione (non causale)",
    "correlation": "Correlazione statistica",
}


def classify(r: Relation) -> str:
    sourced = r.provenance == "sourced"
    if r.relation_type in CAUSAL:
        return "causal_documented" if sourced else "causal_hypothesized"
    if r.relation_type in INFLUENCE:
        return "influence_documented" if sourced else "influence_hypothesized"
    return "association"


def _directed(r: Relation) -> tuple[int, int]:
    """Direzione causa → effetto (consequence_of è espressa al contrario)."""
    return (r.target_entity_id, r.source_entity_id) if r.relation_type == "consequence_of" else (r.source_entity_id, r.target_entity_id)


def _evidence(db: Session, r: Relation) -> str:
    if r.source_id and (s := db.get(Source, r.source_id)):
        return format_citation(s)
    return r.evidence_note or {"user_hypothesis": "Ipotesi dell'utente", "ai_hypothesis": "Ipotesi generata dall'AI"}.get(r.provenance, "")


def chains(db: Session, user: User, start: int, end: int, max_depth: int = 5, limit: int = 12) -> dict:
    """Catene tra due entità leggibili dall'utente (proprie o della Biblioteca NEXUS), sul grafo proprio + Biblioteca.

    Mai dati di altri utenti. Le relazioni si caricano come tuple leggere e la ricerca dei percorsi si limita ai nodi
    raggiungibili da «start» e che raggiungono «end» entro la profondità indicata (il grafo della Biblioteca è grande).
    """
    owners = library.visible_owner_ids(db, user)
    for eid in (start, end):
        e = db.get(Entity, eid)
        if e is None or e.owner_id not in owners:
            raise NotFoundError("Entità non trovata.")
    if start == end:
        raise ValidationFailedError("Scegli due entità diverse.")
    rows = db.execute(select(Relation.id, Relation.source_entity_id, Relation.target_entity_id, Relation.relation_type, Relation.provenance)
                      .where(Relation.owner_id.in_(owners), Relation.relation_type.not_in(("contemporary_of", "related_to", "opposed_to")))).all()
    g = nx.MultiDiGraph()
    for r in rows:
        u, v = _directed(r)  # simmetriche o non orientate escluse: non possono costruire una catena causa → effetto
        g.add_edge(u, v, key=r.id, rel=r)
    names: dict[int, str] = {}

    def name(eid: int) -> str:
        if eid not in names:
            e = db.get(Entity, eid)
            names[eid] = e.name if e else "?"
        return names[eid]

    paths = []
    if start in g and end in g:
        fwd = nx.single_source_shortest_path_length(g, start, cutoff=max_depth)
        back = nx.single_source_shortest_path_length(g.reverse(copy=False), end, cutoff=max_depth)
        keep = {n for n in fwd if n in back and fwd[n] + back[n] <= max_depth}
        sub = nx.DiGraph(g.subgraph(keep))
        if start in sub and end in sub:
            for nodes in nx.all_simple_paths(sub, start, end, cutoff=max_depth):
                links = []
                for u, v in zip(nodes, nodes[1:]):
                    best = max(g.get_edge_data(u, v).values(), key=lambda d: LINK_RANK[classify(d["rel"])])["rel"]
                    k = classify(best)
                    alternatives = [name(x) for x, _, d in g.in_edges(v, data=True) if x != u and classify(d["rel"]) != "association"][:20]
                    links.append({"from": name(u), "to": name(v), "relation_type": best.relation_type, "class": k,
                                  "label": LINK_LABEL[k], "evidence": _evidence(db, db.get(Relation, best.id)), "relation_id": best.id,
                                  "alternatives": sorted(set(alternatives))[:5]})
                weakest = min(links, key=lambda x: LINK_RANK[x["class"]])
                paths.append({"nodes": [name(n) for n in nodes], "entity_ids": nodes, "links": links,
                              "strength": weakest["class"], "strength_label": LINK_LABEL[weakest["class"]]})
                if len(paths) >= 50:
                    break
    paths.sort(key=lambda p: (-LINK_RANK[p["strength"]], len(p["nodes"])))
    paths = paths[:limit]
    common = []
    if start in g and end in g:
        both = nx.ancestors(g, start) & nx.ancestors(g, end)
        common = sorted(name(x) for x in list(both)[:200])
    notes = []
    if not paths:
        notes.append("Nessuna catena orientata collega le due entità nel grafo: mancano relazioni, oppure i collegamenti sono solo associazioni.")
    if any(p["strength"] != "causal_documented" for p in paths):
        notes.append("Le catene che contengono anelli ipotizzati o associazioni non dimostrano un rapporto causale.")
    return {"start": name(start), "end": name(end), "paths": paths, "common_causes": common[:10], "notes": notes}


# --- Catene di trasmissione tra serie -----------------------------------------------------------

TEMPLATES = [
    {
        "id": "monetary_transmission_us",
        "title": "Trasmissione della politica monetaria (Stati Uniti)",
        "steps": [
            {"label": "Tassi d'interesse di policy", "connector": "fred", "series_id": "FEDFUNDS"},
            {"label": "Costo del credito alle imprese", "connector": "fred", "series_id": "BAA"},
            {"label": "Investimenti privati", "connector": "fred", "series_id": "GPDI"},
            {"label": "PIL reale", "connector": "fred", "series_id": "GDPC1"},
            {"label": "Disoccupazione", "connector": "fred", "series_id": "UNRATE"},
        ],
    },
]


def transmission(db: Session, user: User, series_ids: list[int], labels: list[str] | None = None, max_lag: int = 4) -> dict:
    if len(series_ids) < 2 or len(series_ids) > 8:
        raise ValidationFailedError("Indica da 2 a 8 serie, nell'ordine della catena.")
    owners = library.visible_owner_ids(db, user)  # serie proprie o della Biblioteca NEXUS (sola lettura), mai di altri utenti
    series = []
    for sid in series_ids:
        s = db.get(Series, sid)
        if s is None or s.owner_id not in owners:
            raise NotFoundError(f"Serie {sid} non trovata.")
        series.append(s)
    ent_of = {e.series_id: e.id for e in db.scalars(select(Entity).where(Entity.owner_id.in_(owners), Entity.series_id.in_(series_ids)))}
    steps = []
    for i, (a, b) in enumerate(zip(series, series[1:])):
        fa, fb = series_frame(a), series_frame(b)
        res = lagged_association(fa, fb, a.frequency, b.frequency, max_lag=max_lag) if len(fa) >= 12 and len(fb) >= 12 else None
        documented = None
        if a.id in ent_of and b.id in ent_of:
            documented = db.scalar(select(Relation).where(
                Relation.owner_id.in_(owners), Relation.provenance == "sourced", Relation.relation_type.in_(CAUSAL | INFLUENCE),
                Relation.source_entity_id == ent_of[a.id], Relation.target_entity_id == ent_of[b.id]))
        if documented:
            cls = "causal_documented" if documented.relation_type in CAUSAL else "influence_documented"
        else:
            cls = "correlation"
        step = {"from": (labels[i] if labels and i < len(labels) else a.name), "to": (labels[i + 1] if labels and i + 1 < len(labels) else b.name),
                "from_series": a.id, "to_series": b.id, "class": cls, "label": LINK_LABEL[cls],
                "evidence": _evidence(db, documented) if documented else None, "statistic": None, "uncertainty": "",
                "variables": [f"{a.name} ({a.unit})", f"{b.name} ({b.unit})"],
                "alternatives": ["Fattori comuni che muovono entrambe le variabili (es. ciclo economico, shock esterni)",
                                 "Causalità inversa", "Effetti con ritardi più lunghi di quelli provati"]}
        if res is None:
            step["uncertainty"] = "Dati insufficienti per stimare la relazione (servono almeno 12 osservazioni comuni)."
        else:
            step["statistic"] = res
            expected = res["lag"] >= 0
            sig = res["p_adj"] <= 0.05
            step["uncertainty"] = ("Associazione statisticamente significativa" if sig else "Associazione NON significativa") + \
                (f"; il primo anello anticipa il secondo di {res['lag']} periodi" if res["lag"] > 0 else
                 "; nessun anticipo" if res["lag"] == 0 else f"; attenzione: è il secondo ad anticipare il primo ({-res['lag']} periodi)") + \
                ("" if expected else " — direzione temporale opposta a quella della catena")
        steps.append(step)
    return {"steps": steps, "notes": ["Ogni passaggio senza relazione documentata nel grafo è una correlazione, non una prova causale.",
                                      "Correlazioni calcolate sulle variazioni, alla frequenza comune più bassa, con p-value corretti per i ritardi provati."]}
