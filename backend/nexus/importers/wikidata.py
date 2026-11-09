"""Eventi storici e Knowledge Graph dalla Biblioteca: Wikidata (CC0) + brevi estratti di Wikipedia (CC BY-SA 4.0).

Regole (principi del progetto):
- ogni evento ha una Fonte (Wikidata + articolo Wikipedia, URL, data di accesso, licenza) collegata;
- affidabilità «unverified»; «probable» solo se la voce Wikidata ha almeno due riferimenti distinti; mai «established»;
- cause/conseguenze solo dalle proprietà P828 «ha causa» / P1542 «ha effetto», dichiarandolo;
- nessuna informazione datata (Time Machine) generata: Wikidata/Wikipedia non sono fonti coeve;
- relazioni del grafo solo da proprietà reali di Wikidata, provenance «sourced», confidenza «medium»;
- le classi Wikidata sono verificate per etichetta all'avvio: se una non corrisponde, si salta.
Date: l'endpoint SPARQL restituisce anni astronomici (0 = 1 a.C.) e date gregoriane; per gli eventi prima del 1583
si conserva solo l'anno, per non riportare giorni e mesi convertiti di calendario.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from datetime import date

import httpx
from sqlalchemy import select

from ..api.schemas_history import EntityIn, EventIn
from ..api.schemas_research import SourceIn
from ..models import Entity, EventSource, HistoricalEvent, Relation, Series, Source
from ..services import activity, sources
from .common import Run

UA = "NEXUS/0.1 (https://nexus-sigma-gules.vercel.app; open-data research platform)"
SPARQL = "https://query.wikidata.org/sparql"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
ORIGIN = "wikidata"
WD_LICENSE = "Wikidata: CC0 1.0 (https://www.wikidata.org/wiki/Wikidata:Licensing)"
WP_LICENSE = "Wikipedia: testo CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/), estratto breve con attribuzione"

# QID -> (etichetta inglese attesa, categorie NEXUS, minimo di sitelink)
EVENT_CLASSES = {
    "Q198": ("war", ["war_geopolitics"], 2), "Q8465": ("civil war", ["war_geopolitics"], 2),
    "Q178561": ("battle", ["war_geopolitics"], 3), "Q188055": ("siege", ["war_geopolitics"], 3),
    "Q131569": ("treaty", ["war_geopolitics"], 2), "Q625298": ("peace treaty", ["war_geopolitics"], 1),
    "Q10931": ("revolution", ["revolution"], 1), "Q45382": ("coup d'état", ["revolution"], 2),
    "Q124734": ("rebellion", ["revolution"], 2), "Q114380": ("financial crisis", ["financial_crisis"], 1),
    "Q806729": ("banking crisis", ["banking", "financial_crisis"], 1), "Q1020018": ("stock market crash", ["financial_crisis"], 1),
    "Q290178": ("economic crisis", ["economic"], 1), "Q176494": ("recession", ["economic"], 1),
    "Q185565": ("hyperinflation", ["monetary"], 1), "Q1417912": ("currency crisis", ["monetary", "financial_crisis"], 1),
    "Q1092023": ("sovereign default", ["financial_crisis"], 1), "Q773335": ("debt crisis", ["financial_crisis"], 1),
    "Q806663": ("bank run", ["banking"], 1), "Q65224": ("monetary reform", ["monetary"], 1),
    "Q41806476": ("currency reform", ["monetary"], 1), "Q168247": ("famine", ["economic"], 1),
}
# Fondazioni/dissoluzioni ricavate da organizzazioni e stati (P571 inizio, P576 fine)
FOUNDING_CLASSES = {
    "Q66344": ("central bank", ["banking", "monetary"], 1, "Founding of"),
    "Q11691": ("stock exchange", ["capitalism"], 1, "Founding of"),
    "Q3024240": ("historical country", ["empires"], 3, "Founding of"),
    "Q48349": ("empire", ["empires"], 1, "Founding of"),
}
# QID -> (etichetta, tipo di entità NEXUS, minimo sitelink, proprietà di classificazione)
ENTITY_CLASSES = {
    "Q188094": ("economist", "person", 3, "P106"), "Q806798": ("banker", "person", 3, "P106"),
    "Q3624078": ("sovereign state", "state", 1, "P31"), "Q3024240": ("historical country", "state", 2, "P31"),
    "Q48349": ("empire", "state", 1, "P31"), "Q66344": ("central bank", "bank", 1, "P31"), "Q22687": ("bank", "bank", 3, "P31"),
    "Q11691": ("stock exchange", "institution", 2, "P31"), "Q162157": ("chartered company", "company", 1, "P31"),
    "Q2865305": ("trading company", "company", 2, "P31"), "Q484652": ("international organization", "organization", 2, "P31"),
    "Q1401304": ("economic theory", "theory", 1, "P31"), "Q3048444": ("school of economic thought", "theory", 1, "P31"),
    "Q273005": ("economic system", "economic_system", 1, "P31"),
}
# Proprietà Wikidata -> (tipo di relazione NEXUS, verso): "so" = soggetto→oggetto, "os" = oggetto→soggetto
RELATION_PROPS = {
    "P828": ("caused", "os", "has cause"), "P1542": ("caused", "so", "has effect"), "P361": ("occurred_during", "so", "part of"),
    "P155": ("preceded", "os", "follows"), "P156": ("preceded", "so", "followed by"), "P710": ("participant_in", "os", "participant"),
    "P607": ("participant_in", "so", "conflict"), "P1365": ("replaced", "so", "replaces"), "P1366": ("replaced", "os", "replaced by"),
    "P112": ("related_to", "os", "founded by"), "P8324": ("financed", "os", "funder"), "P859": ("financed", "os", "sponsor"),
    "P737": ("influenced", "os", "influenced by"), "P793": ("involved_in", "so", "significant event"),
}
PAGE = 1000


class Wikimedia:
    """Client gentile: User-Agent descrittivo, pause, rispetto di 429/Retry-After, cache su disco delle risposte."""

    def __init__(self, run: Run, client: httpx.Client | None = None):
        self.run = run
        self.client = client or httpx.Client(timeout=httpx.Timeout(90, connect=20), headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
        self.cache_dir = run.settings.cache_dir / "wikimedia"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get(self, url: str, params: dict) -> dict:
        key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())
        for attempt in range(6):
            try:
                r = self.client.get(url, params=params)
            except httpx.HTTPError as exc:
                if attempt == 5:
                    raise
                print(f"    Wikimedia: {type(exc).__name__}, riprovo (tentativo {attempt + 1}/6)", flush=True)
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code in (429, 503, 502, 504):
                wait = float(r.headers.get("Retry-After", 30 * (attempt + 1)))
                print(f"    Wikimedia: HTTP {r.status_code}, attendo {min(wait, 300):.0f} s (tentativo {attempt + 1}/6)", flush=True)
                self.run.report.note("Wikimedia ha chiesto di rallentare o non ha risposto (429/50x): attese rispettate.")
                time.sleep(min(wait, 300))
                continue
            r.raise_for_status()
            data = r.json()
            path.write_text(json.dumps(data))
            self.run.sleep()
            return data
        raise RuntimeError(f"Wikimedia non disponibile per {url}")

    def sparql(self, query: str) -> list[dict]:
        data = self._get(SPARQL, {"query": query, "format": "json"})
        return [{k: v["value"] for k, v in b.items()} for b in data["results"]["bindings"]]

    def extracts(self, titles: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for i in range(0, len(titles), 20):
            chunk = titles[i:i + 20]
            data = self._get(WIKIPEDIA_API, {"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                                             "exsentences": 2, "redirects": 1, "format": "json", "titles": "|".join(chunk)})
            norm = {n["to"]: n["from"] for n in data.get("query", {}).get("normalized", [])}
            redir = {r["to"]: r["from"] for r in data.get("query", {}).get("redirects", [])}
            for page in data.get("query", {}).get("pages", {}).values():
                t = page.get("title", "")
                orig = norm.get(redir.get(t, t), redir.get(t, t))
                if page.get("extract"):
                    out[orig] = page["extract"].strip()[:700]
        return out


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def parse_time(value: str | None, precision: str | None) -> tuple[int | None, int | None, int | None, int]:
    """Valore SPARQL (anno astronomico, gregoriano) -> (anno storico, mese, giorno, precisione)."""
    if not value or value.startswith("http"):  # valore sconosciuto («somevalue») di Wikidata
        return None, None, None, 0
    neg = value.startswith("-")
    try:
        y = int(value.lstrip("-+").split("-")[0])
    except ValueError:
        return None, None, None, 0
    y = -y if neg else y
    year = y if y > 0 else y - 1  # anno astronomico 0 = 1 a.C.
    prec = int(precision or 9)
    if prec < 9 and year < 0 and (year + 1) % 10 == 0:
        year += 1  # date per decennio/secolo/millennio: si conserva l'anno «tondo» indicato dalla fonte (es. 3000 a.C.)
    rest = value.lstrip("-+").split("T")[0].split("-")
    month = int(rest[1]) if prec >= 10 and len(rest) > 1 and year >= 1583 else None
    day = int(rest[2]) if prec >= 11 and len(rest) > 2 and year >= 1583 else None
    return year, month, day, prec


def verify_classes(wm: Wikimedia, run: Run, classes: dict) -> dict:
    ids = " ".join(f"wd:{q}" for q in classes)
    rows = wm.sparql(f'SELECT ?q ?l WHERE {{ VALUES ?q {{ {ids} }} ?q rdfs:label ?l FILTER(LANG(?l)="en") }}')
    labels = {qid(r["q"]): r["l"] for r in rows}
    ok = {}
    for q, spec in classes.items():
        if labels.get(q, "").lower() == spec[0].lower():
            ok[q] = spec
        else:
            run.report.note(f"Classe Wikidata {q} saltata: etichetta attesa «{spec[0]}», trovata «{labels.get(q)}».")
    return ok


def _event_candidates(wm: Wikimedia, run: Run, cls: str, min_sl: int, cap: int) -> list[dict]:
    out: dict[str, dict] = {}
    offset = 0
    while len(out) < cap:
        rows = wm.sparql(f"""
