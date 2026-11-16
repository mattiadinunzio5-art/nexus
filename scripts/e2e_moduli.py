"""Controllo end-to-end dei moduli di NEXUS su un server reale in modalità locale (un utente, database vuoto).

Uso: avviare il server su un database NUOVO, per esempio
    NEXUS_DATABASE_URL=sqlite:////tmp/e2e.db NEXUS_DATA_DIR=/tmp/e2e-data uvicorn nexus.main:app --port 8765
poi:  python scripts/e2e_moduli.py http://127.0.0.1:8765 risultati.json
Ogni controllo è stampato come PASS/FAIL; il file JSON raccoglie i risultati. Crea dati di prova: non usarlo sul server online.
"""

import io
import json
import sys
import time

import httpx

B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
c = httpx.Client(base_url=B, headers={"X-Nexus-Client": "web"}, timeout=120)
results = []


def check(area, name, cond, detail=""):
    results.append({"area": area, "check": name, "ok": bool(cond), "detail": str(detail)[:300]})
    print(("PASS " if cond else "FAIL ") + f"[{area}] {name}" + (f" — {detail}" if detail and not cond else ""))


def j(r):
    try:
        return r.json()
    except Exception:
        return {"_raw": r.text[:300]}


# --- Knowledge Memory: progetto, documento, note, ricerca globale, attività -------------------------
p = j(c.post("/api/projects", json={"title": "Crisi del 1929", "research_question": "Perché la crisi bancaria del 1930 seguì il crollo di borsa?"}))
check("Knowledge Memory", "crea progetto", "id" in p, p)
doc_text = ("The stock market crash of October 1929 wiped out household wealth. "
            "Bank failures in 1930 followed the crash and reduced credit to firms. "
            "Industrial production fell sharply between 1929 and 1932.\n") * 3
r = c.post("/api/documents", files={"file": ("crash.txt", doc_text.encode(), "text/plain")}, data={"title": "Friedman & Schwartz (estratto)", "project_id": str(p["id"])})
d = j(r)
check("Knowledge Memory", "carica documento e lo indicizza", r.status_code in (200, 201) and d.get("chunk_count", 0) > 0, r.text[:200])
n = j(c.post("/api/notes", json={"title": "Idea: canale del credito", "body": "Le banche fallite riducono il credito", "project_id": p["id"], "document_id": d.get("id")}))
check("Knowledge Memory", "crea nota collegata a progetto e documento", "id" in n, n)
s = j(c.get("/api/search", params={"q": "credito"}))
check("Knowledge Memory", "ricerca globale trova la nota o il documento", any(h["type"] in ("note", "document", "chunk") for h in s.get("hits", [])), [h["type"] for h in s.get("hits", [])])
s2 = j(c.get("/api/search", params={"q": "fallimenti bancari"}))
check("Knowledge Memory", "ricerca in italiano trova il documento inglese", any("Friedman" in h["title"] for h in s2.get("hits", [])), [h["title"] for h in s2.get("hits", [])][:5])
act = j(c.get("/api/activity"))
items = act if isinstance(act, list) else act.get("items", [])
check("Knowledge Memory", "registro attività registra le azioni", any("documento" in (a.get("summary") or "").lower() or a.get("action", "").startswith("document") for a in items), len(items))

# --- Deep Research: Ask the Archive ---------------------------------------------------------------
a = j(c.post("/api/research/ask", json={"question": "fallimenti bancari dopo il crollo del 1929"}))
check("Deep Research", "risposta con stato, affermazioni e passaggi", "answer_status" in a and a.get("passages") is not None and a.get("claims") is not None, list(a)[:12])
check("Deep Research", "domanda in italiano su documento inglese: risposta sostenuta", a.get("answer_status") in ("supported", "partial") and any("Friedman" in json.dumps(x) for x in a.get("passages", [])), (a.get("answer_status"), [c_.get("text", "")[:80] for c_ in a.get("claims", [])][:2]))
a2 = j(c.post("/api/research/ask", json={"question": "inflazione in Germania nel 1923"}))
check("Deep Research", "domanda senza fonti non viene «risposta»", a2.get("answer_status") in ("unsupported", "no_sources", "insufficient"), a2.get("answer_status"))

# --- Intelligence Core: War Room (coda persistente) -------------------------------------------------
run = j(c.post("/api/research/runs", json={"question": "Perché le banche fallirono dopo il crollo del 1929?", "project_id": p["id"], "document_ids": [d.get("id")]}))
check("Intelligence Core", "ricerca War Room messa in coda", run.get("status") in ("queued", "running"), run)
status = None
for _ in range(60):
    rr = j(c.get(f"/api/research/runs/{run.get('id')}"))
    status = rr.get("status")
    if status not in ("queued", "running"):
        break
    time.sleep(2)
