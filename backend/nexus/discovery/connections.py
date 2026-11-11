"""Componente B — Discovery Engine.

Cinque rilevatori deterministici, ognuno con un tipo di relazione esplicito. Nessuno
dichiara una causalità: una coincidenza temporale resta una coincidenza, una correlazione
resta una correlazione. Ogni connessione porta elementi, periodo, evidenze, fonti,
affidabilità motivata e una spiegazione con le sue cautele.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..finance import analytics
from ..models import Entity, HistoricalEvent, Relation, Series, Source, User
from ..research.text import terms
from . import evidence as ev
from .kg import norm

KIND_LABEL = {
    "shared_actors": "Attori condivisi",
    "textual_reference": "Riferimento testuale",
    "graph_proximity": "Vicinanza nel grafo",
    "event_data_change": "Coincidenza evento–dati",
    "statistical_association": "Associazione statistica",
}
NOT_CAUSAL = "La connessione non dimostra un rapporto di causa-effetto: va verificata."

COUNTRY_ALIASES = {
    "italy": "it", "italia": "it", "ita": "it", "it": "it", "germany": "de", "germania": "de", "deu": "de", "de": "de",
    "france": "fr", "francia": "fr", "fra": "fr", "fr": "fr", "spain": "es", "spagna": "es", "esp": "es", "es": "es",
    "united states": "us", "stati uniti": "us", "usa": "us", "us": "us", "united kingdom": "gb", "regno unito": "gb",
    "gbr": "gb", "uk": "gb", "gb": "gb", "japan": "jp", "giappone": "jp", "jpn": "jp", "jp": "jp", "china": "cn",
    "cina": "cn", "chn": "cn", "cn": "cn", "euro area": "u2", "area euro": "u2", "eurozona": "u2", "u2": "u2", "ea": "u2",
}


def country_key(c: str) -> str:
    k = norm(c)
    return COUNTRY_ALIASES.get(k, k)


def fingerprint(kind: str, keys: list[str]) -> str:
    return hashlib.sha256(f"{kind}|{'|'.join(sorted(keys))}".encode()).hexdigest()


@dataclass
class Candidate:
    kind: str
    title: str
    elements: list[dict]
    period: str
    evidence: list[dict]
    source_ids: list[int]
    explanation: str
    caveats: list[str]
    score: float
    reliability: str = "low"
    reliability_reasons: list[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.kind, [f"{e['type']}:{e['id']}" for e in self.elements])


def event_year(e: HistoricalEvent) -> float:
    return e.start_year + ((e.start_month or 1) - 1) / 12


def event_span(e: HistoricalEvent) -> tuple[int, int]:
    return e.start_year, e.end_year if e.end_year is not None else e.start_year


def fmt_years(a: int, b: int) -> str:
    def y(v: int) -> str:
        return f"{-v} a.C." if v < 0 else str(v)
    return y(a) if a == b else f"{y(a)}–{y(b)}"


def _event_el(e: HistoricalEvent) -> dict:
    return {"type": "event", "id": e.id, "label": e.title}


def _event_sources(db: Session, e: HistoricalEvent, cache: dict | None = None) -> list[Source]:
    if cache is not None and e.id in cache:
        return cache[e.id]
    out = [s for link in e.source_links if (s := db.get(Source, link.source_id))]
    if cache is not None:
        cache[e.id] = out
    return out


def _grade_events(db: Session, evs: list[HistoricalEvent], cache: dict | None = None) -> tuple[str, list[str], list[int]]:
    sources = {s.id: s for e in evs for s in _event_sources(db, e, cache)}
    level, reasons, _ = ev.grade(db, list(sources.values()))
    disputed = [e.title for e in evs if e.reliability in ("disputed", "unverified")]
    if disputed:
        reasons.append(f"Affidabilità dichiarata bassa o contestata: {', '.join(disputed)}")
        level = "low" if level != "high" else "medium"
    return level, reasons, list(sources)


# --- 1–2. Eventi: attori condivisi e riferimenti testuali ---------------------------------------


def _actors(e: HistoricalEvent) -> dict[str, str]:
    return {norm(x): x for x in [*(e.people or []), *(e.institutions or [])] if norm(x)}


def _mentions(text: str, title: str) -> bool:
    """Il testo cita l'evento: titolo intero oppure almeno l'80% dei suoi termini (minimo 2)."""
    if not text or not title:
        return False
    if norm(title) and norm(title) in norm(text):
        return True
    tt = set(terms(title))
    return len(tt) >= 2 and len(tt & set(terms(text))) / len(tt) >= 0.8


# Oltre queste dimensioni il confronto «tutti con tutti» non è praticabile (la Biblioteca NEXUS ha decine di migliaia di
# eventi ed entità): si confrontano solo le coppie che possono dare un risultato, trovate con indici. Sotto la soglia resta
# il confronto completo, identico a prima.
EXACT_MAX_EVENTS = 1500
EXACT_MAX_NODES = 2000
MAX_ACTOR_EVENTS = 200   # in un archivio grande, un attore presente in più eventi di così è «comune» e non distingue nulla
MAX_HUB_DEGREE = 300     # nodi del grafo con più collegamenti di così non generano coppie candidate (restano nel punteggio)
KEEP = 500               # candidati conservati per rilevatore (il salvataggio ne tiene comunque al massimo `max_items`)


def _event_pair(db: Session, a: HistoricalEvent, b: HistoricalEvent, common_actors: set[str], grade) -> Candidate | None:
    """Confronta due eventi (a precede b nell'ordine dell'archivio). `grade` calcola l'affidabilità quando serve."""
    first, second = (a, b) if event_year(a) <= event_year(b) else (b, a)
    s1, e1 = event_span(first)
    s2, e2 = event_span(second)
    gap = max(0, s2 - e1)
    period = fmt_years(min(s1, s2), max(e1, e2))
    # Riferimento testuale: cause/descrizione del secondo citano il primo.
    later_text = " ".join([second.causes, second.description, second.economic_implications])
    if _mentions(later_text, first.title):
        level, reasons, src_ids = grade(a, b)
        return Candidate(
            kind="textual_reference", title=f"«{second.title}» richiama «{first.title}»",
            elements=[_event_el(first), _event_el(second)], period=period,
            evidence=[{"kind": "text", "label": f"Scheda «{second.title}»: cause e descrizione", "detail": "Il testo cita l'evento precedente.", "ref": {"event_id": second.id}}],
            source_ids=src_ids, score=3.0 + (1 if gap <= 10 else 0),
            explanation=(f"La scheda di «{second.title}» menziona «{first.title}» tra cause o contesto, e il primo evento precede il secondo"
                         f"{' di ' + str(gap) + ' anni' if gap else ''}. È un collegamento dichiarato nel tuo archivio, non ancora una relazione documentata da una fonte."),
            caveats=[NOT_CAUSAL, "Il riferimento proviene dal testo inserito nell'archivio: va confermato con una fonte."],
            reliability=level, reliability_reasons=reasons,
        )
    shared = {k: v for k, v in _actors(a).items() if k in _actors(b) and k not in common_actors}
    if not (shared and gap <= 30):
        return None
    ca = {country_key(c) for c in a.countries or []}
    cb = {country_key(c) for c in b.countries or []}
    countries = ca & cb
    cats = set(a.categories or []) & set(b.categories or [])
    names = sorted(shared.values())
    level, reasons, src_ids = grade(a, b)
    return Candidate(
        kind="shared_actors", title=f"{first.title} ↔ {second.title}",
        elements=[_event_el(first), _event_el(second)], period=period,
        evidence=[{"kind": "actors", "label": "Attori comuni", "detail": ", ".join(names)},
                  *([{"kind": "context", "label": "Paesi comuni", "detail": ", ".join(sorted(countries))}] if countries else []),
                  *([{"kind": "context", "label": "Categorie comuni", "detail": ", ".join(sorted(cats))}] if cats else [])],
        source_ids=src_ids, score=2.0 * len(shared) + 0.5 * len(countries) + 0.25 * len(cats) + (1 if gap <= 5 else 0),
        explanation=(f"Gli stessi attori ({', '.join(names)}) compaiono in entrambi gli eventi, a {gap} anni di distanza. "
                     "Gli attori condivisi suggeriscono una possibile continuità di decisioni o interessi."),
        caveats=[NOT_CAUSAL, "Lo stesso attore può partecipare a eventi indipendenti."],
        reliability=level, reliability_reasons=reasons,
    )


