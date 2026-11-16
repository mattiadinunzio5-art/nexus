"""Fonti bibliografiche: validazione formale, verifica opzionale, formattazione.

Regola: NEXUS non inventa riferimenti. I metadati provengono dall'utente o da
un registro esterno interrogato su richiesta (Crossref per i DOI). Una fonte
resta "non verificata" finché l'utente o il registro non la confermano.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

DOI_RX = re.compile(r"^10\.\d{4,9}/\S+$")


def normalize_doi(doi: str) -> str:
    doi = doi.strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi, flags=re.I)
    return doi


def valid_doi(doi: str) -> bool:
    return bool(DOI_RX.match(normalize_doi(doi)))


def valid_isbn(isbn: str) -> bool:
    digits = re.sub(r"[\s-]", "", isbn).upper()
    if len(digits) == 10 and re.fullmatch(r"\d{9}[\dX]", digits):
        total = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(digits))
        return total % 11 == 0
    if len(digits) == 13 and digits.isdigit():
        total = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(digits))
        return total % 10 == 0
    return False


def valid_url(url: str) -> bool:
    return bool(re.match(r"^https?://[^\s/$.?#].[^\s]*$", url.strip(), re.I))


@dataclass
class RegistryResult:
    # found: il DOI esiste nel registro (NON significa che la scheda corrisponda: vedi compare_metadata)
    status: str  # found | not_found | unavailable
    note: str
    metadata: dict


CROSSREF_API = "https://api.crossref.org/works/"


def _years(msg: dict) -> list[int]:
    out = []
    for key in ("published-print", "published-online", "issued", "published"):
        parts = (msg.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            y = int(parts[0][0])
            if y not in out:
                out.append(y)
    return out


def crossref_lookup(doi: str, timeout: float = 8.0, client: httpx.Client | None = None) -> RegistryResult:
    """Interroga Crossref. «found» dice solo che il DOI esiste: il confronto con la scheda è separato."""
    own = client is None
    client = client or httpx.Client(timeout=timeout, headers={"User-Agent": "NEXUS/0.1 (research platform)"})
    url = CROSSREF_API + normalize_doi(doi)
    try:
        r = client.get(url)
        if r.status_code == 404:
            return RegistryResult("not_found", "Crossref non conosce questo DOI.", {"registry_url": url})
        if r.status_code != 200:
            return RegistryResult("unavailable", f"Crossref ha risposto HTTP {r.status_code}.", {})
        msg = r.json().get("message", {})
        people = msg.get("author", []) or []
        authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "") for a in people]
        families = [a.get("family") or a.get("name", "") for a in people]
        years = _years(msg)
        meta = {
            "doi": msg.get("DOI", normalize_doi(doi)),
            "title": (msg.get("title") or [""])[0],
            "subtitle": (msg.get("subtitle") or [""])[0],
            "authors": [a for a in authors if a],
            "families": [f for f in families if f],
            "year": years[0] if years else None,
            "years": years,
            "container": (msg.get("container-title") or [""])[0],
            "short_container": (msg.get("short-container-title") or [""])[0],
            "publisher": msg.get("publisher", ""),
            "pages": msg.get("page", ""),
            "type": msg.get("type", ""),
            "url": msg.get("URL", "") or f"https://doi.org/{normalize_doi(doi)}",
            "licenses": [x.get("URL", "") for x in (msg.get("license") or []) if x.get("URL")],
            "registry": "Crossref",
            "registry_url": url,
        }
        return RegistryResult("found", "Il DOI esiste in Crossref.", meta)
    except httpx.HTTPError as exc:
        return RegistryResult("unavailable", f"Crossref non raggiungibile: {type(exc).__name__}", {})
    finally:
        if own:
            client.close()


# --- Confronto scheda ↔ registro -------------------------------------------------------------

FIELD_LABELS = {"doi": "DOI", "title": "titolo", "authors": "autori", "year": "anno", "container": "rivista"}


def _norm(t: str) -> str:
    import html
    import unicodedata

    t = unicodedata.normalize("NFKD", html.unescape(re.sub(r"<[^>]+>", "", t or "")))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s]", " ", t.casefold())
    return re.sub(r"\s+", " ", t).strip()


def family_name(author: str) -> str:
    """Cognome da «Nome Cognome» o «Cognome, Nome»."""
    a = (author or "").strip()
    if not a:
        return ""
    if "," in a:
        return _norm(a.split(",", 1)[0])
    parts = _norm(a).split()
    return parts[-1] if parts else ""


def _title_match(local: str, meta: dict) -> str:
    from difflib import SequenceMatcher

    loc = _norm(local)
    cands = [_norm(meta.get("title", ""))]
    if meta.get("subtitle"):
        cands.append(_norm(f"{meta['title']} {meta['subtitle']}"))
    if ":" in (meta.get("title") or ""):
        # Titolo breve (senza sottotitolo) della stessa opera.
        cands.append(_norm(meta["title"].split(":", 1)[0]))
    if loc in cands:
        return "match"
    best = max(SequenceMatcher(None, loc, c).ratio() for c in cands)
    return "match" if best >= 0.93 else "mismatch"


def compare_metadata(src, meta: dict) -> dict:
    """Confronta campo per campo DOI, titolo, autori, anno e rivista.

    Ogni campo: match | mismatch | missing_local (manca nella scheda) | missing_registry (manca nel registro).
    """
    fields: dict[str, dict] = {}

    def put(name: str, status: str, local, registry):
        fields[name] = {"status": status, "local": local, "registry": registry, "label": FIELD_LABELS[name]}

    reg_doi = (meta.get("doi") or "").lower()
    put("doi", "match" if reg_doi == normalize_doi(src.doi or "").lower() else "mismatch", src.doi, meta.get("doi"))

    if not meta.get("title"):
        put("title", "missing_registry", src.title, "")
    else:
        put("title", _title_match(src.title, meta), src.title, meta["title"])

    local_auth = [a for a in (src.authors or []) if _norm(a) not in ("et al", "aa vv", "")]
    reg_fam = [_norm(f) for f in meta.get("families") or []]
    if not reg_fam:
        put("authors", "missing_registry" if local_auth else "match", local_auth, meta.get("authors") or [])
    elif not local_auth:
        put("authors", "missing_local", [], meta.get("authors"))
    else:
        loc_fam = [family_name(a) for a in local_auth]
        reg_set = {w for f in reg_fam for w in f.split()}
        ok = all(any(w in reg_set for w in f.split()) for f in loc_fam) and any(w in reg_fam[0].split() for w in loc_fam[0].split())
        put("authors", "match" if ok else "mismatch", local_auth, meta.get("authors"))

    years = meta.get("years") or ([meta["year"]] if meta.get("year") else [])
    if not years:
        put("year", "missing_registry" if src.year else "match", src.year, None)
    elif not src.year:
        put("year", "missing_local", None, years[0])
    else:
        put("year", "match" if src.year in years else "mismatch", src.year, years[0])

    reg_c = [c for c in (meta.get("container"), meta.get("short_container")) if c]
    if not reg_c:
        if src.container:
            put("container", "missing_registry", src.container, "")
    elif not src.container:
        put("container", "missing_local", "", reg_c[0])
    else:
        lc = _norm(src.container)
        put("container", "match" if any(lc == _norm(c) or lc in _norm(c) or _norm(c) in lc for c in reg_c) else "mismatch",
            src.container, reg_c[0])
    return fields


ESSENTIAL = ("title", "authors", "year")


def registry_verdict(fields: dict) -> tuple[str, str]:
    """Stato della scheda dopo il confronto. Una scheda con un campo discordante non è MAI verificata."""
    mism = [f["label"] for f in fields.values() if f["status"] == "mismatch"]
    missing = [f["label"] for k, f in fields.items() if f["status"] == "missing_local"]
    if mism:
        note = ("DOI trovato ma metadati discordanti: " + ", ".join(mism)
                + ". Correggi la scheda (o il DOI) e ripeti la verifica.")
        return "registry_mismatch", note
    if any(fields.get(k, {}).get("status") == "missing_local" for k in ESSENTIAL):
        return "registry_incomplete", ("DOI trovato e nessuna discordanza, ma alla scheda mancano: " + ", ".join(missing)
                                       + ". Completa i campi per poterla considerare verificata.")
    ok = [f["label"] for f in fields.values() if f["status"] == "match"]
    note = "Riferimento corrispondente: " + ", ".join(ok) + " confermati dal registro."
    if missing:
        note += " Campi non indicati nella scheda: " + ", ".join(missing) + "."
    return "verified_registry", note


def format_citation(src) -> str:
    """Formato autore-data (ispirato a Chicago/APA), costruito solo dai campi presenti."""
    authors = list(src.authors or [])
    if len(authors) > 3:
        a = f"{authors[0]} et al."
    else:
        a = ", ".join(authors)
    parts = []
    parts.append(a or "[Autore non indicato]")
    parts.append(f"({src.year})" if src.year else "(s.d.)")
    title = src.title
    if src.source_type in ("article", "chapter") and src.container:
        parts.append(f"«{title}». {src.container}")
    else:
        parts.append(f"{title}")
    if src.publisher:
        parts.append(src.publisher)
    if src.pages:
        parts.append(f"pp. {src.pages}")
    if src.doi:
        parts.append(f"https://doi.org/{normalize_doi(src.doi)}")
    elif src.url:
        parts.append(src.url + (f" (consultato il {src.accessed_at})" if src.accessed_at else ""))
    text = ". ".join(p.rstrip(".") for p in parts if p) + "."
    return text


VERIFICATION_LABEL = {
    "unverified": "Fonte non verificata",
    "verified_user": "Controllata dall'utente sull'originale",
    "verified_registry": "Metadati confermati dal registro (contenuto non controllato)",
    "registry_mismatch": "DOI trovato ma metadati discordanti",
    "registry_incomplete": "DOI trovato, scheda incompleta",
    "not_found": "Identificativo non trovato nel registro",
}