SELECT ?item ?label ?sl ?t ?tp ?s ?sp ?e ?ep ?article WHERE {{
  ?item wdt:P31 wd:{cls} ; wikibase:sitelinks ?sl . FILTER(?sl >= {min_sl})
  ?item rdfs:label ?label FILTER(LANG(?label) = "en")
  OPTIONAL {{ ?item p:P585/psv:P585 [ wikibase:timeValue ?t ; wikibase:timePrecision ?tp ] }}
  OPTIONAL {{ ?item p:P580/psv:P580 [ wikibase:timeValue ?s ; wikibase:timePrecision ?sp ] }}
  OPTIONAL {{ ?item p:P582/psv:P582 [ wikibase:timeValue ?e ; wikibase:timePrecision ?ep ] }}
  OPTIONAL {{ ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }}
}} ORDER BY ?item LIMIT {PAGE} OFFSET {offset}""")
        for r in rows:
            q = qid(r["item"])
            if q not in out:
                out[q] = r
        if len(rows) < PAGE:
            break
        offset += PAGE
    return list(out.values())


def _founding_candidates(wm: Wikimedia, cls: str, min_sl: int, cap: int) -> list[dict]:
    out: dict[str, dict] = {}
    offset = 0
    while len(out) < cap:
        rows = wm.sparql(f"""