def _candidate_event_pairs(events: list[HistoricalEvent], common_actors: set[str]) -> list[tuple[int, int]]:
    """Coppie (i, j), i < j, che possono dare un risultato: attore non comune condiviso, oppure il testo dell'uno contiene
    abbastanza termini del titolo dell'altro. Per il titolo basta indicizzare i suoi m+1 termini più rari, dove m è il
    numero di termini che possono mancare restando sopra l'80%: almeno uno di essi compare per forza nel testo."""
    pairs: set[tuple[int, int]] = set()
    by_actor: dict[str, list[int]] = {}
    for i, e in enumerate(events):
        for k in _actors(e):
            if k not in common_actors:
                by_actor.setdefault(k, []).append(i)
    for idx in by_actor.values():
        pairs.update(combinations(idx, 2))
    title_terms = [set(terms(e.title)) for e in events]
    df: dict[str, int] = {}
    for tt in title_terms:
        for w in tt:
            df[w] = df.get(w, 0) + 1
    by_term: dict[str, list[int]] = {}
    for i, tt in enumerate(title_terms):
        if not tt:
            continue
        missing = len(tt) - math.ceil(0.8 * len(tt) - 1e-9)
        for w in sorted(tt, key=lambda x: (df[x], x))[:missing + 1]:
            by_term.setdefault(w, []).append(i)
    for j, e in enumerate(events):
        text_terms = set(terms(" ".join([e.causes, e.description, e.economic_implications])))
        hits = {i for w in text_terms for i in by_term.get(w, ()) if i != j}
        for i in hits:  # stesso criterio di _mentions (titolo intero, oppure almeno 2 termini e l'80% presente)
            tt = title_terms[i]
            if len(tt & text_terms) / len(tt) >= 0.8:
                pairs.add((min(i, j), max(i, j)))
    return sorted(pairs)


