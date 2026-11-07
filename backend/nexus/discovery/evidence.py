"""Classificazione delle informazioni e valutazione delle fonti.

Criteri: autorevolezza, originalità (primaria/secondaria), data di pubblicazione,
pertinenza, conferme indipendenti, contraddizioni. Le fonti che riprendono la stessa
fonte primaria (campo «fonte primaria» in bibliografia) o la stessa opera (DOI/ISBN/URL)
contano come una sola conferma.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..models import Source

CLAIM_TYPES = {
    "documented_fact": "Fatto documentato",
    "interpretation": "Interpretazione",
    "hypothesis": "Ipotesi",
    "forecast": "Previsione",
    "unverified": "Informazione non verificata",
}

_OFFICIAL = re.compile(
    r"\b(bank|banca|banco|bundesbank|reserve|central|istat|eurostat|statistic|statist|ministr|commission|commissione|"
    r"office|ufficio|government|governo|parliament|parlamento|imf|oecd|ocse|world bank|united nations|nazioni unite|"
    r"university press|universit|institute|istituto|federal|european union|unione europea)\b",
    re.I,
)
PRIMARY_TYPES = {"archive", "dataset", "document"}
SECONDARY_TYPES = {"book", "article", "chapter"}
VERIFIED = {"verified_user", "verified_registry"}


def work_key(s: Source) -> str:
    """Identità dell'opera: due schede della stessa opera non sono conferme distinte."""
    if s.doi:
        return f"doi:{s.doi.lower()}"
    if s.isbn:
        return f"isbn:{re.sub(r'[^0-9X]', '', s.isbn.upper())}"
    if s.url:
        u = urlparse(s.url)
        return f"url:{u.netloc.lower().removeprefix('www.')}{u.path.rstrip('/')}"
    return f"title:{re.sub(r'[^a-z0-9]+', ' ', s.title.lower()).strip()}|{s.year or ''}"


def root_of(db: Session, s: Source) -> Source:
    """Risale la catena delle fonti primarie dichiarate (senza cicli: garantito alla creazione)."""
    seen = set()
    cur = s
    while cur.primary_source_id and cur.primary_source_id not in seen:
        seen.add(cur.id)
        nxt = db.get(Source, cur.primary_source_id)
        if nxt is None:
            break
        cur = nxt
    return cur


def independent_groups(db: Session, sources: list[Source]) -> list[list[Source]]:
    """Raggruppa le fonti per origine comune (fonte primaria dichiarata o stessa opera)."""
    groups: dict[str, list[Source]] = {}
    for s in sources:
        groups.setdefault(work_key(root_of(db, s)), []).append(s)
    return list(groups.values())


def assess_source(s: Source, event_year: int | None = None) -> dict:
    """Valutazione di una singola fonte, con le ragioni di ogni giudizio."""
    reasons = []
    official = bool(_OFFICIAL.search(" ".join([s.publisher or "", s.container or "", s.title or ""])))
    if s.verification_status == "not_found":
        authority = "low"
        reasons.append("Identificativo non trovato nel registro")
    elif s.verification_status == "verified_registry" or (official and s.source_type in PRIMARY_TYPES | {"book", "article"}):
        authority = "high"
        reasons.append("Verificata su registro" if s.verification_status == "verified_registry" else "Editore o ente istituzionale")
    elif s.source_type in SECONDARY_TYPES:
        authority = "medium"
        reasons.append("Pubblicazione editoriale o accademica")
    else:
        authority = "low"
        reasons.append("Pagina web o tipo non specificato")
    originality = "primary" if s.source_type in PRIMARY_TYPES else "secondary" if s.source_type in SECONDARY_TYPES else "unknown"
    if s.primary_source_id:
        originality = "derived"
        reasons.append("Riprende un'altra fonte (indicata in bibliografia)")
    timing = None
    if event_year is not None and s.year is not None:
        gap = s.year - event_year
        timing = "before" if gap < 0 else "contemporary" if gap <= 2 else "later"
        if gap < 0:
            reasons.append("Pubblicata prima dell'evento: può documentare il contesto, non l'evento")
    verified = s.verification_status in VERIFIED
    if not verified:
        reasons.append("Non verificata")
    score = {"high": 3, "medium": 2, "low": 1}[authority] + (1 if verified else 0) + (1 if originality == "primary" else 0)
    return {"source_id": s.id, "authority": authority, "originality": originality, "timing": timing, "verified": verified,
            "year": s.year, "score": score, "reasons": reasons}


def grade(db: Session, sources: list[Source], *, contradictions: int = 0, event_year: int | None = None,
          base: str | None = None) -> tuple[str, list[str], list[dict]]:
    """Affidabilità complessiva (low/medium/high) di un insieme di fonti, con motivazioni."""
    assessed = [assess_source(s, event_year) for s in sources]
    groups = independent_groups(db, sources) if sources else []
    n_ind = len(groups)
    strong = sum(1 for a in assessed if a["score"] >= 4)
    reasons = []
    if not sources:
        level = base or "low"
        reasons.append("Nessuna fonte bibliografica collegata")
    else:
        reasons.append(f"{len(sources)} fonti, {n_ind} indipendenti" + (" (alcune riprendono la stessa origine)" if n_ind < len(sources) else ""))
        if n_ind >= 2 and strong >= 2:
            level = "high"
        elif strong >= 1 or n_ind >= 2:
            level = "medium"
        else:
            level = "low"
        unver = sum(1 for a in assessed if not a["verified"])
        if unver:
            reasons.append(f"{unver} fonti non verificate")
    if contradictions:
        reasons.append(f"{contradictions} contraddizioni rilevate")
        level = {"high": "medium", "medium": "low", "low": "low"}[level]
    return level, reasons, assessed