SELECT ?item ?label ?sl ?s ?sp ?e ?ep ?article WHERE {{
  ?item wdt:P31 wd:{cls} ; wikibase:sitelinks ?sl ; p:P571/psv:P571 [ wikibase:timeValue ?s ; wikibase:timePrecision ?sp ] . FILTER(?sl >= {min_sl})
  ?item rdfs:label ?label FILTER(LANG(?label) = "en")
  OPTIONAL {{ ?item p:P576/psv:P576 [ wikibase:timeValue ?e ; wikibase:timePrecision ?ep ] }}
  OPTIONAL {{ ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }}
}} ORDER BY ?item LIMIT {PAGE} OFFSET {offset}""")
        for r in rows:
            q = qid(r["item"])
            if q not in out:
                out[q] = r
        if len(rows) < PAGE:
            break
        offset += PAGE
    return list(out.values())


def balance(cands: list[dict], limit: int) -> list[dict]:
    """Copertura equilibrata: a turno un elemento per secolo (il più citato), finché si raggiunge il limite."""
    by_century: dict[int, list[dict]] = defaultdict(list)
    for c in cands:
        by_century[c["_year"] // 100].append(c)
    for v in by_century.values():
        v.sort(key=lambda c: -int(c.get("sl", 0)))
    picked: list[dict] = []
    while len(picked) < limit and any(by_century.values()):
        for cent in sorted(by_century):
            if by_century[cent] and len(picked) < limit:
                picked.append(by_century[cent].pop(0))
    return picked


def _details(wm: Wikimedia, qids: list[str]) -> dict[str, dict]:
    """Paesi (P17), luogo (P276), cause (P828), effetti (P1542) con etichette, e numero di riferimenti distinti."""
    vals = " ".join(f"wd:{q}" for q in qids)
    rows = wm.sparql(f"""