check("Intelligence Core", "il worker completa la ricerca (in attesa di approvazione)", status == "awaiting_approval", f"stato finale {status}: {rr.get('error')}")
check("Intelligence Core", "passaggi e prove registrati", len(rr.get("steps", [])) >= 3 and rr.get("evidence") is not None, len(rr.get("steps", [])))
dec = c.post(f"/api/research/runs/{run.get('id')}/decision", json={"decision": "approve", "note": "Verificata sulle fonti"})
check("Intelligence Core", "approvazione dell'utente", dec.status_code == 200 and j(dec).get("status") == "approved", dec.text[:200])
rep = c.post(f"/api/reports/from-run/{run.get('id')}")
check("Intelligence Core", "rapporto creato dalla ricerca approvata", rep.status_code in (200, 201), rep.text[:200])

# --- Confidence System -----------------------------------------------------------------------------
src1 = j(c.post("/api/sources", json={"source_type": "book", "title": "A Monetary History of the United States", "authors": ["Friedman, Milton", "Schwartz, Anna"], "year": 1963, "publisher": "Princeton University Press", "evidence_class": "secondary"}))
src2 = j(c.post("/api/sources", json={"source_type": "book", "title": "Essays on the Great Depression", "authors": ["Bernanke, Ben"], "year": 2000, "publisher": "Princeton University Press"}))
src3 = j(c.post("/api/sources", json={"source_type": "article", "title": "Money and Business Cycles", "authors": ["Friedman, Milton"], "year": 1963}))
for s_ in (src1, src2):
    c.post(f"/api/sources/{s_['id']}/verify", json={"method": "user", "note": "Controllata"})
asm = j(c.get(f"/api/sources/{src1['id']}/assessment"))
check("Confidence System", "valutazione per dimensioni con motivazioni", {"identity", "authority", "originality"} <= set(asm) and len(asm.get("reasons", [])) >= 3, asm.get("reasons"))
check("Confidence System", "identità dichiarata ≠ contenuto verificato", asm.get("identity") == "declared" and "non controlla" in asm.get("content_note", ""), asm.get("identity"))

# --- Temporal Intelligence: eventi, tre date, Time Machine -------------------------------------------
e1 = j(c.post("/api/history/events", json={"title": "Crollo di Wall Street", "start_year": 1929, "start_month": 10, "start_day": 24, "countries": ["Stati Uniti"], "categories": ["financial_crisis"], "institutions": ["Federal Reserve"], "reliability": "established"}))
e2 = j(c.post("/api/history/events", json={"title": "Crisi bancaria americana", "start_year": 1930, "start_month": 11, "countries": ["Stati Uniti"], "categories": ["banking"], "institutions": ["Federal Reserve"], "reliability": "established"}))
check("Temporal Intelligence", "eventi creati", "id" in e1 and "id" in e2, (e1, e2))
c.post(f"/api/history/events/{e1['id']}/sources", json={"source_id": src1["id"], "pages": "299-305"})
c.post(f"/api/history/events/{e2['id']}/sources", json={"source_id": src2["id"], "pages": "41-46"})
c.post(f"/api/history/events/{e2['id']}/sources", json={"source_id": src3["id"], "pages": "12"})
e3 = j(c.post("/api/history/events", json={"title": "Fallimento della Bank of United States", "start_year": 1930, "start_month": 12, "countries": ["Stati Uniti"], "categories": ["banking"], "institutions": ["Federal Reserve"], "reliability": "established"}))
c.post(f"/api/history/events/{e3['id']}/sources", json={"source_id": src3["id"], "pages": "40"})
k1 = c.post(f"/api/history/events/{e1['id']}/knowledge", json={"content": "Le perdite di borsa erano note ai contemporanei", "kind": "contemporary", "known_since_year": 1929, "refers_to": "1929-10-24", "published_on": "1929-10-25"})
k2 = c.post(f"/api/history/events/{e1['id']}/knowledge", json={"content": "Il ruolo della contrazione monetaria fu documentato dopo", "kind": "later_discovery", "known_since_year": 1963, "source_id": src1["id"], "published_on": "1963-01-01"})
check("Temporal Intelligence", "conoscenze con date distinte", k1.status_code in (200, 201) and k2.status_code in (200, 201), k1.text[:200] + k2.text[:200])
tl = j(c.get("/api/history/timeline", params={"as_of_year": 1935}))
ev = next((x for x in tl.get("events", []) if x.get("title") == "Crollo di Wall Street"), None) if isinstance(tl, dict) else None
known = [k["content"] for k in (ev or {}).get("known_then", [])]
later = json.dumps(ev or {})
check("Temporal Intelligence", "Time Machine al 1935: mostra ciò che era noto", any("contemporanei" in k for k in known), known)
check("Temporal Intelligence", "Time Machine al 1935: non usa conoscenze del 1963 come note", not any("contrazione monetaria" in k for k in known), known)
check("Temporal Intelligence", "Time Machine: la conoscenza del 1963 è tra quelle successive (nascosta o separata)", (ev or {}).get("hidden_later_count", 0) >= 1 or any("contrazione monetaria" in json.dumps(k) for k in (ev or {}).get("known_later", [])), {k: (ev or {}).get(k) for k in ("known_later", "hidden_later_count")})
tl2 = j(c.get("/api/history/timeline", params={"as_of_year": 1970}))
ev2 = next((x for x in tl2.get("events", []) if x.get("title") == "Crollo di Wall Street"), {})
check("Temporal Intelligence", "Time Machine al 1970: la conoscenza del 1963 è nota", any("contrazione monetaria" in k["content"] for k in ev2.get("known_then", [])), [k["content"] for k in ev2.get("known_then", [])])