def event_connections(db: Session, events: list[HistoricalEvent], known_pairs: set[frozenset]) -> list[Candidate]:
    out: list[Candidate] = []
    # Un attore presente in quasi tutti gli eventi (es. la banca centrale di riferimento) non distingue nulla:
    # come nella ricerca testuale, gli attori troppo frequenti non contano.
    df: dict[str, int] = {}
    for e in events:
        for k in _actors(e):
            df[k] = df.get(k, 0) + 1
    common_actors = {k for k, n in df.items() if len(events) >= 4 and n > max(2, len(events) // 2)}
    large = len(events) > EXACT_MAX_EVENTS
    if large:
        common_actors |= {k for k, n in df.items() if n > MAX_ACTOR_EVENTS}
        pairs = ((events[i], events[j]) for i, j in _candidate_event_pairs(events, common_actors))
    else:
        pairs = combinations(events, 2)
    cache: dict[int, list[Source]] = {}

    def grade(a: HistoricalEvent, b: HistoricalEvent):
        if large:
            return "low", [], []  # calcolata dopo, solo per i candidati conservati
        return _grade_events(db, [a, b])

    kept: list[tuple[Candidate, HistoricalEvent, HistoricalEvent]] = []
    for a, b in pairs:
        if frozenset((("event", a.id), ("event", b.id))) in known_pairs:
            continue  # già collegati nel grafo: non è una scoperta
        c = _event_pair(db, a, b, common_actors, grade)
        if c:
            kept.append((c, a, b))
    if large:
        kept = sorted(kept, key=lambda x: -x[0].score)[:KEEP]
        for c, a, b in kept:
            c.reliability, c.reliability_reasons, c.source_ids = _grade_events(db, [a, b], cache)
    out = [c for c, _, _ in kept]
    return out


# --- 3. Grafo: entità non collegate con vicini comuni ---------------------------------------------


def graph_connections(db: Session, user: User, entities: dict[int, Entity], rels: list[Relation], scope_ids: set[int] | None,
                      limit: int = 30) -> list[Candidate]:
    g = nx.Graph()
    for r in rels:
        g.add_edge(r.source_entity_id, r.target_entity_id)
    if g.number_of_nodes() < 3:
        return []
    nodes = [n for n in g.nodes if scope_ids is None or n in scope_ids]
    if len(nodes) <= EXACT_MAX_NODES:
        pairs = [(u, v) for u, v in combinations(nodes, 2) if not g.has_edge(u, v)]
    else:
        # Solo coppie con almeno 2 vicini comuni (le altre non superano il filtro qui sotto), generate dai vicini di ogni
        # nodo. I nodi con moltissimi collegamenti non generano coppie, ma contano nel punteggio delle coppie trovate.
        pos = {n: i for i, n in enumerate(nodes)}
        count: dict[tuple[int, int], int] = {}
        for c in g.nodes:
            nb = sorted((n for n in g.neighbors(c) if n in pos), key=pos.__getitem__)
            if len(nb) > MAX_HUB_DEGREE:
                continue
            for u, v in combinations(nb, 2):
                count[(u, v)] = count.get((u, v), 0) + 1
        pairs = sorted(((u, v) for (u, v), n in count.items() if n >= 2 and not g.has_edge(u, v)), key=lambda p: (pos[p[0]], pos[p[1]]))
    scored = []
    for u, v, s in nx.adamic_adar_index(g, pairs):
        common = list(nx.common_neighbors(g, u, v))
        if len(common) >= 2:
            scored.append((s, u, v, common))
    scored.sort(key=lambda x: -x[0])
    by_pair: dict[frozenset, list[Relation]] = {}
    for r in rels:
        by_pair.setdefault(frozenset((r.source_entity_id, r.target_entity_id)), []).append(r)
    out = []
    for s, u, v, common in scored[:limit]:
        path_rels = [r for c in common for r in by_pair.get(frozenset((u, c)), []) + by_pair.get(frozenset((v, c)), [])]
        sources = [x for r in path_rels if r.source_id and (x := db.get(Source, r.source_id))]
        level, reasons, _ = ev.grade(db, sources)
        hyp = sum(1 for r in path_rels if r.provenance != "sourced")
        if hyp:
            reasons.append(f"{hyp} dei collegamenti intermedi sono ipotesi")
            level = "low"
        names = [entities[c].name for c in common if c in entities]
        a, b = entities[u], entities[v]
        out.append(Candidate(
            kind="graph_proximity", title=f"{a.name} ↔ {b.name}",
            elements=[{"type": "entity", "id": a.id, "label": a.name}, {"type": "entity", "id": b.id, "label": b.name}],
            period=fmt_years(min(x for x in (a.start_year, b.start_year) if x is not None), max(x for x in (a.end_year or a.start_year, b.end_year or b.start_year) if x is not None))
            if any(x is not None for x in (a.start_year, b.start_year)) else "",
            evidence=[{"kind": "graph", "label": "Collegati agli stessi nodi", "detail": ", ".join(names)},
                      *[{"kind": "relation", "label": f"{entities[r.source_entity_id].name} → {r.relation_type} → {entities[r.target_entity_id].name}",
                         "detail": r.evidence_note or r.provenance, "ref": {"relation_id": r.id}} for r in path_rels[:8]]],
            source_ids=[x.id for x in sources], score=round(float(s), 3),
            explanation=(f"«{a.name}» e «{b.name}» non sono collegati direttamente, ma condividono {len(common)} collegamenti "
                         f"({', '.join(names[:5])}). Nodi con molti vicini comuni sono spesso legati in modo diretto: vale la pena cercarlo."),
            caveats=[NOT_CAUSAL, "La vicinanza nel grafo dipende da cosa hai inserito: un archivio incompleto produce lacune e falsi segnali."],
            reliability=level, reliability_reasons=reasons,
        ))
    return out


# --- 4. Eventi e cambiamenti nei dati ---------------------------------------------------------------

MIN_OBS = 12


def series_frame(s: Series) -> pd.Series:
    return analytics.to_pandas([(o.date, o.value) for o in s.observations]).dropna()


WINDOW = {"A": 1, "Q": 2, "M": 3, "W": 4, "D": 10}
PERIOD_DAYS = {"A": 370, "Q": 95, "M": 33, "W": 8, "D": 5}


def event_data_connections(db: Session, events: list[HistoricalEvent], series: list[Series], require_country: bool = True,
                           window: int | None = None, z_min: float = 2.0) -> list[Candidate]:
    out = []
    fixed_window = window
    cache: dict = {}
    ekeys_of = {e.id: {country_key(c) for c in e.countries or []} for e in events}
    by_country: dict[str, list[HistoricalEvent]] = {}
    for e in events:
        for k in ekeys_of[e.id]:
            by_country.setdefault(k, []).append(e)
    for s in series:
        window = fixed_window or WINDOW.get(s.frequency, 2)
        v = series_frame(s)
        if len(v) < MIN_OBS:
            continue
        d = v.diff().dropna()
        sums = d.rolling(window).sum().dropna()  # variazioni su finestre di `window` periodi: il riferimento storico
        med = float(sums.median())
        mad = float((sums - med).abs().median() * 1.4826)
        scale = max(mad, 1e-6 * max(1.0, float(v.abs().max())))
        if (sums - med).abs().max() <= scale:
            continue  # serie senza variabilità apprezzabile
        skey = country_key(s.country) if s.country else ""
        if require_country:
            if not skey:
                continue
            pool = by_country.get(skey, [])  # stessi eventi, nello stesso ordine, senza scorrere tutto l'archivio
        else:
            pool = events
        for e in pool:
            t = pd.Timestamp(year=max(1, e.start_year), month=e.start_month or 1, day=1) if e.start_year > 0 else None
            if t is None or t < v.index[0] or t > v.index[-1]:
                continue
            # I dati devono cadere davvero nella finestra dopo l'evento (serie irregolari, es. «date dei cambiamenti»).
            limit = t + pd.Timedelta(days=PERIOD_DAYS.get(s.frequency, 33) * (window + 1))
            after = d[(d.index >= t) & (d.index <= limit)].iloc[:window]
            before = v[v.index < t]
            if len(after) < window or before.empty:
                continue
            change = float(after.sum())
            z = (change - med) / scale
            # Quante finestre storiche hanno una variazione almeno altrettanto ampia: se sono molte, non è insolita.
            similar = int(((sums - med).abs() >= abs(change - med) - 1e-12).sum())
            if abs(z) < z_min or similar / len(sums) > 0.1:
                continue
            level, reasons, src_ids = _grade_events(db, [e], cache)
            reasons.insert(0, f"Serie da fonte {'istituzionale' if s.connector != 'upload' else 'caricata dall’utente'}: {s.source_label}")
            out.append(Candidate(
                kind="event_data_change", title=f"{e.title} — {s.name}",
                elements=[_event_el(e), {"type": "series", "id": s.id, "label": s.name}],
                period=f"{after.index[0].strftime('%Y-%m')}–{after.index[-1].strftime('%Y-%m')}",
                evidence=[{"kind": "data", "label": "Ultimo valore prima dell'evento", "detail": f"{before.index[-1].strftime('%Y-%m-%d')}: {before.iloc[-1]:.4g} {s.unit}"},
                          {"kind": "data", "label": f"Variazione nei {len(after)} periodi successivi", "detail": f"{change:+.4g} {s.unit} (z robusto {z:+.1f})"},
                          {"kind": "data", "label": "Variazioni altrettanto ampie nella serie", "detail": f"{similar} su {len(sums)} finestre di {window} periodi"}],
                source_ids=src_ids, score=min(abs(z), 10.0),
                explanation=(f"Dopo «{e.title}» ({fmt_years(*event_span(e))}) la serie «{s.name}» registra una variazione insolita "
                             f"({change:+.4g} {s.unit}, z robusto {z:+.1f}). La coincidenza temporale merita una verifica."),
                caveats=[NOT_CAUSAL, "Altri fatti contemporanei possono spiegare la variazione.",
                         "Il valore è la versione attuale della serie (possibili revisioni)."],
                reliability="medium" if level != "low" else "low", reliability_reasons=reasons,
            ))
    return out


# --- 5. Associazione statistica tra serie --------------------------------------------------------


def lagged_association(a: pd.Series, b: pd.Series, freq_a: str, freq_b: str, max_lag: int = 3) -> dict | None:
    """Correlazione tra le VARIAZIONI di due serie (non i livelli), al ritardo con |r| massimo.

    Frequenze diverse: ricampionamento alla più bassa (media). Restituisce r, ritardo, n, p-value
    e p corretto per il numero di ritardi provati (Bonferroni).
    """
    target = freq_a if analytics.FREQ_ORDER[freq_a] >= analytics.FREQ_ORDER[freq_b] else freq_b
    ra = analytics.resample(a, freq_a, target, "mean").diff().dropna()
    rb = analytics.resample(b, freq_b, target, "mean").diff().dropna()
    best = None
    for lag in range(-max_lag, max_lag + 1):
        x, y = ra.align(rb.shift(-lag), join="inner")
        mask = x.notna() & y.notna()
        x, y = x[mask], y[mask]
        if len(x) < MIN_OBS or x.std() == 0 or y.std() == 0:
            continue
        r, p = stats.pearsonr(x, y)
        if best is None or abs(r) > abs(best["r"]):
            best = {"r": float(r), "p": float(p), "lag": lag, "n": int(len(x)), "freq": target}
    if best:
        best["p_adj"] = min(1.0, best["p"] * (2 * max_lag + 1))
    return best


def series_connections(db: Session, series: list[Series], r_min: float = 0.5, p_max: float = 0.01) -> list[Candidate]:
    frames = {s.id: series_frame(s) for s in series}
    out = []
    for a, b in combinations(series, 2):
        if a.category == b.category and a.category != "other" and a.country and b.country and country_key(a.country) == country_key(b.country):
            continue  # due misure dello stesso fenomeno nello stesso paese: il confronto spetta al controllo delle discrepanze
        fa, fb = frames[a.id], frames[b.id]
        if len(fa) < MIN_OBS or len(fb) < MIN_OBS:
            continue
        try:
            res = lagged_association(fa, fb, a.frequency, b.frequency)
        except analytics.AnalysisError:
            continue
        if not res or abs(res["r"]) < r_min or res["p_adj"] > p_max:
            continue
        lead, follow = (a, b) if res["lag"] >= 0 else (b, a)
        lag = abs(res["lag"])
        sign = "nella stessa direzione" if res["r"] > 0 else "in direzione opposta"
        unit = ({"A": "anno", "Q": "trimestre", "M": "mese", "W": "settimana", "D": "giorno"} if lag == 1 else
                {"A": "anni", "Q": "trimestri", "M": "mesi", "W": "settimane", "D": "giorni"})[res["freq"]]
        x, y = frames[a.id], frames[b.id]
        start = max(x.index[0], y.index[0]).year
        end = min(x.index[-1], y.index[-1]).year
        reasons = [f"r = {res['r']:+.2f} su {res['n']} osservazioni, p corretto = {res['p_adj']:.2g}",
                   "Fonti dei dati: " + "; ".join(sorted({a.source_label, b.source_label}))]
        level = "medium" if res["n"] >= 30 and abs(res["r"]) >= 0.6 else "low"
        out.append(Candidate(
            kind="statistical_association", title=f"{a.name} ↔ {b.name}",
            elements=[{"type": "series", "id": a.id, "label": a.name}, {"type": "series", "id": b.id, "label": b.name}],
            period=fmt_years(start, end),
            evidence=[{"kind": "statistic", "label": "Correlazione delle variazioni", "detail": f"r = {res['r']:+.3f}, n = {res['n']}, frequenza {res['freq']}"},
                      {"kind": "statistic", "label": "Ritardo", "detail": "nessuno" if lag == 0 else f"«{lead.name}» anticipa di {lag} {unit}"},
                      {"kind": "statistic", "label": "Significatività", "detail": f"p = {res['p']:.2g}; corretto per i 7 ritardi provati: {res['p_adj']:.2g}"}],
            source_ids=[], score=abs(res["r"]) * math.log(res["n"]),
            explanation=(f"Le variazioni delle due serie si muovono {sign}" + (f", con «{lead.name}» in anticipo di {lag} {unit}" if lag else "")
                         + ". Si usano le variazioni e non i livelli, perché due serie con un trend comune sembrano sempre correlate."),
            caveats=["Correlazione, non causalità: un terzo fattore può muovere entrambe le serie.",
                     "Il risultato può cambiare nei sottoperiodi: verifica la stabilità.", "Dati nella versione attuale (possibili revisioni)."],
            reliability=level, reliability_reasons=reasons,
        ))
    return out
