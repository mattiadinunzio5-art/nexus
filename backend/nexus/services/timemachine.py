"""Historical Time Machine: cronologia con filtro anti-senno-di-poi.

Regole (modalità rigorosa, ``hindsight=False``):
1. Si mostrano solo eventi iniziati entro l'anno selezionato.
2. Le «conseguenze» descritte in una scheda sono considerate conoscenza
   retrospettiva e vengono nascoste: ciò che era noto all'epoca va registrato
   come informazione datata (``KnowledgeItem``).
3. Delle informazioni datate si mostrano solo quelle note entro l'anno.
4. Gli eventi ancora in corso sono marcati come tali.
5. Degli indicatori economici si mostra l'ultimo valore con data <= anno
   selezionato, avvertendo che i dati possono essere stati rivisti dopo.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_history import KnowledgeOut, TimelineEvent, TimelineIndicator, TimelineOut
from ..history import dates
from ..models import User
from . import history


def timeline(
    db: Session, user: User, *, as_of_year: int | None, hindsight: bool, country: str | None, category: str | None,
    from_year: int | None, to_year: int | None, event_id: int | None = None, origin: str | None = None,
    project_id: int | None = None,
) -> TimelineOut:
    from ..core import library

    upper = to_year
    if as_of_year is not None and not hindsight:
        upper = min(as_of_year, to_year) if to_year is not None else as_of_year
    windowed = False
    if as_of_year is not None and from_year is None and origin != "mine" and project_id is None and library.library_user_id(db) is not None:
        # Con la Biblioteca l'archivio è molto grande: senza «dall'anno» si mostra una finestra
        # di WINDOW_YEARS anni prima della data scelta (modificabile con i filtri).
        from_year, windowed = as_of_year - WINDOW_YEARS, True
    all_events = history.list_events(db, user, category=category, country=country, from_year=from_year, to_year=to_year,
                                     limit=MAX_EVENTS, origin=origin, project_id=project_id)
    events = [e for e in all_events if upper is None or e.start_year <= upper]
    if event_id is not None:
        events = [e for e in events if e.id == event_id]
    hidden_future = len(all_events) - len([e for e in all_events if upper is None or e.start_year <= upper])

    from ..models import Source
    from ..research.citations import format_citation

    src_ids = {link.source_id for e in events for link in e.source_links} | {k.source_id for e in events for k in e.knowledge if k.source_id}
    srcs = {s.id: s for s in db.scalars(select(Source).where(Source.id.in_(src_ids)))} if src_ids else {}

    def k_out(k, then: bool) -> KnowledgeOut:
        o = KnowledgeOut.model_validate(k)
        o.availability = "not_applicable" if as_of_year is None else ("then" if then else "later")
        if k.source_id and k.source_id in srcs:
            o.source_citation = format_citation(srcs[k.source_id])
        return o

    out = []
    for e in events:
        k_then, k_later = [], []
        for k in e.knowledge:
            then = as_of_year is None or k.known_since_year <= as_of_year
            (k_then if then else k_later).append(k_out(k, then))
        ev_sources = []
        for link in e.source_links:
            src = srcs.get(link.source_id)
            if src is None:
                continue
            after = as_of_year is not None and src.year is not None and src.year > as_of_year
            ev_sources.append({"source_id": src.id, "citation": format_citation(src), "year": src.year, "pages": link.pages,
                               "evidence_class": src.evidence_class or "", "published_after": after})
        if as_of_year is None:
            status = "not_applicable"
        else:
            end = e.end_year if e.end_year is not None else e.start_year
            status = "ongoing" if end > as_of_year else "concluded"
        strict = as_of_year is not None and not hindsight
        out.append(
            TimelineEvent(
                id=e.id, title=e.title,
                date_label=dates.fmt_range(e.start_year, e.start_month, e.start_day, e.end_year, e.end_month, e.end_day),
                start_year=e.start_year, end_year=e.end_year, status_at_date=status, countries=e.countries,
                categories=e.categories, reliability=e.reliability, description=e.description,
                consequences=None if strict else e.consequences, consequences_hidden=strict and bool(e.consequences),
                known_then=k_then, known_later=[] if strict else k_later, hidden_later_count=len(k_later) if strict else 0,
                is_demo=e.is_demo, library=library.is_library(db, e.owner_id),
                date_precision="day" if e.start_day else "month" if e.start_month else "year",
                sources=[x for x in ev_sources if not (strict and x["published_after"])] if strict else ev_sources,
            )
        )

    indicators = _indicators_as_of(db, user, as_of_year, country) if as_of_year is not None else []
    notes = []
    if windowed:
        notes.append(f"Archivio esteso (Biblioteca NEXUS): sono mostrati gli eventi dal {dates.fmt(from_year)}; usa «Dall'anno» per allargare.")
    if as_of_year is not None and not hindsight:
        notes.append(f"Vista rigorosa al {dates.fmt(as_of_year)}: nascosti eventi successivi, conseguenze retrospettive e informazioni emerse dopo.")
    if as_of_year is not None and hindsight:
        notes.append("Senno di poi attivo: sono incluse informazioni non disponibili all'epoca, evidenziate come tali.")
    if indicators:
        notes.append("Gli indicatori mostrano i valori attuali delle serie fino alla data scelta: possono differire dai dati pubblicati all'epoca (revisioni).")
        if any(i.retrospective for i in indicators):
            notes.append("Alcuni indicatori sono ricostruzioni pubblicate dopo la data scelta: segnalati come «ricostruzione a posteriori», non erano noti ai contemporanei.")
    return TimelineOut(
        as_of_year=as_of_year, hindsight=hindsight,
        filters={"country": country, "category": category, "from_year": from_year, "to_year": to_year},
        events=out, indicators=indicators, hidden_future_events=hidden_future if not hindsight else 0, notes=notes,
        completeness=completeness(out, indicators, as_of_year, country) if as_of_year is not None else None,
    )


def completeness(events: list, indicators: list, as_of_year: int, country: str | None) -> dict:
    """Quanto è completa la ricostruzione alla data scelta, con le lacune da colmare.

    Quattro componenti (0–1), media semplice: eventi con almeno una fonte disponibile all'epoca,
    eventi con almeno un'informazione datata nota all'epoca, eventi con data precisa (mese),
    indicatori economici disponibili all'epoca (non ricostruiti dopo).
    """
    n = len(events)
    gaps: list[str] = []
    comps = []

    def comp(key: str, label: str, ok: int, total: int, gap: str | None):
        comps.append({"key": key, "label": label, "ok": ok, "total": total, "ratio": round(ok / total, 2) if total else None})
        if gap and total and ok < total:
            gaps.append(gap)

    with_src = [e for e in events if any(not s["published_after"] for s in e.sources)]
    comp("sources", "Eventi con una fonte disponibile all'epoca", len(with_src), n,
         f"{n - len(with_src)} eventi senza fonti pubblicate entro il {as_of_year}: " + "; ".join(e.title for e in events if e not in with_src)[:300])
    with_k = [e for e in events if e.known_then]
    comp("knowledge", "Eventi con informazioni datate note all'epoca", len(with_k), n,
         f"{n - len(with_k)} eventi senza informazioni datate: non si sa che cosa ne sapessero i contemporanei.")
    precise = [e for e in events if e.date_precision != "year"]
    comp("dates", "Eventi datati almeno al mese", len(precise), n, f"{n - len(precise)} eventi datati solo all'anno: l'ordine nello stesso anno è incerto.")
    avail = [i for i in indicators if i.availability == "available"]
    comp("indicators", "Indicatori economici disponibili all'epoca", len(avail), len(indicators),
         f"{len(indicators) - len(avail)} indicatori sono ricostruzioni successive o senza data di pubblicazione.")
    if not events:
        gaps.append(f"Nessun evento registrato entro il {as_of_year}" + (f" per «{country}»." if country else "."))
    if not indicators:
        gaps.append("Nessun indicatore economico con dati entro la data scelta" + (f" per «{country}»." if country else "."))
    ratios = [c["ratio"] for c in comps if c["ratio"] is not None]
    score = round(sum(ratios) / 4, 2) if ratios else 0.0  # le componenti senza dati contano zero
    level = "high" if score >= 0.75 else "medium" if score >= 0.4 else "low"
    return {"score": score, "level": level, "components": comps, "gaps": gaps,
            "method": "Media di quattro componenti (fonti dell'epoca, informazioni datate, precisione delle date, indicatori disponibili all'epoca); "
                      "una componente senza elementi conta zero."}


def _year(text: str | None) -> int | None:
    import re

    m = re.search(r"(1[89]\d\d|20\d\d)", text or "")
    return int(m.group(1)) if m else None


WINDOW_YEARS = 25
MAX_EVENTS = 400
MAX_LIBRARY_INDICATORS = 12


def _indicators_as_of(db: Session, user: User, year: int, country: str | None = None) -> list[TimelineIndicator]:
    try:
        from ..models import Observation, Series
    except ImportError:  # Fase 4 non ancora installata
        return []
    from ..core import library

    result = []
    candidates = list(db.scalars(select(Series).where(Series.owner_id == user.id)))
    lib = library.library_user_id(db)
    if lib is not None and lib != user.id and country:
        # Dalla Biblioteca solo le serie del paese filtrato, con un limite (sono migliaia).
        candidates += list(db.scalars(select(Series).where(Series.owner_id == lib, Series.country.ilike(f"%{country}%"))
                                      .order_by(Series.name).limit(MAX_LIBRARY_INDICATORS)))
    for s in candidates:
        obs = db.scalar(
            select(Observation)
            .where(Observation.series_id == s.id, Observation.date <= f"{year}-12-31", Observation.value.is_not(None))
            .order_by(Observation.date.desc())
            .limit(1)
        )
        if obs is not None:
            # Data in cui la fonte ha pubblicato questa versione: se è successiva all'anno scelto, il valore è una
            # ricostruzione a posteriori e all'epoca non era noto in questa forma.
            published = _year(s.source_last_updated) or (s.retrieved_at.year if s.retrieved_at else None)
            retro = published is not None and published > year
            availability = "unknown" if published is None else ("retrospective" if retro else "available")
            caveat = (f"Ricostruzione a posteriori: la fonte ha pubblicato questa serie nel {published}. All'epoca il dato non era disponibile in questa forma."
                      if retro else "Valore della versione attuale della serie (possibili revisioni successive).")
            result.append(
                TimelineIndicator(
                    series_id=s.id, name=s.name, unit=s.unit, source=s.source_label, last_date=obs.date, last_value=obs.value,
                    caveat=caveat, retrospective=retro, published=published,
                    retrieved_at=s.retrieved_at.isoformat() if s.retrieved_at else None, availability=availability,
                )
            )
    return result
