"""Componente A — NEXUS Intelligence Core.

Coordina una sessione di discovery a passi:

- guidata: comprende la domanda → individua l'ambito (eventi, serie, entità pertinenti)
  → connessioni → anomalie → ipotesi → catene causali → sintesi;
- autonoma: esamina tutto l'archivio → connessioni → anomalie → ipotesi → verifica delle
  ipotesi principali → piste di approfondimento → sintesi.

Ogni passo è registrato (esecutore, durata, conteggi). La sessione rispetta limiti di tempo,
di chiamate AI e di risultati; può essere messa in pausa, ripresa o fermata tra un passo e
l'altro. I risultati sono deduplicati con un'impronta (stesso tipo + stessi elementi).
L'AI è facoltativa: interpreta la domanda e scrive la sintesi; i rilevatori sono deterministici.
"""

from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..agents import guard, llm
from ..core.config import Settings
from ..database.base import utcnow
from ..models import (DiscoveryAnalysis, DiscoveryAnomaly, DiscoveryConnection, DiscoveryHypothesis, DiscoverySession, Entity,
                      HistoricalEvent, Relation, Series, User)
from ..research.text import strip_accents, terms
from . import anomalies as an
from . import causal, connections as cx, hypotheses as hy

STEPS = {
    "guided": ["understand", "connections", "anomalies", "hypotheses", "causal", "synthesis"],
    "autonomous": ["survey", "connections", "anomalies", "hypotheses", "verify", "leads", "synthesis"],
}
STEP_LABEL = {
    "understand": "Comprensione della domanda e ambito", "survey": "Esame delle conoscenze disponibili",
    "connections": "Discovery Engine: connessioni", "anomalies": "Anomaly Detection", "hypotheses": "Hypothesis Generator",
    "causal": "Causal Intelligence: catene nel grafo", "verify": "Verifica delle ipotesi principali",
    "leads": "Piste di approfondimento", "synthesis": "Sintesi finale",
}

# Sinonimi italiano ↔ inglese per collegare domande in italiano a dati con nomi in inglese.
SYNONYMS = {
    "inflazione": ["inflation", "prices", "cpi", "hicp"], "prezzi": ["prices", "cpi"], "tassi": ["rate", "rates", "interest", "yield"],
    "tasso": ["rate", "interest"], "interesse": ["interest"], "disoccupazione": ["unemployment"], "debito": ["debt"],
    "crisi": ["crisis", "crash"], "banca": ["bank"], "banche": ["bank", "banks"], "bancaria": ["banking", "bank"],
    "monetario": ["monetary"], "monetaria": ["monetary"], "pil": ["gdp", "growth"], "crescita": ["growth", "gdp"],
    "cambio": ["exchange", "currency"], "valute": ["currency", "exchange"], "petrolio": ["oil", "wti"], "salari": ["wages"],
    "borsa": ["stock", "equity"], "credito": ["credit", "loans"], "investimenti": ["investment"], "guerra": ["war"],
    "commercio": ["trade"], "bce": ["ecb", "refinancing", "european central bank"], "fed": ["federal", "fedfunds"],
    "politica": ["policy"], "euro": ["euro", "eur", "u2"], "italia": ["italy", "ita"], "europa": ["euro", "europe"], "finanziaria": ["financial"], "finanziarie": ["financial"], "mercati": ["markets"], "oro": ["gold"],
}

SYSTEM = (
    "Sei il coordinatore di NEXUS Discovery Intelligence. Rispondi SOLO con JSON valido. "
    "Non inventare fatti, dati o fonti: lavori esclusivamente sugli elementi forniti, citandone gli id. "
    "Le connessioni e le ipotesi sono candidate da verificare, mai scoperte dimostrate."
)


class SessionLimit(Exception):
    pass


def _terms(q: str) -> list[str]:
    base = terms(q)
    out = list(base)
    for t in base:
        out += SYNONYMS.get(strip_accents(t), [])
    return list(dict.fromkeys(out))


