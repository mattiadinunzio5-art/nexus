"""Classificazione delle informazioni e valutazione delle fonti (Confidence System).

Si valutano dimensioni distinte, ognuna con la sua motivazione, senza fonderle in un solo voto:

* **Identità e metadati** — l'opera esiste ed è descritta correttamente? Lo dice il registro esterno
  (Crossref per i DOI) oppure l'utente che dichiara di averla controllata sull'originale. NON dice nulla
  sul contenuto: un DOI confermato non conferma l'affermazione.
* **Autorevolezza** — tipo di pubblicazione ed editore/ente (letti da editore e rivista, mai dal titolo).
* **Originalità** — primaria, secondaria, derivata da un'altra fonte, o raccolta compilativa (terziaria).
  La classificazione indicata dall'utente in bibliografia prevale su quella dedotta dal tipo.
* **Provenienza** — da dove viene la scheda (importazione automatica, provenienza dichiarata).
* **Sostegno dell'affermazione** — NEXUS non legge le fonti per controllare che sostengano un'affermazione:
  può solo dire se il collegamento indica una pagina o un passaggio da leggere.

Indipendenza: due fonti NON sono conferme indipendenti se sono la stessa opera (DOI/ISBN/URL/titolo+anno),
se riprendono la stessa fonte primaria dichiarata, se hanno un autore in comune, o se vengono dalla stessa
raccolta compilativa (Wikidata/Wikipedia). È una regola prudente: può unire fonti che in realtà sono
indipendenti, mai il contrario.
"""

from __future__ import annotations

import re
import unicodedata
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

# Enti istituzionali riconosciuti dal nome dell'editore o della rivista (non dal titolo dell'opera).
_OFFICIAL = re.compile(
    r"\b(bank|banca|banco|bundesbank|reserve|central|istat|eurostat|statistic|statist|ministr|commission|commissione|"
    r"office|ufficio|government|governo|parliament|parlamento|imf|oecd|ocse|world bank|united nations|nazioni unite|"
    r"university press|universit|institute|istituto|federal|european union|unione europea)\b",
    re.I,
)
PRIMARY_TYPES = {"archive", "dataset", "document"}
SECONDARY_TYPES = {"book", "article", "chapter"}
VERIFIED = {"verified_user", "verified_registry"}
# Raccolte compilative: ogni voce rimanda alla stessa base, quindi più voci non sono conferme distinte.
AGGREGATORS = {"wikidata": "Wikidata/Wikipedia"}
AGGREGATOR_DOMAINS = {"wikidata.org": "wikidata", "wikipedia.org": "wikidata"}

IDENTITY = {
    "verified_registry": ("confirmed", "confermati dal registro (Crossref): l'opera esiste ed è citata correttamente; il contenuto non è stato controllato"),
    "verified_user": ("declared", "controllati dall'utente sull'originale (dichiarazione dell'utente)"),
    "registry_incomplete": ("incomplete", "DOI trovato nel registro, ma alla scheda mancano dati essenziali"),
    "registry_mismatch": ("doubtful", "DOI trovato ma i metadati del registro non corrispondono alla scheda: identità dell'opera dubbia"),
    "not_found": ("doubtful", "Identificativo non trovato nel registro: identità dell'opera dubbia"),
    "unverified": ("unchecked", "non controllati"),
}
IDENTITY_OK = {"confirmed", "declared"}

CONTENT_NOTE = ("Contenuto: NEXUS non controlla che le fonti sostengano l'affermazione. La verifica dei metadati "
                "riguarda solo l'identità dell'opera; il sostegno va accertato leggendo la fonte.")


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.") if url else ""


def aggregator_of(s: Source) -> str | None:
    """Raccolta compilativa da cui viene la scheda (es. «wikidata»), se riconosciuta."""
    if s.origin in AGGREGATORS:
        return s.origin
    dom = _domain(s.url)
    for d, key in AGGREGATOR_DOMAINS.items():
        if dom == d or dom.endswith("." + d):
            return key
    return None


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