SELECT ?item ?p ?oLabel WHERE {{
  VALUES ?item {{ {vals} }} VALUES ?p {{ wdt:P17 wdt:P276 wdt:P828 wdt:P1542 }}
  ?item ?p ?o . ?o rdfs:label ?oLabel FILTER(LANG(?oLabel) = "en")
}}""")
    out: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        p = r["p"].rsplit("/", 1)[-1]
        lst = out[qid(r["item"])][p]
        if r["oLabel"] not in lst:
            lst.append(r["oLabel"])
    refs = wm.sparql(f"""
SELECT ?item (COUNT(DISTINCT ?ref) AS ?n) WHERE {{ VALUES ?item {{ {vals} }} ?item ?prop ?st . ?st prov:wasDerivedFrom ?ref }} GROUP BY ?item""")
    for r in refs:
        out[qid(r["item"])]["refs"] = int(r["n"])
    return out


def clean_extract(text: str) -> str:
    """Toglie i residui della pronuncia rimossa da Wikipedia («Elam () was», «(; Greek: …)»); il testo non cambia."""
    import re

    text = re.sub(r"\(\s*[;,]?\s*\)", "", text)
    text = re.sub(r"\(\s*;\s*", "(", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _wiki_title(article: str | None) -> str | None:
    if not article:
        return None
    from urllib.parse import unquote

    return unquote(article.rsplit("/wiki/", 1)[-1]).replace("_", " ")


def run_events(run: Run, wm: Wikimedia | None = None) -> None:
    wm = wm or Wikimedia(run)
    limit = run.limit or 10**9
    events_cls = verify_classes(wm, run, EVENT_CLASSES)
    found_cls = verify_classes(wm, run, {k: v[:3] for k, v in FOUNDING_CLASSES.items()})
    cands: list[dict] = []
    for cls, (label, cats, min_sl) in events_cls.items():
        print(f"  candidati: {label} ({cls})…", flush=True)
        for c in _event_candidates(wm, run, cls, min_sl, cap=max(limit, 2000)):
            y, *_ = parse_time(c.get("t") or c.get("s"), c.get("tp") or c.get("sp"))
            if y is None:
                continue
            c.update(_year=y, _cats=cats, _kind="event", _cls=label)
            cands.append(c)
    for cls, (label, cats, min_sl) in found_cls.items():
        prefix = FOUNDING_CLASSES[cls][3]
        for c in _founding_candidates(wm, cls, min_sl, cap=max(limit // 4, 500)):
            y, *_ = parse_time(c.get("s"), c.get("sp"))
            if y is None:
                continue
            c.update(_year=y, _cats=cats, _kind="founding", _cls=label, label=f"{prefix} {c['label']}", e=None, ep=None)
            cands.append(c)
    # stesso QID in più classi: una sola volta
    uniq: dict[str, dict] = {}
    for c in cands:
        uniq.setdefault(qid(c["item"]) + c["_kind"], c)
    chosen = balance(list(uniq.values()), limit)
    run.report.note(f"Eventi candidati: {len(uniq)}; selezionati con copertura per secolo: {len(chosen)}.")

    today = date.today().isoformat()
    present = set(run.db.scalars(select(HistoricalEvent.external_id).where(HistoricalEvent.owner_id == run.lib.id,
                                                                          HistoricalEvent.origin == ORIGIN)))
    for i in range(0, len(chosen), 50):
        batch = []
        for c in chosen[i:i + 50]:
            if run.is_done(_ekey(c)):
                continue
            if _ext(c) in present:
                run.report.add("historical_events", "skipped")
                continue
            batch.append(c)
        if not batch:
            continue
        print(f"  eventi {i + 1}–{i + len(batch)} di {len(chosen)}", flush=True)
        det = _details(wm, [qid(c["item"]) for c in batch])
        titles = [t for c in batch if (t := _wiki_title(c.get("article")))]
        extracts = wm.extracts(titles)
        try:
            for c in batch:
                _create_event(run, c, det.get(qid(c["item"]), {}), extracts, today)
            activity.record(run.db, user=run.lib, actor="system", action="library.import", entity_type="event", entity_id=None,
                            summary=f"Biblioteca: importati eventi da Wikidata (lotto {i // 50 + 1})")
            run.db.commit()
        except Exception as exc:  # noqa: BLE001 — il lotto si annulla e si riprova al prossimo avvio
            for c in batch:
                run.done.discard(_ekey(c))
            run.error("historical_events", f"lotto {i // 50 + 1}", repr(exc))
            continue
        run.save_state()


def _ext(c: dict) -> str:
    return qid(c["item"]) if c["_kind"] == "event" else f"{qid(c['item'])}:founding"


def _ekey(c: dict) -> str:
    return f"event:{c['_kind']}:{qid(c['item'])}"


def _create_event(run: Run, c: dict, det: dict, extracts: dict[str, str], today: str) -> None:
    q = qid(c["item"])
    ext = _ext(c)
    key = _ekey(c)
    if c["_kind"] == "event":
        sy, sm, sd, sp = parse_time(c.get("t") or c.get("s"), c.get("tp") or c.get("sp"))
        ey, em, ed, _ = parse_time(c.get("e"), c.get("ep")) if not c.get("t") else (None, None, None, 0)
    else:
        sy, sm, sd, sp = parse_time(c.get("s"), c.get("sp"))
        ey = em = ed = None
    title_wp = _wiki_title(c.get("article"))
    extract = clean_extract(extracts.get(title_wp or "", ""))
    causes = det.get("P828", [])
    effects = det.get("P1542", [])
    prec = {11: "giorno", 10: "mese", 9: "anno", 8: "decennio", 7: "secolo", 6: "millennio"}.get(sp, "anno o meno")
    note = (f"Importato da Wikidata ({q}). Precisione della data: {prec}"
            + ("; prima del 1583 si riporta solo l'anno (conversione di calendario)" if sy is not None and sy < 1583 else "")
            + ". Cause e conseguenze solo se presenti come proprietà Wikidata.")
    try:
        data = EventIn(
            title=(c["label"][:1].upper() + c["label"][1:])[:300], start_year=sy, start_month=sm, start_day=sd,
            end_year=ey if ey is not None and ey >= sy else None, end_month=em if ey is not None and ey >= sy else None,
            end_day=ed if ey is not None and ey >= sy else None,
            countries=det.get("P17", [])[:20], region=(det.get("P276") or [""])[0][:120], categories=c["_cats"],
            description=extract,
            causes=("Secondo Wikidata (P828 «ha causa»): " + "; ".join(causes[:10])) if causes else "",
            consequences=("Secondo Wikidata (P1542 «ha effetto»): " + "; ".join(effects[:10])) if effects else "",
            reliability="probable" if det.get("refs", 0) >= 2 else "unverified", reliability_note=note,
        )
    except Exception as exc:  # noqa: BLE001 — date incoerenti o campi non validi: si salta, non si corregge a mano
        run.report.add("historical_events", "skipped")
        run.error("historical_events", key, f"non valido: {exc}")
        run.mark(key)
        return
    notes = f"Dati strutturati: {WD_LICENSE}."
    if title_wp:
        notes += f" Descrizione: estratto dall'articolo «{title_wp}» di Wikipedia in inglese (https://en.wikipedia.org/wiki/{title_wp.replace(' ', '_')}). {WP_LICENSE}."
    try:
        sdata = SourceIn(source_type="web", title=f"Wikidata {q}: {c['label'][:400]}", url=f"https://www.wikidata.org/wiki/{q}",
                         accessed_at=today, notes=notes)
    except Exception as exc:  # noqa: BLE001
        run.error("sources", key, f"non valida: {exc}")
        run.mark(key)
        return
    # Scrittura a blocchi (stesse validazioni di create_event/create_source/link_source, commit unico per lotto):
    # verso un database remoto evita ~10 viaggi di rete per evento.
    src = Source(owner_id=run.lib.id, origin=ORIGIN, external_id=ext, **sdata.model_dump())
    e = HistoricalEvent(owner_id=run.lib.id, origin=ORIGIN, external_id=ext, **data.model_dump())
    run.db.add_all([src, e])
    run.db.flush()
    e.source_links.append(EventSource(source_id=src.id, pages="", note="Voce Wikidata e articolo Wikipedia"))
    run.db.add(Entity(owner_id=run.lib.id, entity_type="event", name=e.title, description=e.description[:2000],
                      start_year=e.start_year, end_year=e.end_year, event_id=e.id,
                      origin=ORIGIN if c["_kind"] == "event" else None, external_id=q if c["_kind"] == "event" else None))
    run.report.add("historical_events", "created")
    run.report.add("sources", "created")
    run.mark(key)


# --- Knowledge Graph --------------------------------------------------------------------------------


def _entity_candidates(wm: Wikimedia, cls: str, prop: str, min_sl: int, cap: int) -> list[dict]:
    out: dict[str, dict] = {}
    offset = 0
    while len(out) < cap:
        rows = wm.sparql(f"""
