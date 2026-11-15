"""Aiuti AI controllati: revisione di un capitolo, traduzione della domanda, proposte estratte da un documento.

Regole comuni:
- l'AI non scrive testo al posto dell'utente: segnala, traduce o propone;
- ogni segnalazione o proposta deve citare alla lettera il testo da cui nasce: ciò che non si ritrova
  nel testo viene scartato (nessuna citazione inventata);
- senza AI configurata la revisione usa controlli locali e le altre funzioni lo dichiarano.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import guard, llm
from ..core.config import Settings
from ..core.errors import ValidationFailedError
from ..models import DocumentChunk, Source, User
from ..models.graph import ENTITY_TYPES, RELATION_TYPES
from ..research.safety import UNTRUSTED_POLICY, wrap_untrusted
from ..studio.citations import CITE_RX
from . import activity, ai

SYSTEM = ("Sei un assistente di ricerca di NEXUS per studenti universitari. Rispondi SOLO con JSON valido, in italiano. "
          "Non inventare fatti, fonti, date o numeri. " + UNTRUSTED_POLICY)

_SENT = re.compile(r"[^.!?\n]+[.!?]?")
_STRONG = re.compile(r"\b(dimostra(?:no)?|prova(?:no)? che|certamente|sicuramente|senza dubbio|sempre|mai|tutti|nessuno|"
                     r"inevitabilmente|indiscutibil\w+|causato|ha causato|hanno causato)\b", re.IGNORECASE)
_NUM = re.compile(r"\d")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _client(db: Session, user: User, settings: Settings) -> llm.LLMClient | None:
    try:
        return ai.client_for(db, user, settings)
    except llm.ProviderError:
        return None


# --- 1. Revisione di un capitolo ------------------------------------------------------------


def _local_review(body: str) -> list[dict]:
    issues = []
    for m in _SENT.finditer(body):
        s = m.group(0).strip()
        if len(s) < 25 or s.startswith("#") or CITE_RX.search(s):
            continue
        if _NUM.search(CITE_RX.sub("", s)):
            issues.append({"kind": "uncited", "quote": s, "comment": "Contiene un dato numerico senza citazione: indica la fonte con [@id]."})
        elif _STRONG.search(s):
            issues.append({"kind": "overclaim", "quote": s,
                           "comment": f"Formulazione forte («{_STRONG.search(s).group(0)}») senza citazione: va sostenuta da una fonte o attenuata."})
    return issues[:20]


def review_section(db: Session, user: User, settings: Settings, report_id: int, section_id: int) -> dict:
    from .studio import get_report

    r = get_report(db, user, report_id, "viewer")
    sec = next((s for s in r.sections if s.id == section_id), None)
    if sec is None:
        raise ValidationFailedError("Sezione inesistente.")
    body = sec.body or ""
    if len(body.strip()) < 40:
        raise ValidationFailedError("La sezione è troppo breve per una revisione: scrivi almeno qualche frase.")
    local = _local_review(body)
    client = _client(db, user, settings)
    if client is None:
        return {"mode": "local", "provider": "none", "issues": local,
                "note": "Controlli locali: frasi con numeri o affermazioni forti senza citazione. Per una revisione più completa attiva l'AI in Sistema."}
    ids = sorted({int(m.group(1)) for m in CITE_RX.finditer(body)})
    srcs = {s.id: s for s in db.scalars(select(Source).where(Source.id.in_(ids)))} if ids else {}
    from ..research.citations import format_citation

    cited = "\n".join(f"[@{i}] {format_citation(srcs[i])}" for i in ids if i in srcs) or "(nessuna fonte citata)"
    prompt = (
        "Rivedi questo capitolo di una tesi. NON riscriverlo. Segnala solo problemi concreti:\n"
        "- uncited: affermazione fattuale o numero senza citazione [@id];\n"
        "- overclaim: affermazione più forte di quanto una fonte possa sostenere (causalità, generalizzazioni);\n"
        "- inconsistency: contraddizioni interne al testo (date, cifre, nomi);\n"
        "- clarity: frase ambigua o poco chiara.\n"
        'Rispondi con {"issues": [{"kind": "...", "quote": "frase copiata ALLA LETTERA dal testo", "comment": "perché, in una frase"}]}, '
        "massimo 12 voci. Se non ci sono problemi, lista vuota.\n\n"
        f"Fonti citate nel capitolo:\n{cited}\n\n" + wrap_untrusted("T", sec.title, body[:14000])
    )
    try:
        res = client.complete(SYSTEM, prompt, 2500)
        data = guard.parse_json(res.text)
    except (llm.ProviderError, guard.ParseError) as exc:
        return {"mode": "local", "provider": "none", "issues": local, "note": f"AI non disponibile ({exc}): mostrati i controlli locali."}
    nb = _norm(body)
    issues, dropped = [], 0
    for it in (data.get("issues") or [])[:20]:
        if not isinstance(it, dict):
            continue
        q, kind = str(it.get("quote", "")).strip(), str(it.get("kind", ""))
        if kind not in ("uncited", "overclaim", "inconsistency", "clarity") or len(q) < 8 or _norm(q) not in nb:
            dropped += 1  # citazione non presente nel testo: scartata
            continue
        issues.append({"kind": kind, "quote": q, "comment": str(it.get("comment", ""))[:500]})
    seen = {_norm(i["quote"]) for i in issues}
    issues += [i for i in local if _norm(i["quote"]) not in seen]
    activity.record(db, user=user, actor="ai", action="studio.review", entity_type="report", entity_id=r.id,
                    summary=f"Revisione AI della sezione «{sec.title[:60]}» con {client.provider}")
    db.commit()
    note = "Segnalazioni dell'AI verificate sul testo (ogni frase citata esiste nel capitolo), più i controlli locali. Decidi tu cosa cambiare."
    if dropped:
        note += f" {dropped} segnalazioni scartate perché citavano frasi non presenti nel testo."
    return {"mode": "ai", "provider": client.provider, "model": client.model, "issues": issues[:25], "note": note}


# --- 2. Traduzione della domanda --------------------------------------------------------------


def translate_query(client: llm.LLMClient | None, q: str) -> list[str]:
    """La domanda in inglese (o in italiano se è in inglese), per cercare anche i documenti nell'altra lingua."""
    if client is None or not q.strip():
        return []
    try:
        res = client.complete(SYSTEM, 'Traduci questa ricerca: se è in italiano in inglese, se è in inglese in italiano. '
                                      'Usa i termini tecnici del settore. Rispondi con {"translations": ["..."]} (massimo 2 varianti brevi).\n'
                                      + wrap_untrusted("Q", "ricerca", q[:500]), 300)
        data = guard.parse_json(res.text)
    except (llm.ProviderError, guard.ParseError):
        return []
    out = [str(t).strip()[:300] for t in (data.get("translations") or []) if str(t).strip()]
    return [t for t in out if _norm(t) != _norm(q)][:2]


