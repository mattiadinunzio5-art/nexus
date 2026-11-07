"""BibTeX: esportazione delle fonti e importazione (es. da Zotero, Mendeley, JabRef).

Le fonti importate entrano come «non verificate»: un file .bib dice cosa
dichiara chi lo ha scritto, non che la fonte esista.
"""

from __future__ import annotations

import re
import unicodedata

TYPE_TO_BIB = {"book": "book", "article": "article", "chapter": "incollection", "web": "online", "dataset": "misc",
               "archive": "misc", "document": "misc", "other": "misc"}
BIB_TO_TYPE = {"book": "book", "article": "article", "incollection": "chapter", "inbook": "chapter", "inproceedings": "chapter",
               "online": "web", "electronic": "web", "www": "web", "dataset": "dataset", "techreport": "document",
               "report": "document", "phdthesis": "document", "mastersthesis": "document", "thesis": "document"}
_LATEX_SPECIAL = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                  "_": r"\_", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def latex_escape(s: str) -> str:
    return "".join(_LATEX_SPECIAL.get(ch, ch) for ch in s or "")


def cite_key(authors: list[str], year: int | None, title: str, taken: set[str]) -> str:
    first = (authors[0].split(",")[0] if authors else title.split(" ")[0] if title else "fonte").strip()
    base = unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]", "", base) or "fonte"
    base += str(year or "")
    key, n = base, 0
    while key in taken:
        n += 1
        key = base + "abcdefghijklmnopqrstuvwxyz"[(n - 1) % 26] * ((n - 1) // 26 + 1)
    taken.add(key)
    return key


def source_to_bibtex(s, key: str) -> str:
    fields: list[tuple[str, str]] = [("title", s.title)]
    if s.authors:
        fields.append(("author", " and ".join(s.authors)))
    if s.year is not None:
        fields.append(("year", str(s.year)))
    if s.container:
        fields.append(("journal" if s.source_type == "article" else "booktitle", s.container))
    for name, val in (("publisher", s.publisher), ("pages", s.pages), ("doi", s.doi), ("isbn", s.isbn), ("url", s.url),
                      ("urldate", s.accessed_at)):
        if val:
            fields.append((name, val))
    status = getattr(s, "verification_status", "unverified")
    fields.append(("note", f"NEXUS: verification status {status}"))
    body = ",\n".join(f"  {k} = {{{latex_escape(v) if k not in ('url', 'doi') else v}}}" for k, v in fields)
    return f"@{TYPE_TO_BIB.get(s.source_type, 'misc')}{{{key},\n{body}\n}}\n"


# --- Parser -------------------------------------------------------------------------------------

_UNLATEX = [(r"\&", "&"), (r"\%", "%"), (r"\$", "$"), (r"\#", "#"), (r"\_", "_"), ("--", "–"), (r"\textbackslash{}", "\\")]


def _clean(v: str) -> str:
    for a, b in _UNLATEX:
        v = v.replace(a, b)
    v = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", v)  # \emph{x} -> x
    v = v.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", v).strip()


def _read_value(text: str, i: int) -> tuple[str, int]:
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text):
        return "", i
    if text[i] == "{":
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    return text[i + 1:j], j + 1
            j += 1
        raise ValueError("Parentesi graffe non chiuse.")
    if text[i] == '"':
        j = i + 1
        depth = 0
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            elif text[j] == '"' and depth == 0:
                return text[i + 1:j], j + 1
            j += 1
        raise ValueError("Virgolette non chiuse.")
    m = re.match(r"[A-Za-z0-9_.:-]+", text[i:])
    return (m.group(0), i + m.end()) if m else ("", i)


def parse_bibtex(text: str) -> list[dict]:
    """Restituisce le voci come dizionari: {'type', 'key', campi in minuscolo}."""
    entries = []
    for m in re.finditer(r"@\s*([A-Za-z]+)\s*[{(]\s*([^,\s]*)\s*,", text):
        etype = m.group(1).lower()
        if etype in ("comment", "preamble", "string"):
            continue
        i, fields = m.end(), {}
        while i < len(text):
            fm = re.compile(r"\s*([A-Za-z][A-Za-z0-9_-]*)\s*=").match(text, i)
            if not fm:
                break
            val, i = _read_value(text, fm.end())
            fields[fm.group(1).lower()] = _clean(val)
            sep = re.compile(r"\s*,?").match(text, i)
            i = sep.end()
            if i < len(text) and text[i] in "})":
                break
        entries.append({"type": etype, "key": m.group(2), **fields})
    return entries


def entry_to_source(e: dict) -> dict:
    """Voce BibTeX -> campi di SourceIn (solo ciò che il file dichiara)."""
    year = None
    if re.fullmatch(r"-?\d{1,4}", e.get("year", "")):
        year = int(e["year"])
    elif re.match(r"\d{4}", e.get("date", "")):
        year = int(e["date"][:4])
    authors = [a.strip() for a in re.split(r"\s+and\s+", e.get("author", "") or e.get("editor", "")) if a.strip()]
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", e.get("doi", ""), flags=re.I)
    urldate = e.get("urldate", "")
    return {
        "source_type": BIB_TO_TYPE.get(e["type"], "other"),
        "title": e.get("title", "")[:500],
        "authors": [a[:200] for a in authors[:50]],
        "year": year,
        "publisher": (e.get("publisher") or e.get("institution") or e.get("school") or "")[:300],
        "container": (e.get("journal") or e.get("journaltitle") or e.get("booktitle") or "")[:300],
        "pages": e.get("pages", "")[:50],
        "doi": doi[:200],
        "isbn": e.get("isbn", "")[:20],
        "url": e.get("url", "")[:1000],
        "accessed_at": urldate if re.fullmatch(r"\d{4}-\d{2}-\d{2}", urldate) else "",
        "notes": f"Importata da BibTeX (chiave {e.get('key', '')})."[:5000],
    }