# --- Intelligence Graph ----------------------------------------------------------------------------
ents = {x["name"]: x["id"] for x in j(c.get("/api/graph/entities", params={"limit": 50}))} if isinstance(j(c.get("/api/graph/entities")), list) else {}
ea, eb = ents.get("Crollo di Wall Street"), ents.get("Crisi bancaria americana")
check("Intelligence Graph", "ogni evento ha il suo nodo nel grafo", ea and eb, list(ents)[:10])
ec = j(c.post("/api/graph/entities", json={"entity_type": "indicator", "name": "Credito alle imprese"}))
r1 = c.post("/api/graph/relations", json={"source_entity_id": ea, "target_entity_id": eb, "relation_type": "caused", "provenance": "sourced", "source_id": src2["id"]})
r2 = c.post("/api/graph/relations", json={"source_entity_id": eb, "target_entity_id": ec.get("id"), "relation_type": "caused", "provenance": "user_hypothesis", "evidence_note": "canale del credito"})
check("Intelligence Graph", "relazioni documentata e ipotizzata", r1.status_code == 201 and r2.status_code == 201, r1.text[:150] + r2.text[:150])
dup = c.post("/api/graph/relations", json={"source_entity_id": ea, "target_entity_id": eb, "relation_type": "caused", "provenance": "sourced", "source_id": src2["id"]})
check("Intelligence Graph", "relazione duplicata rifiutata", dup.status_code in (409, 422), dup.status_code)
nosrc = c.post("/api/graph/relations", json={"source_entity_id": ea, "target_entity_id": ec.get("id"), "relation_type": "influenced", "provenance": "sourced"})
check("Intelligence Graph", "«documentata» senza fonte rifiutata", nosrc.status_code == 422, nosrc.status_code)
path = j(c.get("/api/graph/path", params={"source": ea, "target": ec.get("id")}))
check("Intelligence Graph", "percorso tra nodi", path.get("found") and len(path.get("entity_ids", [])) == 3, path)

# --- Causal Engine ---------------------------------------------------------------------------------
ch = j(c.post("/api/discovery/causal/chains", json={"start": ea, "end": ec.get("id")}))
res = ch.get("result", {})
links = (res.get("paths") or [{}])[0].get("links", [])
check("Causal Engine", "catena causale ricostruita", len(links) == 2, res.get("notes"))
check("Causal Engine", "anello documentato vs ipotizzato distinti", [x.get("class") for x in links] == ["causal_documented", "causal_hypothesized"], [x.get("class") for x in links])
check("Causal Engine", "forza della catena = anello più debole (non dimostrata)", (res.get("paths") or [{}])[0].get("strength") == "causal_hypothesized", (res.get("paths") or [{}])[0].get("strength"))
import math
csv1 = "date,value\n" + "\n".join(f"{1950 + i}-01-01,{100 * 1.03 ** i * (1 + 0.02 * math.sin(i)):.4f}" for i in range(60))
csv2 = "date,value\n" + "\n".join(f"{1950 + i}-01-01,{5 + 2 * math.sin(i) + 0.03 * i:.4f}" for i in range(60) if i not in (30, 31))
up1 = j(c.post("/api/finance/series/upload", files={"file": ("pil.csv", csv1.encode())}, data={"name": "PIL reale indice", "source_label": "Dati di prova", "unit": "indice"}))
up2 = j(c.post("/api/finance/series/upload", files={"file": ("disocc.csv", csv2.encode())}, data={"name": "Disoccupazione prova", "source_label": "Dati di prova", "unit": "%"}))
check("Causal Engine", "serie caricate da CSV", "id" in up1 and "id" in up2, (str(up1)[:150], str(up2)[:150]))
tr = j(c.post("/api/discovery/causal/transmission", json={"series_ids": [up1.get("id"), up2.get("id")]}))
st = (tr.get("result", {}).get("steps") or [{}])[0]
check("Causal Engine", "trasmissione tra serie = correlazione, non causa", st.get("class") == "correlation" and "p_adj_chain" in (st.get("statistic") or {}), st.get("class"))
fs = j(c.post("/api/discovery/foresight", json={"variables": [{"series_id": up1.get("id"), "favorable": "up"}, {"series_id": up2.get("id"), "favorable": "down"}], "horizon_years": 3}))
fr = fs.get("result", {})
check("Causal Engine", "scenari con dipendenze, note sui buchi e riproducibilità",
      fr.get("dependencies") is not None and any("escluse" in x for x in fr.get("data_notes", [])) and fr.get("reproducibility", {}).get("seed") == 7,
      (fr.get("data_notes"), fr.get("reproducibility")))