class Runner:
    def __init__(self, db: Session, sess: DiscoverySession, user: User, settings: Settings, client: llm.LLMClient | None):
        self.db, self.s, self.user, self.settings, self.client = db, sess, user, settings, client
        self.t0 = time.perf_counter()
        self.base_elapsed = sess.elapsed_ms or 0

    # --- infrastruttura ---------------------------------------------------------------------

    def elapsed_ms(self) -> int:
        return self.base_elapsed + int((time.perf_counter() - self.t0) * 1000)

    def check_budget(self) -> None:
        if self.elapsed_ms() > self.s.limits.get("max_seconds", 120) * 1000:
            raise SessionLimit(f"Limite di tempo raggiunto ({self.s.limits.get('max_seconds')} s).")

    def ai(self, prompt: str, max_tokens: int = 1500) -> tuple[dict, llm.LLMResult] | None:
        if not self.client or self.s.llm_calls >= self.s.limits.get("max_llm_calls", 3):
            return None
        self.s.llm_calls += 1
        res = self.client.complete(SYSTEM, prompt, max_tokens)
        return guard.parse_json(res.text), res

    def log(self, name: str, *, executor: str, summary: str, counts: dict | None = None, t0: float, status: str = "executed",
            error: str | None = None, res: llm.LLMResult | None = None) -> None:
        self.s.steps = [*self.s.steps, {
            "ordinal": len(self.s.steps) + 1, "step": name, "label": STEP_LABEL[name], "status": status, "executor": executor,
            "summary": summary[:1500], "counts": counts or {}, "error": error,
            "duration_ms": int((time.perf_counter() - t0) * 1000), "model": res.model if res else "",
            "tokens": (res.input_tokens or 0) + (res.output_tokens or 0) if res else None,
        }]

    # --- dati ------------------------------------------------------------------------------

    def data(self):
        uid = self.user.id
        sc = self.s.scope or {}
        # Caricamento in blocco delle collezioni usate dai rilevatori (evita una query per ogni evento o serie).
        events = list(self.db.scalars(select(HistoricalEvent).where(HistoricalEvent.owner_id == uid)
                                      .options(selectinload(HistoricalEvent.source_links), selectinload(HistoricalEvent.knowledge))))
        series = list(self.db.scalars(select(Series).where(Series.owner_id == uid).options(selectinload(Series.observations))))
        entities = {e.id: e for e in self.db.scalars(select(Entity).where(Entity.owner_id == uid))}
        rels = list(self.db.scalars(select(Relation).where(Relation.owner_id == uid)))
        if sc.get("restricted"):
            ev_ids, se_ids, en_ids = set(sc.get("event_ids", [])), set(sc.get("series_ids", [])), set(sc.get("entity_ids", []))
            events_in = [e for e in events if e.id in ev_ids]
            series_in = [s for s in series if s.id in se_ids]
            ent_scope = en_ids | {e.id for e in entities.values() if e.event_id in ev_ids or e.series_id in se_ids}
        else:
            events_in, series_in, ent_scope = events, series, None
        return events_in, series_in, entities, rels, ent_scope, events, series

    def save_connections(self, cands: list[cx.Candidate]) -> tuple[int, int]:
        new = known = 0
        cap = self.s.limits.get("max_items", 60)
        for c in sorted(cands, key=lambda x: -x.score)[:cap]:
            ex = self.db.scalar(select(DiscoveryConnection).where(DiscoveryConnection.owner_id == self.user.id, DiscoveryConnection.fingerprint == c.fingerprint))
            if ex:
                known += 1
                continue
            self.db.add(DiscoveryConnection(
                owner_id=self.user.id, session_id=self.s.id, fingerprint=c.fingerprint, kind=c.kind, title=c.title[:500], elements=c.elements,
                period=c.period[:60], evidence=c.evidence, sources=c.source_ids, reliability=c.reliability, reliability_reasons=c.reliability_reasons,
                explanation=c.explanation, caveats=c.caveats, score=round(float(c.score), 4)))
            new += 1
        self.db.flush()
        return new, known

    def save_anomalies(self, cands: list[an.AnomalyCandidate]) -> tuple[int, int]:
        new = known = 0
        cap = self.s.limits.get("max_items", 60)
        for a in sorted(cands, key=lambda x: -x.relevance)[:cap]:
            if self.db.scalar(select(DiscoveryAnomaly).where(DiscoveryAnomaly.owner_id == self.user.id, DiscoveryAnomaly.fingerprint == a.fingerprint)):
                known += 1
                continue
            self.db.add(DiscoveryAnomaly(
                owner_id=self.user.id, session_id=self.s.id, fingerprint=a.fingerprint, kind=a.kind, title=a.title[:500], what_changed=a.what_changed,
                reference=a.reference, period=a.period[:60], data=a.data, alternatives=a.alternatives, refs=a.refs,
                relevance=round(float(a.relevance), 3), verifiability=a.verifiability))
            new += 1
        self.db.flush()
        return new, known

    # --- passi -----------------------------------------------------------------------------

    def step_understand(self, t0: float) -> None:
        q = self.s.query
        words = _terms(q)
        executor, res, concepts = "local", None, []
        try:
            out = self.ai(f"Domanda: {q}\nRestituisci {{\"concepts\": [max 12 concetti chiave e sinonimi in italiano E inglese, "
                          f"es. nomi di indicatori, istituzioni, eventi]}}") if self.client else None
            if out:
                data, res = out
                concepts = [str(x)[:60] for x in data.get("concepts", [])][:12]
                executor = "ai"
        except (llm.ProviderError, guard.ParseError) as exc:
            self.log("understand", executor="ai", status="failed", summary="Interpretazione AI non riuscita: uso l'analisi locale.", error=str(exc), t0=t0)
            t0 = time.perf_counter()
        for c in concepts:
            words += _terms(c)
        wset = set(dict.fromkeys(words))
        events, series, entities, *_ = self.data()

        def hit(text: str) -> int:
            return len(wset & set(terms(text)))

        ev_ids = [e.id for e in events if hit(" ".join([e.title, e.description, e.causes, e.consequences, " ".join(e.categories or []),
                                                          " ".join(e.countries or [])])) >= 1]
        se_ids = [s.id for s in series if hit(f"{s.name} {s.category} {s.description[:300]}") >= 1]
        en_ids = [e.id for e in entities.values() if e.event_id is None and hit(" ".join([e.name, *(e.aliases or [])])) >= 1]
        restricted = bool(ev_ids or se_ids or en_ids)
        self.s.scope = {"terms": list(wset)[:40], "concepts": concepts, "event_ids": ev_ids, "series_ids": se_ids, "entity_ids": en_ids,
                        "restricted": restricted}
        summary = (f"Ambito: {len(ev_ids)} eventi, {len(se_ids)} serie, {len(en_ids)} entità pertinenti." if restricted else
                   "Nessun elemento dell'archivio corrisponde alla domanda: analizzo l'intero archivio.")
        self.log("understand", executor=executor, summary=summary, counts={"events": len(ev_ids), "series": len(se_ids), "entities": len(en_ids)}, t0=t0, res=res)

    def step_survey(self, t0: float) -> None:
        events, series, entities, rels, *_ = self.data()
        self.s.scope = {"restricted": False}
        self.log("survey", executor="local", t0=t0,
                 summary=f"Archivio: {len(events)} eventi, {len(series)} serie, {len(entities)} entità, {len(rels)} relazioni.",
                 counts={"events": len(events), "series": len(series), "entities": len(entities), "relations": len(rels)})

    def step_connections(self, t0: float) -> None:
        events, series, entities, rels, ent_scope, _, _ = self.data()
        ent_of_event = {e.event_id: e.id for e in entities.values() if e.event_id}
        event_of_ent: dict[int, int] = {}
        for ev_id, en_id in ent_of_event.items():  # come prima: il primo evento che punta all'entità
            event_of_ent.setdefault(en_id, ev_id)
        known = set()
        for r in rels:
            a = ("event", event_of_ent[r.source_entity_id]) if r.source_entity_id in event_of_ent else ("entity", r.source_entity_id)
            b = ("event", event_of_ent[r.target_entity_id]) if r.target_entity_id in event_of_ent else ("entity", r.target_entity_id)
            known.add(frozenset((a, b)))
        cands = cx.event_connections(self.db, events, known)
        cands += cx.graph_connections(self.db, self.user, entities, rels, ent_scope)
        cands += cx.event_data_connections(self.db, events, series, require_country=not (self.s.scope or {}).get("restricted"))
        self.check_budget()
        cands += cx.series_connections(self.db, series[:25])
        new, dup = self.save_connections(cands)
        by_kind: dict[str, int] = {}
        for c in cands:
            by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
        self.log("connections", executor="local", t0=t0, counts={"new": new, "already_known": dup, **by_kind},
                 summary=f"{len(cands)} connessioni candidate ({new} nuove, {dup} già individuate in precedenza)." if cands else
                 "Nessuna connessione: servono più eventi con attori o fonti, più relazioni nel grafo o serie con almeno 12 osservazioni.")

    def step_anomalies(self, t0: float) -> None:
        events, series, entities, rels, _, all_events, _ = self.data()
        skipped: dict = {}
        cands = an.series_anomalies(series, all_events, skipped) + an.source_discrepancies(series, skipped)
        cands += an.chronology_issues(self.db, events, rels, entities)
        new, dup = self.save_anomalies(cands)
        note = f" Esclusi per dati insufficienti: {', '.join(f'{k} {v}' for k, v in skipped.items())}." if skipped else ""
        self.log("anomalies", executor="local", t0=t0, counts={"new": new, "already_known": dup, **skipped},
                 summary=(f"{len(cands)} anomalie ({new} nuove)." if cands else "Nessuna anomalia rilevata.") + note)

    def _session_connections(self) -> list[DiscoveryConnection]:
        return list(self.db.scalars(select(DiscoveryConnection).where(DiscoveryConnection.owner_id == self.user.id,
                                                                      DiscoveryConnection.session_id == self.s.id)
                                    .order_by(DiscoveryConnection.score.desc())))

    def step_hypotheses(self, t0: float) -> None:
        created = 0
        for c in self._session_connections()[:15]:
            if c.status == "dismissed":
                continue
            if self.db.scalar(select(DiscoveryHypothesis).where(DiscoveryHypothesis.owner_id == self.user.id, DiscoveryHypothesis.fingerprint == c.fingerprint)):
                continue
            h = hy.from_connection(self.db, c)
            self.db.add(DiscoveryHypothesis(owner_id=self.user.id, session_id=self.s.id, connection_id=c.id, fingerprint=c.fingerprint, origin="rules", **h))
            created += 1
        self.db.flush()
        self.log("hypotheses", executor="local", t0=t0, counts={"created": created},
                 summary=f"{created} ipotesi generate, tutte nello stato «da verificare»." if created else "Nessuna nuova ipotesi: non ci sono connessioni nuove.")

    def step_causal(self, t0: float) -> None:
        _, _, entities, rels, ent_scope, _, _ = self.data()
        if not ent_scope:
            self.log("causal", executor="local", t0=t0, summary="Meno di due entità nell'ambito: nessuna catena da ricostruire.", status="skipped")
            return
        linked = {r.source_entity_id for r in rels} | {r.target_entity_id for r in rels}
        ids = [i for i in ent_scope if i in linked][:6]
        found = 0
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                for x, y in ((a, b), (b, a)):
                    res = causal.chains(self.db, self.user, x, y, max_depth=4, limit=5)
                    if res["paths"]:
                        found += 1
                        self.db.add(DiscoveryAnalysis(owner_id=self.user.id, session_id=self.s.id, kind="causal_chain",
                                                      title=f"{res['start']} → {res['end']}", params={"start": x, "end": y}, result=res))
        self.db.flush()
        self.log("causal", executor="local", t0=t0, counts={"chains": found},
                 summary=f"{found} catene orientate trovate tra le entità dell'ambito." if found else "Nessuna catena orientata tra le entità dell'ambito.")

    def step_verify(self, t0: float) -> None:
        hyps = list(self.db.scalars(select(DiscoveryHypothesis).where(DiscoveryHypothesis.owner_id == self.user.id, DiscoveryHypothesis.session_id == self.s.id,
                                                                      DiscoveryHypothesis.status == "to_verify").limit(5)))
        for h in hyps:
            self.check_budget()
            c = self.db.get(DiscoveryConnection, h.connection_id) if h.connection_id else None
            checks = hy.verify(self.db, self.user, self.settings, c)
            h.verification = [{"at": utcnow().isoformat(), "checks": checks, "suggested": hy.suggested_outcome(checks)}]
            h.status = "verifying"
        self.db.flush()
        self.log("verify", executor="local", t0=t0, counts={"verified": len(hyps)},
                 summary=f"Verifica automatica su {len(hyps)} ipotesi: ora «in verifica», in attesa della tua decisione." if hyps else "Nessuna ipotesi da verificare.")

    def leads(self) -> list[dict]:
        out: list[dict] = []
        for h in self.db.scalars(select(DiscoveryHypothesis).where(DiscoveryHypothesis.owner_id == self.user.id, DiscoveryHypothesis.session_id == self.s.id).limit(6)):
            for m in h.missing[:1]:
                out.append({"kind": "missing", "text": f"{m} — per l'ipotesi «{h.title[:120]}»", "ref": {"hypothesis_id": h.id}})
        events, *_ = self.data()
        for e in events:
            if not e.source_links:
                out.append({"kind": "sources", "text": f"Aggiungi una fonte all'evento «{e.title}»: oggi nessuna connessione che lo riguarda può superare l'affidabilità bassa.",
                            "ref": {"event_id": e.id}})
        for a in self.db.scalars(select(DiscoveryAnomaly).where(DiscoveryAnomaly.owner_id == self.user.id, DiscoveryAnomaly.session_id == self.s.id).limit(4)):
            out.append({"kind": "anomaly", "text": f"Spiega l'anomalia: {a.title}", "ref": {"anomaly_id": a.id}})
        sc = self.s.scope or {}
        if sc.get("terms") and not sc.get("restricted"):
            out.append({"kind": "data", "text": f"L'archivio non contiene materiale su: {', '.join(sc['terms'][:6])}. Importa serie, documenti o eventi pertinenti.", "ref": {}})
        return out[:15]

    def step_leads(self, t0: float) -> None:
        leads = self.leads()
        self.s.result = {**self.s.result, "leads": leads}
        self.log("leads", executor="local", t0=t0, counts={"leads": len(leads)}, summary=f"{len(leads)} piste di approfondimento.")

    def step_synthesis(self, t0: float) -> None:
        conns = self._session_connections()
        hyps = list(self.db.scalars(select(DiscoveryHypothesis).where(DiscoveryHypothesis.session_id == self.s.id)))
        anoms = list(self.db.scalars(select(DiscoveryAnomaly).where(DiscoveryAnomaly.session_id == self.s.id).order_by(DiscoveryAnomaly.relevance.desc())))
        chains = list(self.db.scalars(select(DiscoveryAnalysis).where(DiscoveryAnalysis.session_id == self.s.id)))
        leads = self.s.result.get("leads") or self.leads()
        local = [f"{len(conns)} connessioni nuove, {len(hyps)} ipotesi, {len(anoms)} anomalie, {len(chains)} catene causali."]
        if conns:
            local.append("Connessione più forte: " + conns[0].title + f" ({cx.KIND_LABEL[conns[0].kind]}, affidabilità {conns[0].reliability}).")
        if anoms:
            local.append("Anomalia più rilevante: " + anoms[0].title + ".")
        if not (conns or anoms or chains):
            local.append("L'archivio non contiene ancora abbastanza materiale collegato per produrre risultati: vedi le piste di approfondimento.")
        synthesis = {"text": " ".join(local), "executor": "local", "references": []}
        res = None
        if self.client and (conns or anoms):
            items = {f"C{c.id}": f"{c.title} — {c.explanation[:300]}" for c in conns[:10]}
            items.update({f"A{a.id}": f"{a.title} — {a.what_changed}" for a in anoms[:6]})
            try:
                out = self.ai("Elementi individuati (id: descrizione):\n" + json.dumps(items, ensure_ascii=False) +
                              f"\nDomanda: {self.s.query or '(discovery autonoma)'}\n"
                              "Scrivi {\"summary\": \"sintesi in italiano, max 8 frasi, che cita gli id tra parentesi quadre e "
                              "distingue fatti, interpretazioni e ipotesi\", \"references\": [id usati]}", max_tokens=1200)
                if out:
                    data, res = out
                    refs = [r for r in data.get("references", []) if r in items]
                    text = str(data.get("summary", ""))[:4000]
                    if text and refs:
                        synthesis = {"text": text, "executor": "ai", "references": refs,
                                     "note": "Sintesi scritta da un modello AI sugli elementi trovati: verifica ogni affermazione sugli elementi citati."}
            except (llm.ProviderError, guard.ParseError) as exc:
                synthesis["note"] = f"Sintesi AI non riuscita ({exc}); mostrata la sintesi locale."
        self.s.result = {**self.s.result, "synthesis": synthesis, "leads": leads,
                         "counts": {"connections": len(conns), "hypotheses": len(hyps), "anomalies": len(anoms), "chains": len(chains)}}
        self.log("synthesis", executor=synthesis["executor"], t0=t0, summary=synthesis["text"][:400], res=res)