# --- 3. Proposte da un documento --------------------------------------------------------------

_YEAR = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")


def extract_from_document(db: Session, user: User, settings: Settings, document_id: int) -> dict:
    from .documents import get_document

    doc = get_document(db, user, document_id)
    client = _client(db, user, settings)
    if client is None:
        raise ValidationFailedError("Le proposte dai documenti richiedono l'AI: attivala in Sistema (o chiedi all'amministratore l'AI condivisa).")
    chunks = list(db.scalars(select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.ordinal)))
    if not chunks:
        raise ValidationFailedError("Il documento non contiene testo estratto.")
    # Prima i passaggi con date, poi gli altri, fino a ~12.000 caratteri.
    ranked = sorted(chunks, key=lambda c: (-len(_YEAR.findall(c.text)), c.ordinal))
    picked, size = [], 0
    for c in ranked:
        if size + len(c.text) > 12000:
            continue
        picked.append(c)
        size += len(c.text)
    picked.sort(key=lambda c: c.ordinal)
    ev = {f"P{i}": c for i, c in enumerate(picked, start=1)}
    block = "\n".join(wrap_untrusted(k, c.locator or f"segmento {c.ordinal}", c.text) for k, c in ev.items())
    prompt = (
        "Dai passaggi seguenti proponi elementi per l'archivio storico dell'utente. Solo ciò che i passaggi affermano esplicitamente.\n"
        '{"events": [{"title": "...", "start_year": 1973, "end_year": null, "countries": ["..."], "description": "una frase", "evidence": "P1", "quote": "frase copiata ALLA LETTERA"}],\n'
        ' "entities": [{"name": "...", "entity_type": "' + "|".join(t for t in ENTITY_TYPES if t != "event") + '", "evidence": "P2", "quote": "..."}],\n'
        ' "relations": [{"source": "nome entità o titolo evento", "target": "...", "relation_type": "' + "|".join(RELATION_TYPES) + '", "evidence": "P3", "quote": "..."}]}\n'
        "Massimo 8 eventi, 12 entità, 8 relazioni. Titoli in italiano.\n\n" + block
    )
    try:
        res = client.complete(SYSTEM, prompt, 3500)
        data = guard.parse_json(res.text)
    except (llm.ProviderError, guard.ParseError) as exc:
        raise ValidationFailedError(f"Proposte AI non disponibili: {exc}") from exc

    def anchor(it: dict) -> DocumentChunk | None:
        c = ev.get(str(it.get("evidence", "")))
        q = str(it.get("quote", "")).strip()
        return c if c is not None and len(q) >= 8 and _norm(q) in _norm(c.text) else None

    out: dict[str, list] = {"events": [], "entities": [], "relations": []}
    dropped = 0
    for it in (data.get("events") or [])[:8]:
        c = anchor(it) if isinstance(it, dict) else None
        try:
            y = int(it.get("start_year")) if c else None
            ye = int(it["end_year"]) if c and it.get("end_year") not in (None, "") else None
        except (TypeError, ValueError):
            y = None
        if c is None or y is None or not (-3000 <= y <= 2100) or (ye is not None and ye < y):
            dropped += 1
            continue
        out["events"].append({"title": str(it.get("title", ""))[:300], "start_year": y, "end_year": ye,
                              "countries": [str(x)[:120] for x in (it.get("countries") or [])][:10],
                              "description": str(it.get("description", ""))[:1000], "quote": str(it["quote"]).strip(),
                              "chunk_id": c.id, "locator": c.locator})
    for it in (data.get("entities") or [])[:12]:
        c = anchor(it) if isinstance(it, dict) else None
        if c is None or it.get("entity_type") not in ENTITY_TYPES or it.get("entity_type") == "event" or not str(it.get("name", "")).strip():
            dropped += 1
            continue
        out["entities"].append({"name": str(it["name"]).strip()[:200], "entity_type": it["entity_type"], "quote": str(it["quote"]).strip(),
                                "chunk_id": c.id, "locator": c.locator})
    for it in (data.get("relations") or [])[:8]:
        c = anchor(it) if isinstance(it, dict) else None
        if c is None or it.get("relation_type") not in RELATION_TYPES or not it.get("source") or not it.get("target"):
            dropped += 1
            continue
        out["relations"].append({"source": str(it["source"])[:200], "target": str(it["target"])[:200], "relation_type": it["relation_type"],
                                 "quote": str(it["quote"]).strip(), "chunk_id": c.id, "locator": c.locator})
    activity.record(db, user=user, actor="ai", action="documents.extract", entity_type="document", entity_id=doc.id,
                    summary=f"Proposte AI da «{doc.title[:60]}»: {len(out['events'])} eventi, {len(out['entities'])} entità, {len(out['relations'])} relazioni")
    db.commit()
    note = ("Proposte dell'AI, ciascuna con il passaggio che la sostiene: nulla è salvato finché non lo aggiungi tu. "
            "Gli eventi aggiunti restano «da verificare».")
    if dropped:
        note += f" {dropped} proposte scartate perché il passaggio citato non si ritrova nel documento o i dati non erano validi."
    return {"provider": client.provider, "model": client.model, "document_id": doc.id, **out, "note": note}