def _norm_author(a: str) -> str:
    a = unicodedata.normalize("NFKD", a).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", a).strip()


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


def independence(db: Session, sources: list[Source]) -> tuple[list[list[Source]], list[str]]:
    """Gruppi di fonti con origine comune, e perché sono state unite (una riga per legame trovato)."""
    parent = list(range(len(sources)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    notes: list[str] = []
    first: dict[str, int] = {}
    labels = {"work": "stessa opera o stessa fonte primaria dichiarata", "author": "autore in comune", "agg": "stessa raccolta compilativa"}
    for i, s in enumerate(sources):
        root = root_of(db, s)
        keys = [("work", work_key(root), "")]
        keys += [("author", f"author:{n}", a) for a in (s.authors or []) if (n := _norm_author(a))]
        if (agg := aggregator_of(s)) is not None:
            keys.append(("agg", f"agg:{agg}", AGGREGATORS[agg]))
        for kind, key, detail in keys:
            if key not in first:
                first[key] = i
                continue
            j = first[key]
            if find(i) != find(j):
                parent[find(i)] = find(j)
                why = labels[kind] + (f" ({detail})" if detail else "")
                notes.append(f"«{_short(sources[j])}» e «{_short(s)}»: {why}")
    groups: dict[int, list[Source]] = {}
    for i, s in enumerate(sources):
        groups.setdefault(find(i), []).append(s)
    return list(groups.values()), notes


def independent_groups(db: Session, sources: list[Source]) -> list[list[Source]]:
    """Raggruppa le fonti per origine comune (vedi `independence`)."""
    return independence(db, sources)[0]


def _short(s: Source) -> str:
    return (s.title or f"fonte #{s.id}")[:60]


def assess_source(s: Source, event_year: int | None = None) -> dict:
    """Valutazione di una singola fonte, dimensione per dimensione, con le ragioni di ogni giudizio."""
    reasons: list[str] = []
    identity, id_reason = IDENTITY.get(s.verification_status, IDENTITY["unverified"])
    reasons.append(f"Metadati: {id_reason}")
    agg = aggregator_of(s)
    # Autorevolezza: tipo di pubblicazione ed ente, letti da editore e rivista (il titolo può contenere qualsiasi parola).
    official = bool(_OFFICIAL.search(" ".join([s.publisher or "", s.container or ""])))
    if agg:
        authority = "low"
        reasons.append(f"Autorevolezza: raccolta compilativa ({AGGREGATORS[agg]}), da usare come punto di partenza verso le fonti citate")
    elif official and s.source_type in PRIMARY_TYPES | SECONDARY_TYPES:
        authority = "high"
        reasons.append("Autorevolezza: editore o ente istituzionale")
    elif s.source_type in SECONDARY_TYPES:
        authority = "medium"
        reasons.append("Autorevolezza: pubblicazione editoriale o accademica (editore non riconosciuto come istituzionale)")
    elif s.source_type in PRIMARY_TYPES:
        authority = "medium"
        reasons.append("Autorevolezza: documento, archivio o dataset di un ente non riconosciuto come istituzionale")
    else:
        authority = "low"
        reasons.append("Autorevolezza: pagina web o tipo di fonte non specificato")
    # Originalità: la classificazione dell'utente prevale sul tipo.
    if s.evidence_class in ("primary", "secondary"):
        originality = s.evidence_class
        reasons.append(f"Originalità: {'primaria' if originality == 'primary' else 'secondaria'} (indicata in bibliografia)")
    else:
        originality = "primary" if s.source_type in PRIMARY_TYPES else "secondary" if s.source_type in SECONDARY_TYPES else "unknown"
        reasons.append("Originalità: " + {"primary": "primaria (dedotta dal tipo di fonte)", "secondary": "secondaria (dedotta dal tipo di fonte)",
                                           "unknown": "non indicata"}[originality])
    if agg:
        originality = "tertiary"
        reasons.append("Originalità: terziaria (compilazione di altre fonti)")
    if s.primary_source_id:
        originality = "derived"
        reasons.append("Originalità: riprende un'altra fonte indicata in bibliografia (non è una conferma indipendente di quella)")
    provenance = []
    if s.origin:
        provenance.append(f"importazione automatica «{s.origin}»")
    if s.provenance:
        provenance.append(s.provenance[:200])
    if provenance:
        reasons.append("Provenienza della scheda: " + "; ".join(provenance))
    timing = None
    if event_year is not None and s.year is not None:
        gap = s.year - event_year
        timing = "before" if gap < 0 else "contemporary" if gap <= 2 else "later"
        if gap < 0:
            reasons.append("Data: pubblicata prima dell'evento, può documentare il contesto ma non l'evento")
    verified = identity in IDENTITY_OK
    # Fonte «qualificata»: identità accertata e autorevolezza almeno media. È un requisito sulla fonte, non sull'affermazione.
    qualified = verified and authority in ("high", "medium")
    return {"source_id": s.id, "authority": authority, "originality": originality, "identity": identity, "timing": timing,
            "verified": verified, "qualified": qualified, "doubtful": identity == "doubtful", "aggregator": agg,
            "year": s.year, "reasons": reasons}


def grade(db: Session, sources: list[Source], *, contradictions: int = 0, event_year: int | None = None,
          base: str | None = None, claim_refs: int | None = None) -> tuple[str, list[str], list[dict]]:
    """Affidabilità complessiva (low/medium/high) di un insieme di fonti, con motivazioni esplicite.

    - alta: almeno due gruppi indipendenti, ognuno con una fonte qualificata (identità accertata, autorevolezza ≥ media);
    - media: un gruppo con una fonte qualificata, oppure almeno due gruppi indipendenti;
    - bassa: altrimenti.
    Le fonti con identità dubbia non contano. Senza pagina o passaggio indicati (`claim_refs == 0`) il livello non
    supera «media». Ogni contraddizione segnalata abbassa di un livello.
    """
    assessed = [assess_source(s, event_year) for s in sources]
    reasons: list[str] = []
    if not sources:
        level = base or "low"
        reasons.append("Fonti: nessuna fonte bibliografica collegata")
    else:
        by_id = {a["source_id"]: a for a in assessed}
        doubtful = [s for s in sources if by_id[s.id]["doubtful"]]
        usable = [s for s in sources if not by_id[s.id]["doubtful"]]
        groups, notes = independence(db, usable)
        qualified_groups = sum(1 for g in groups if any(by_id[s.id]["qualified"] for s in g))
        reasons.append(f"Indipendenza: {len(usable)} fonti utilizzabili in {len(groups)} gruppi indipendenti"
                       + (" (alcune hanno un'origine comune)" if len(groups) < len(usable) else ""))
        reasons.extend(f"Origine comune: {n}" for n in notes[:5])
        if doubtful:
            reasons.append(f"Escluse: {len(doubtful)} fonti con identità dubbia (DOI non trovato o metadati discordanti)")
        reasons.append(f"Qualità: {qualified_groups} gruppi contengono una fonte con identità accertata e autorevolezza almeno media")
        if qualified_groups >= 2:
            level = "high"
        elif qualified_groups >= 1 or len(groups) >= 2:
            level = "medium"
        else:
            level = "low"
        unchecked = sum(1 for a in assessed if not a["verified"] and not a["doubtful"])
        if unchecked:
            reasons.append(f"Metadati: {unchecked} fonti senza identità accertata (né registro né controllo dell'utente)")
    if claim_refs is not None and sources:
        if claim_refs == 0:
            reasons.append("Ancoraggio: nessun collegamento indica la pagina o il passaggio a sostegno dell'affermazione")
            if level == "high":
                level = "medium"
        else:
            reasons.append(f"Ancoraggio: {claim_refs} collegamenti indicano pagina o passaggio (da leggere: indicarli non prova il sostegno)")
    if contradictions:
        reasons.append(f"Contraddizioni: {contradictions} rilevate")
        level = {"high": "medium", "medium": "low", "low": "low"}[level]
    if sources:
        reasons.append(CONTENT_NOTE)
    return level, reasons, assessed
