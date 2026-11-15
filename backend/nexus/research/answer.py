"""Risposte basate esclusivamente sui passaggi recuperati (modalità locale).

Senza un provider AI NEXUS non genera testo: estrae dai documenti le frasi più
pertinenti e le restituisce *testualmente*, con documento, pagina/locator e
livello di supporto. Ogni affermazione è classificata:

- ``documented_fact``: frase riportata alla lettera da un documento importato.
  Indica che il documento AFFERMA qualcosa, non che sia vero: l'attendibilità
  dipende dalla fonte.
- ``missing``: nessun passaggio pertinente trovato.

Interpretazioni, ipotesi e stime richiedono un modello AI (Fase 5) e sono
sempre etichettate come tali.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chunking import split_sentences
from .text import stem, terms

CLAIM_TYPES = ("documented_fact", "interpretation", "hypothesis", "estimate", "missing")


def concepts(query: str) -> list[tuple[str, set[str]]]:
    """I concetti della domanda: ogni termine con le sue forme nell'altra lingua («plastica» ↔ «plastic»)."""
    from .crosslang import translations

    out = []
    for t in dict.fromkeys(terms(query)):
        forms = {stem(t)} | {stem(w) for tr in translations(t) for w in terms(tr)}
        out.append((t, forms))
    return out


def concept_hits(query: str, text: str) -> tuple[list[str], list[str]]:
    """Concetti della domanda presenti e assenti nel testo (in qualsiasi delle due lingue)."""
    words = {stem(w) for w in terms(text)}
    found, missing = [], []
    for t, forms in concepts(query):
        (found if any(f in words or any(w.startswith(f) for w in words if len(f) >= 5) for f in forms) else missing).append(t)
    return found, missing


def coverage(query: str, passage: str) -> float:
    """Copertura: quota dei concetti della domanda presenti nel testo (non dice se il testo risponde)."""
    found, missing = concept_hits(query, passage)
    n = len(found) + len(missing)
    return len(found) / n if n else 0.0


def sentence_support(query: str, passage: str) -> tuple[float, str]:
    """Supporto: la frase migliore del passaggio e la quota di concetti che copre DA SOLA.

    Più severo della copertura: termini sparsi in un passaggio lungo non bastano, devono comparire
    insieme nella stessa frase. Resta una stima lessicale: la verifica del significato richiede l'AI.
    """
    best, best_s = 0.0, ""
    for s in split_sentences(passage):
        if len(s) < 25:
            continue
        c = coverage(query, s)
        if c > best:
            best, best_s = c, s
    return best, best_s


def support_level(cov: float) -> str:
    if cov >= 0.75:
        return "strong"
    if cov >= 0.4:
        return "partial"
    if cov > 0:
        return "weak"
    return "none"


@dataclass
class Passage:
    chunk_id: int
    document_id: int
    document_title: str
    page: int | None
    locator: str
    text: str
    score: float
    injection_flag: bool
    source_label: str


def citation_of(p: Passage) -> str:
    where = f"p. {p.page}" if p.page else (p.locator or "")
    return f"{p.document_title}" + (f", {where}" if where else "")


UNSUPPORTED_TEXT = ("Le fonti trovate non sostengono una risposta: contengono alcuni termini della domanda, "
                    "ma nessuna frase ne riunisce i concetti principali.")


def extract_claims(query: str, passages: list[Passage], max_claims: int = 5) -> list[dict]:
    candidates = []
    for p in passages:
        for s in split_sentences(p.text):
            if len(s) < 25:
                continue
            cov = coverage(query, s)
            if cov > 0:
                candidates.append((cov, p.score, s, p))
    candidates.sort(key=lambda x: (-x[0], -x[1]))
    claims, seen = [], set()
    n_concepts = len(concepts(query))
    # Una frase «sostiene» solo se riunisce almeno metà dei concetti (e almeno 2 se la domanda ne ha più di uno).
    need = 0.5 if n_concepts <= 1 else max(0.5, 2 / n_concepts)
    for cov, _, sentence, p in candidates:
        if cov < need:
            continue
        key = sentence.lower()[:120]
        if key in seen:
            continue
        seen.add(key)
        claims.append(
            {
                "type": "documented_fact",
                "text": sentence,
                "support": support_level(cov),
                "coverage": round(cov, 2),
                "evidence": [p.chunk_id],
                "citations": [citation_of(p)],
                "note": "Citazione testuale: indica ciò che il documento afferma, non ne garantisce la veridicità.",
            }
        )
        if len(claims) >= max_claims:
            break
    if not claims and candidates:
        found, missing = concept_hits(query, " ".join(c[2] for c in candidates[:10]))
        claims.append({
            "type": "missing", "text": UNSUPPORTED_TEXT, "support": "none", "coverage": round(candidates[0][0], 2), "evidence": [],
            "citations": [],
            "note": (f"Concetti trovati: {', '.join(found) or '—'}; mancanti: {', '.join(missing) or '—'}. "
                     "I passaggi sotto sono correlati, non una risposta: riformula la domanda o importa fonti pertinenti."),
        })
    if not claims:
        claims.append(
            {
                "type": "missing",
                "text": "Nessun passaggio dell'archivio risponde alla domanda.",
                "support": "none",
                "coverage": 0.0,
                "evidence": [],
                "citations": [],
                "note": "Dato mancante: importa documenti pertinenti o riformula la domanda.",
            }
        )
    return claims