SELECT ?item ?label ?desc ?sl (MIN(?b0) AS ?b) (MAX(?d0) AS ?d) WHERE {{
  ?item wdt:{prop} wd:{cls} ; wikibase:sitelinks ?sl . FILTER(?sl >= {min_sl})
  ?item rdfs:label ?label FILTER(LANG(?label) = "en")
  OPTIONAL {{ ?item schema:description ?desc FILTER(LANG(?desc) = "en") }}
  OPTIONAL {{ ?item wdt:P569|wdt:P571 ?b0 }}
  OPTIONAL {{ ?item wdt:P570|wdt:P576 ?d0 }}
}} GROUP BY ?item ?label ?desc ?sl ORDER BY DESC(?sl) ?item LIMIT {PAGE} OFFSET {offset}""")
        for r in rows:
            out.setdefault(qid(r["item"]), r)
        if len(rows) < PAGE:
            break
        offset += PAGE
    return list(out.values())[:cap]


def _year(v: str | None) -> int | None:
    y, *_ = parse_time(v, "9")
    return y if y is None or -10000 <= y <= 2200 else None


def _library_source(run: Run) -> Source:
    s = run.db.scalar(select(Source).where(Source.owner_id == run.lib.id, Source.origin == ORIGIN, Source.external_id == "graph"))
    if s is None:
        s = sources.create_source(run.db, run.lib, SourceIn(
            source_type="dataset", title="Wikidata — dichiarazioni usate per il Knowledge Graph", url="https://www.wikidata.org/",
            accessed_at=date.today().isoformat(),
            notes=f"{WD_LICENSE}. Ogni relazione indica nella nota la proprietà e le voci Wikidata da cui deriva."))
        s.origin, s.external_id = ORIGIN, "graph"
        run.db.commit()
    return s


def run_graph(run: Run, wm: Wikimedia | None = None) -> None:
    wm = wm or Wikimedia(run)
    limit = run.limit or 10**9
    classes = verify_classes(wm, run, ENTITY_CLASSES)
    per_class = max(50, limit // max(1, len(classes)))
    existing = {x: i for x, i in run.db.execute(
        select(Entity.external_id, Entity.id).where(Entity.owner_id == run.lib.id, Entity.origin == ORIGIN))}
    names = {n.lower() for (n,) in run.db.execute(select(Entity.name).where(Entity.owner_id == run.lib.id))}
    created = 0
    for cls, (label, etype, min_sl, prop) in classes.items():
        print(f"  entità: {label} ({cls})…", flush=True)
        for c in _entity_candidates(wm, cls, prop, min_sl, per_class):
            q = qid(c["item"])
            if q in existing:
                run.report.add("entities", "skipped")
                continue
            if created >= limit:
                break
            name = c["label"][:300]
            if name.lower() in names:  # omonimi: si distingue con il QID, non si inventano qualificazioni
                name = f"{name[:285]} ({q})"
            b, d = _year(c.get("b")), _year(c.get("d"))
            try:
                data = EntityIn(entity_type=etype, name=name, description=(c.get("desc") or "")[:2000],
                                start_year=b, end_year=d if d is None or b is None or d >= b else None)
            except Exception as exc:  # noqa: BLE001
                run.error("entities", q, f"non valido: {exc}")
                continue
            e = Entity(owner_id=run.lib.id, origin=ORIGIN, external_id=q, **data.model_dump())
            run.db.add(e)
            existing[q] = -1  # stesso QID in più classi (es. impero e stato storico): una sola entità
            names.add(name.lower())
            created += 1
            run.report.add("entities", "created")
            if created % 500 == 0:
                run.db.flush()
                run.db.commit()
        run.db.commit()
        activity.record(run.db, user=run.lib, actor="system", action="library.import", entity_type="entity", entity_id=None,
                        summary=f"Biblioteca: importate entità Wikidata della classe «{label}»")
        run.db.commit()
    _indicator_entities(run)
    _relations(run, wm)


def _indicator_entities(run: Run) -> None:
    """Un'entità «indicatore» per ogni serie della Biblioteca, collegata con series_id (usata da Discovery)."""
    linked = set(run.db.scalars(select(Entity.series_id).where(Entity.owner_id == run.lib.id, Entity.series_id.is_not(None))))
    for s in run.db.scalars(select(Series).where(Series.owner_id == run.lib.id)):
        if s.id in linked:
            continue
        run.db.add(Entity(owner_id=run.lib.id, entity_type="indicator", name=s.name[:300], description=s.source_label[:2000],
                          series_id=s.id, origin=s.origin, external_id=f"series:{s.id}"))
        run.report.add("entities", "created")
    run.db.commit()