fs2 = j(c.post("/api/discovery/foresight", json={"variables": [{"series_id": up1.get("id"), "favorable": "up"}, {"series_id": up2.get("id"), "favorable": "down"}], "horizon_years": 3}))
check("Causal Engine", "scenari riproducibili", fs2.get("result", {}).get("variables") == fr.get("variables"))
lab = j(c.post("/api/lab/simulations/monte_carlo_bootstrap", json={"series_id": up1.get("id"), "years": 3, "n_paths": 500, "seed": 3}))
check("Causal Engine", "laboratorio: bootstrap con impronta dei dati", "PIL reale indice" in json.dumps(lab.get("result", {}).get("results", {}).get("reproducibility", {})), str(lab)[:200])

# --- Discovery (Intelligence Core) su archivio reale: connessioni con motivazioni del Confidence System
ds = j(c.post("/api/discovery/sessions", json={"mode": "autonomous", "query": ""}))
check("Intelligence Core", "sessione di discovery avviata", ds.get("status") in ("queued", "running", "completed"), ds)
for _ in range(60):
    ss = j(c.get(f"/api/discovery/sessions/{ds.get('id')}"))
    if ss.get("status") not in ("queued", "running"):
        break
    time.sleep(2)
check("Intelligence Core", "sessione di discovery completata", ss.get("status") == "completed", f"{ss.get('status')}: {ss.get('error')}")
conns = j(c.get("/api/discovery/connections"))
reasons = [r for x in (conns if isinstance(conns, list) else []) for r in x.get("reliability_reasons", [])]
ev_conns = [x for x in (conns if isinstance(conns, list) else []) if x.get("sources")]
check("Confidence System", "connessione tra eventi con fonti trovata dalla discovery", ev_conns, [x.get("kind") for x in (conns if isinstance(conns, list) else [])])
check("Confidence System", "le sue motivazioni separano indipendenza, qualità, ancoraggio e contenuto",
      ev_conns and all(any(r.startswith(p_) for r in ev_conns[0]["reliability_reasons"]) for p_ in ("Indipendenza:", "Qualità:", "Ancoraggio:", "Contenuto:")), ev_conns[0]["reliability_reasons"] if ev_conns else None)
check("Confidence System", "due opere dello stesso autore (Friedman) non contano come conferme indipendenti",
      ev_conns and any("autore in comune" in r for x in ev_conns for r in x["reliability_reasons"]), [r for x in ev_conns for r in x["reliability_reasons"]][:8])
if isinstance(conns, list):
    srcs_conn = [x for x in conns if x.get("sources")]
    check("Confidence System", "nessuna connessione «alta» senza due gruppi qualificati", all(x["reliability"] != "high" or any(r.startswith("Qualità: 2") or r.startswith("Qualità: 3") for r in x["reliability_reasons"]) for x in srcs_conn), [x["reliability"] for x in srcs_conn])

# --- Studio: tracciabilità -----------------------------------------------------------------------
reps = j(c.get("/api/reports"))
rid = reps[0]["id"] if isinstance(reps, list) and reps else None
trace = c.get(f"/api/reports/{rid}/trace") if rid else None
check("Deep Research", "rapporto: tracciabilità affermazioni ↔ fonti", trace is not None and trace.status_code == 200 and "summary" in j(trace), trace.text[:200] if trace is not None else "nessun rapporto")
chk = c.get(f"/api/reports/{rid}/check") if rid else None
check("Deep Research", "rapporto: controllo di coerenza", chk is not None and chk.status_code == 200, chk.text[:200] if chk is not None else "")

ok = sum(r["ok"] for r in results)
print(f"\nTOTALE: {ok}/{len(results)} controlli superati")
json.dump(results, open(sys.argv[2] if len(sys.argv) > 2 else "e2e_results.json", "w"), ensure_ascii=False, indent=1)
