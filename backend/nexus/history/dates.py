"""Date storiche: anni interi con segno (negativo = a.C.), mese/giorno facoltativi.

Convenzione storica: l'anno 0 non esiste (1 a.C. è seguito da 1 d.C.).
"""

from __future__ import annotations

import calendar

from ..core.locale import current_lang

MONTHS_IT = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def validate(year: int | None, month: int | None, day: int | None, label: str) -> None:
    if year is None:
        if month is not None or day is not None:
            raise ValueError(f"{label}: mese/giorno senza anno")
        return
    if year == 0:
        raise ValueError(f"{label}: l'anno 0 non esiste (usa -1 per l'1 a.C.)")
    if not -10000 <= year <= 2200:
        raise ValueError(f"{label}: anno fuori intervallo")
    if day is not None and month is None:
        raise ValueError(f"{label}: giorno senza mese")
    if month is not None and not 1 <= month <= 12:
        raise ValueError(f"{label}: mese non valido")
    if day is not None:
        max_day = calendar.monthrange(year, month)[1] if year > 0 else 31  # type: ignore[arg-type]
        if not 1 <= day <= max_day:
            raise ValueError(f"{label}: giorno non valido per il mese")


def sort_key(year: int, month: int | None, day: int | None) -> tuple[int, int, int]:
    return (year, month or 0, day or 0)


def fmt(year: int | None, month: int | None = None, day: int | None = None) -> str:
    if year is None:
        return ""
    en = current_lang.get() == "en"
    months = MONTHS_EN if en else MONTHS_IT
    y = (f"{-year} BC" if en else f"{-year} a.C.") if year < 0 else str(year)
    if month is None:
        return y
    if day is None:
        return f"{months[month - 1]} {y}"
    return f"{day} {months[month - 1]} {y}"


def fmt_range(sy, sm, sd, ey, em, ed) -> str:
    start = fmt(sy, sm, sd)
    if ey is None or (ey, em, ed) == (sy, sm, sd):
        return start
    return f"{start} – {fmt(ey, em, ed)}"
