"""Tracciabilità delle affermazioni di un rapporto.

Regole deterministiche (nessun modello AI):

* il testo di ogni sezione è diviso in paragrafi e frasi;
* un'affermazione è «rilevante» se contiene numeri, date, percentuali, nessi causali
  o giudizi forti (le frasi brevi, le domande e i titoli di elenco non lo sono);
* è «supportata» se la frase contiene una citazione [@id] valida; «supportata dal paragrafo»
  se la citazione è nell'ultima frase dello stesso paragrafo; altrimenti è «senza supporto»;
* per ogni citazione si registra la pagina (collocazione) quando c'è, e se la fonte è
  primaria o secondaria.

Il controllo segnala, non giudica il contenuto: una citazione presente non prova che la
fonte dica davvero ciò che il testo afferma.
"""

from __future__ import annotations

import re

from .citations import CITE_RX

SENT_RX = re.compile(r"(?<=[.!?…»])\s+(?=[«\"A-ZÀ-Ý0-9\[(])")
_NUM = re.compile(r"\d")
_CAUSAL = re.compile(
    r"\b(caus\w*|provoc\w*|determin\w*|portò|portarono|port[oa] a|grazie a|a causa|in seguito a|di conseguenza|perciò|quindi|"
    r"effett\w*|impatt\w*|dimostr\w*|prova\w*|sempre|mai|tutti|nessun\w*|il primo|la prima|il più|la più|"
    r"caused|led to|because|due to|therefore|proves?|always|never|first|largest|most)\b", re.I)
_PAGE = re.compile(r"\b(p{1,2}\.|pag\.|pagg?\.|pp?\s|f\.|ff\.|c\.|cc\.|fol\.|§|col\.|n\.)\s*\w", re.I)
MIN_WORDS = 6

# Sezioni che descrivono il lavoro stesso: le loro frasi non richiedono una fonte.
NO_SOURCE_SECTIONS = {"abstract", "methodology", "limitations"}


def strip_cites(t: str) -> str:
    return re.sub(r"\s+([.,;:!?])", r"\1", re.sub(r"\s+", " ", CITE_RX.sub("", t))).strip()


def sentences(paragraph: str) -> list[str]:
    p = " ".join(paragraph.split())
    if not p:
        return []
    # Le citazioni ([@3, p. 12]) contengono punti: si proteggono prima di dividere le frasi.
    saved: list[str] = []

    def keep(m: re.Match) -> str:
        saved.append(m.group(0))
        return f"\x01{len(saved) - 1}\x01"

    parts = [x.strip() for x in SENT_RX.split(CITE_RX.sub(keep, p)) if x.strip()]
    out: list[str] = []
    for x in parts:
        x = re.sub("\x01(\\d+)\x01", lambda m: saved[int(m.group(1))], x)
        # una citazione dopo il punto («… fine. [@3]») appartiene alla frase precedente
        if out and not strip_cites(x):
            out[-1] += " " + x
        else:
            out.append(x)
    return out


def is_relevant(sentence: str) -> bool:
    text = strip_cites(sentence).lstrip("- ")
    if len(text.split()) < MIN_WORDS or text.endswith("?"):
        return False
    return bool(_NUM.search(text) or _CAUSAL.search(text))


def analyze_section(key: str, body: str, sources: dict, evidence_class: dict) -> list[dict]:
    """Affermazioni rilevanti della sezione con il loro supporto."""
    out = []
    for p_idx, para in enumerate(re.split(r"\n\s*\n", body or "")):
        sents = sentences(para)
        para_cites = [m for m in CITE_RX.finditer(sents[-1])] if sents else []
        for s in sents:
            if not is_relevant(s):
                continue
            cites = list(CITE_RX.finditer(s))
            level = "sentence"
            if not cites and para_cites and s != sents[-1]:
                cites, level = para_cites, "paragraph"
            refs = []
            for m in cites:
                sid = int(m.group(1))
                loc = (m.group(2) or "").strip()
                refs.append({"source_id": sid, "locator": loc, "has_page": bool(loc and (_PAGE.search(loc) or re.fullmatch(r"[\d\-–, ]+", loc))),
                             "valid": sid in sources, "evidence_class": evidence_class.get(sid, "")})
            valid = [r for r in refs if r["valid"]]
            if not refs:
                status = "exempt" if key in NO_SOURCE_SECTIONS else "unsupported"
            elif not valid:
                status = "invalid_citation"
            else:
                status = "supported" if level == "sentence" else "paragraph"
            out.append({"paragraph": p_idx, "text": strip_cites(s)[:400], "status": status, "citations": refs})
    return out


_YEAR = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")
_NUMBER = re.compile(r"(?<![\w.])-?\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?(?![\w])|(?<![\w.,])-?\d+(?:[.,]\d+)?(?![\w])")


def parse_number(tok: str) -> float | None:
    t = tok.replace(" ", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):  # 1.234.567,8 (it)
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):  # 1,234,567.8 (en)
        t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _close(x: float, v: float) -> bool:
    if v == 0:
        return abs(x) < 1e-9
    if abs(x - v) / abs(v) <= 0.01:
        return True
    # stesso valore arrotondato come nel testo (es. 1.234 per 1.2345)
    return any(round(v, d) == x for d in range(0, 4))


def numeric_mismatches(body: str, series_values: dict[str, dict[str, float]]) -> list[dict]:
    """Frasi che citano una serie del grafico, un anno e un valore che non coincide con i dati del grafico.

    series_values: nome della serie -> {anno: valore}. Si controllano solo le frasi che nominano la serie
    (almeno una parola significativa del nome) e un anno presente nei dati, per evitare falsi allarmi.
    """
    issues = []
    for name, by_year in series_values.items():
        words = {w for w in re.findall(r"\w{5,}", name.lower())}
        for s in sentences(" ".join((body or "").split("\n"))):
            text = strip_cites(s)
            low = text.lower()
            if not words or not any(w in low for w in words):
                continue
            years = [y for y in _YEAR.findall(text) if y in by_year]
            if len(years) != 1:
                continue
            nums = [parse_number(t) for t in _NUMBER.findall(_YEAR.sub(" ", text))]
            nums = [n for n in nums if n is not None]
            if not nums:
                continue
            v = by_year[years[0]]
            if not any(_close(n, v) for n in nums):
                issues.append({"series": name, "year": years[0], "text_values": nums[:5], "data_value": v, "sentence": text[:300]})
    return issues