def execute(db: Session, sess: DiscoverySession, user: User, settings: Settings, client: llm.LLMClient | None) -> DiscoverySession:
    r = Runner(db, sess, user, settings, client)
    steps = STEPS[sess.mode]
    sess.status, sess.started_at = "running", sess.started_at or utcnow()
    db.commit()
    try:
        while sess.cursor < len(steps):
            db.refresh(sess)
            if sess.status in ("paused", "stopped"):
                return sess  # pausa o arresto richiesti dall'utente tra un passo e l'altro
            r.check_budget()
            name = steps[sess.cursor]
            t0 = time.perf_counter()
            getattr(r, f"step_{name}")(t0)
            sess.cursor += 1
            sess.elapsed_ms = r.elapsed_ms()
            db.commit()
        sess.status, sess.finished_at = "completed", utcnow()
    except SessionLimit as exc:
        db.rollback()
        db.refresh(sess)
        sess.status, sess.error, sess.finished_at = "stopped", str(exc), utcnow()
    except Exception as exc:  # errore imprevisto: la sessione si ferma con il messaggio, i risultati già salvati restano
        db.rollback()
        db.refresh(sess)
        sess.status, sess.error, sess.finished_at = "failed", f"{type(exc).__name__}: {exc}"[:2000], utcnow()
    sess.elapsed_ms = r.elapsed_ms()
    db.commit()
    return sess
