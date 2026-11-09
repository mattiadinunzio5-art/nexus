"""Bibliografia della Biblioteca: opere di storia economica, monetaria e finanziaria da Crossref (articoli e libri con DOI)
e Open Library (libri con ISBN). Nessun riferimento scritto a memoria: ogni scheda arriva dalle API.
Le fonti con DOI passano dalla verifica esistente su Crossref (verify_source); le altre restano «non verificate».
"""

from __future__ import annotations

import re
from datetime import date

import httpx
from sqlalchemy import select

from ..api.schemas_research import SourceIn
from ..models import Source
from ..services import sources
from .common import Run
from .wikidata import UA

TOPICS = ["economic history", "monetary history", "history of banking", "financial crisis history", "great depression",
          "gold standard", "industrial revolution", "history of capitalism", "history of inflation", "public debt history",
          "history of central banking", "economic growth history", "history of globalization", "history of financial markets"]
KEYWORDS = re.compile(r"histor|monet|bank|crisis|crises|depression|inflation|capitalis|debt|money|financ|gold|industrial|econom", re.I)
OPEN_LIBRARY_SUBJECTS = ["economic history", "monetary policy history", "banks and banking history", "financial crises",
                         "depressions", "gold standard", "industrial revolution", "capitalism history"]


def _client() -> httpx.Client:
    return httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": UA})


def _exists(run: Run, ext: str) -> bool:
    return run.db.scalar(select(Source.id).where(Source.owner_id == run.lib.id, Source.origin.in_(("crossref", "openlibrary")),
                                                 Source.external_id == ext)) is not None


def crossref(run: Run, c: httpx.Client, per_topic: int) -> None:
    for topic in TOPICS:
        if not run.budget_left():
            return
        r = c.get("https://api.crossref.org/works", params={
            "query.bibliographic": topic, "filter": "type:book,type:journal-article,type:monograph", "rows": per_topic * 2,
            "select": "DOI,title,author,issued,publisher,container-title,page,type"})
        run.sleep()
        if r.status_code != 200:
            run.error("sources", f"crossref:{topic}", f"HTTP {r.status_code}")
            continue
        taken = 0
        for it in r.json()["message"]["items"]:
            if taken >= per_topic or not run.budget_left():
                break
            title = (it.get("title") or [""])[0].strip()
            doi = (it.get("DOI") or "").lower()
            if not title or not doi or not KEYWORDS.search(title) or _exists(run, doi):
                run.report.add("sources", "skipped")
                continue
            authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in it.get("author", [])][:20]
            year = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
            stype = "book" if it.get("type") in ("book", "monograph") else "article"
            try:
                s = sources.create_source(run.db, run.lib, SourceIn(
                    source_type=stype, title=title[:500], authors=[a[:200] for a in authors if a], year=year,
                    publisher=(it.get("publisher") or "")[:300], container=((it.get("container-title") or [""])[0])[:300],
                    pages=(it.get("page") or "")[:50], doi=doi, url=f"https://doi.org/{doi}", accessed_at=date.today().isoformat(),
                    notes=f"Metadati da Crossref (ricerca: «{topic}»)."))
                s.origin, s.external_id = "crossref", doi
                run.db.commit()
                run.tick()
                taken += 1
                run.report.add("sources", "created")
                try:
                    sources.verify_source(run.db, run.lib, s.id, "registry", "")
                    run.report.add("sources_verified", "created")
                except Exception as exc:  # noqa: BLE001 — la verifica non riuscita lascia la fonte «non verificata»
                    run.report.add("sources_verified", "skipped")
                    run.db.rollback()
                    _ = exc
                run.sleep()
            except Exception as exc:  # noqa: BLE001
                run.error("sources", doi, repr(exc))


def _isbn(candidates: list[str]) -> str:
    from ..research.citations import valid_isbn

    for x in sorted(candidates or [], key=len, reverse=True):
        if valid_isbn(x):
            return x
    return ""


def open_library(run: Run, c: httpx.Client, per_subject: int) -> None:
    for subj in OPEN_LIBRARY_SUBJECTS:
        if not run.budget_left():
            return
        r = c.get("https://openlibrary.org/search.json", params={
            "q": f'subject:"{subj}"', "fields": "key,title,author_name,first_publish_year,isbn,publisher", "limit": per_subject * 2,
            "sort": "editions"})
        run.sleep()
        if r.status_code != 200:
            run.error("sources", f"openlibrary:{subj}", f"HTTP {r.status_code}")
            continue
        taken = 0
        for d in r.json().get("docs", []):
            if taken >= per_subject or not run.budget_left():
                break
            key = d.get("key", "")
            if not key or not d.get("title") or _exists(run, key):
                run.report.add("sources", "skipped")
                continue
            try:
                s = sources.create_source(run.db, run.lib, SourceIn(
                    source_type="book", title=d["title"][:500], authors=[a[:200] for a in d.get("author_name", [])][:20],
                    year=d.get("first_publish_year"), publisher=((d.get("publisher") or [""])[0])[:300], isbn=_isbn(d.get("isbn", [])),
                    url=f"https://openlibrary.org{key}", accessed_at=date.today().isoformat(),
                    notes=f"Metadati da Open Library (soggetto: «{subj}»); anno = prima pubblicazione indicata dal catalogo."))
                s.origin, s.external_id = "openlibrary", key
                run.db.commit()
                run.tick()
                taken += 1
                run.report.add("sources", "created")
            except Exception as exc:  # noqa: BLE001
                run.error("sources", key, repr(exc))


def run_biblio(run: Run) -> None:
    total = run.limit or 400
    with _client() as c:
        crossref(run, c, per_topic=max(3, int(total * 0.6) // len(TOPICS)))
        run._processed = 0
        open_library(run, c, per_subject=max(3, int(total * 0.4) // len(OPEN_LIBRARY_SUBJECTS)))
