"""Citazioni nel testo dei rapporti.

Sintassi: ``[@12]`` oppure ``[@12, p. 45]`` / ``[@12, pp. 45-47]``, dove 12 è
l'id di una fonte della bibliografia. In esportazione diventano riferimenti
numerati ``[1, p. 45]`` nell'ordine di prima citazione. Una citazione a una
fonte inesistente non viene mai «risolta»: resta segnalata.
"""

from __future__ import annotations

import re

CITE_RX = re.compile(r"\[@(\d+)(?:,\s*([^\]\n]{1,40}))?\]")


def cited_ids(texts: list[str]) -> list[int]:
    seen: list[int] = []
    for t in texts:
        for m in CITE_RX.finditer(t or ""):
            sid = int(m.group(1))
            if sid not in seen:
                seen.append(sid)
    return seen


def render(text: str, numbering: dict[int, int]) -> str:
    def sub(m: re.Match) -> str:
        sid = int(m.group(1))
        loc = m.group(2)
        if sid not in numbering:
            return "[citazione non valida]"
        return f"[{numbering[sid]}{', ' + loc.strip() if loc else ''}]"

    return CITE_RX.sub(sub, text or "")


# --- Stili di citazione ------------------------------------------------------------------------
# Il segnaposto delle note a piè di pagina nel testo esportato: FN_MARK.format(n) (vedi export.split_notes).
FN_MARK = "\x00{}\x00"
FN_RX = re.compile("\x00(\\d+)\x00")


def _surname(src) -> str:
    authors = list(getattr(src, "authors", None) or [])
    if not authors:
        return ""
    first = authors[0].split(",")[0].strip()
    return first + (" et al." if len(authors) > 3 else (" e " + authors[1].split(",")[0].strip() if len(authors) == 2 else ""))


def short_title(src, words: int = 5) -> str:
    w = (src.title or "").split()
    if len(w) <= words:
        return " ".join(w)
    return " ".join(w[:words]).rstrip(",;:.") + "…"


def author_date(src, loc: str | None) -> str:
    who = _surname(src) or short_title(src, 3)
    return f"({who} {src.year or 's.d.'}{', ' + loc.strip() if loc else ''})"


class Notes:
    """Note a piè di pagina numerate per tutto il documento: citazione completa alla prima occorrenza,
    forma breve in seguito, «Ivi» se la fonte è la stessa della nota precedente."""

    def __init__(self, full) -> None:
        self.full = full  # funzione Source -> citazione completa
        self.items: list[str] = []
        self.seen: set[int] = set()
        self.last: int | None = None

    def add(self, src, loc: str | None) -> int:
        loc = (loc or "").strip()
        if self.last == src.id:
            text = f"Ivi{', ' + loc if loc else ''}."
        elif src.id in self.seen:
            who = _surname(src)
            text = f"{who + ', ' if who else ''}{short_title(src)}{', ' + loc if loc else ''}."
        else:
            text = self.full(src).rstrip(".") + (f", {loc}" if loc else "") + "."
        self.seen.add(src.id)
        self.last = src.id
        self.items.append(text.replace("….", "…"))
        return len(self.items)

    def new_chapter(self) -> None:
        """«Ivi» non attraversa i capitoli: dopo l'inizio di un capitolo la prima nota torna alla forma breve."""
        self.last = None

    def note(self, text: str) -> int:
        """Nota libera (es. fonte di una tabella), non legata a una scheda."""
        self.last = None
        self.items.append(text)
        return len(self.items)


def render_styled(text: str, style: str, numbering: dict[int, int], sources: dict, notes: Notes | None) -> str:
    """Rende le citazioni [@id, loc] nello stile scelto. Le fonti inesistenti restano segnalate."""
    if style == "numeric" or notes is None and style == "footnotes":
        return render(text, numbering)

    def sub(m: re.Match) -> str:
        sid = int(m.group(1))
        loc = m.group(2)
        src = sources.get(sid)
        if src is None:
            return "[citazione non valida]"
        if style == "author_date":
            return author_date(src, loc)
        return FN_MARK.format(notes.add(src, loc))

    out = CITE_RX.sub(sub, text or "")
    # la nota si attacca alla parola precedente: «testo [@1]» -> «testo¹»
    return re.sub(r"\s+(\x00\d+\x00)", r"\1", out)