def _relations(run: Run, wm: Wikimedia) -> None:
    ids = {x: i for x, i in run.db.execute(
        select(Entity.external_id, Entity.id).where(Entity.owner_id == run.lib.id, Entity.origin == ORIGIN))}
    qids = [q for q in ids if q.startswith("Q")]
    if not qids:
        return
    src = _library_source(run)
    seen = {(a, b, t) for a, b, t in run.db.execute(select(Relation.source_entity_id, Relation.target_entity_id, Relation.relation_type)
                                                    .where(Relation.owner_id == run.lib.id))}
    props = " ".join(f"wdt:{p}" for p in RELATION_PROPS)
    n_new = 0
    for i in range(0, len(qids), 150):
        key = f"rel:{i}:{qids[i]}"
        if run.is_done(key):
            continue
        vals = " ".join(f"wd:{q}" for q in qids[i:i + 150])
        try:
            rows = wm.sparql(f"SELECT ?s ?p ?o WHERE {{ VALUES ?s {{ {vals} }} VALUES ?p {{ {props} }} ?s ?p ?o . FILTER(isIRI(?o)) }}")
        except Exception as exc:  # noqa: BLE001
            run.error("relations", key, repr(exc))
            continue
        for r in rows:
            s_q, o_q, p = qid(r["s"]), qid(r["o"]), r["p"].rsplit("/", 1)[-1]
            if o_q not in ids or s_q == o_q:
                continue
            rtype, direction, plabel = RELATION_PROPS[p]
            a, b = (ids[s_q], ids[o_q]) if direction == "so" else (ids[o_q], ids[s_q])
            if (a, b, rtype) in seen:
                run.report.add("relations", "skipped")
                continue
            seen.add((a, b, rtype))
            run.db.add(Relation(owner_id=run.lib.id, origin=ORIGIN, source_entity_id=a, target_entity_id=b, relation_type=rtype,
                                provenance="sourced", source_id=src.id, confidence="medium",
                                evidence_note=f"Wikidata: {s_q} {p} ({plabel}) → {o_q}. https://www.wikidata.org/wiki/{s_q}#{p}"))
            n_new += 1
            run.report.add("relations", "created")
        run.db.commit()
        run.mark(key)
    activity.record(run.db, user=run.lib, actor="system", action="library.import", entity_type="relation", entity_id=None,
                    summary=f"Biblioteca: {n_new} relazioni dal grafo Wikidata (provenienza documentata)")
    run.db.commit()
