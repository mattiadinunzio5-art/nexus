"""Ricerca globale.

In Fase 1 cerca (testo, case-insensitive) nei progetti dell'utente e nel
catalogo dei moduli. La risposta dichiara quali ambiti non sono ancora
ricercabili, invece di restituire risultati fittizi.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas import SearchHit, SearchResultOut
from ..core.modules import MODULES
from ..models import Document, Entity, HistoricalEvent, Project, Report, SearchQuery, Series, User
from ..research import index

UNAVAILABLE_SCOPES = [
]


def _snippet(text: str, query: str, width: int = 140) -> str:
    if not text:
        return ""
    idx = text.lower().find(query.lower())
    if idx < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, idx - width // 3)
    end = min(len(text), start + width)
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def _escape_like(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")


def _word_match(query: str):
    """Corrispondenza a inizio parola, in italiano e in inglese: «oil» trova «oil crisis», «oils» e «petrolio», non «turmoil»."""
    from ..research.crosslang import text_matcher

    return text_matcher(query)


def search(db: Session, user: User, query: str, limit: int = 25) -> SearchResultOut:
    from ..research.crosslang import match_any

    ok = _word_match(query)
    wide = limit * 8  # si leggono più candidati e si tengono quelli che corrispondono a inizio parola
    projects = db.scalars(
        select(Project)
        .where(
            Project.owner_id == user.id,
            match_any([Project.title, Project.description, Project.research_question], query),
        )
        .order_by(Project.updated_at.desc())
        .limit(wide)
    )
    projects = [p for p in projects if ok(p.title, p.description, p.research_question)][:limit]
    hits = [
        SearchHit(
            type="project",
            id=str(p.id),
            title=p.title + (" [DEMO]" if p.is_demo else ""),
            snippet=_snippet(p.description, query),
            url=f"/projects?id={p.id}",
        )
        for p in projects
    ]
    doc_ids_seen: set[int] = set()
    for d in db.scalars(
        select(Document).where(Document.owner_id == user.id, match_any([Document.title, Document.author], query)).limit(wide)
    ):
        if not ok(d.title, d.author):
            continue
        doc_ids_seen.add(d.id)
        hits.append(SearchHit(type="document", id=str(d.id), title=d.title, snippet=f"{d.kind.upper()} · {d.chunk_count} segmenti", url=f"/documents/{d.id}"))
    for cid, _ in index.text_search(db, user.id, query, 10):
        from ..models import DocumentChunk

        c = db.get(DocumentChunk, cid)
        if c is None or c.document_id in doc_ids_seen:
            continue
        doc_ids_seen.add(c.document_id)
        hits.append(
            SearchHit(type="document", id=str(c.document_id), title=c.document.title + (f" — {c.locator}" if c.locator else ""),
                      snippet=_snippet(c.text, query), url=f"/documents/{c.document_id}")
        )
    from ..core import library

    owners = library.visible_owner_ids(db, user)
    for e in db.scalars(
        select(HistoricalEvent).where(
            HistoricalEvent.owner_id.in_(owners),
            match_any([HistoricalEvent.title, HistoricalEvent.description], query),
        ).order_by(HistoricalEvent.owner_id != user.id).limit(wide)
    ):
        if not ok(e.title, e.description) or sum(1 for h in hits if h.type == "event") >= limit:
            continue
        hits.append(SearchHit(type="event", id=str(e.id), title=e.title + (" [DEMO]" if e.is_demo else ""),
                              snippet=_snippet(e.description, query), url=f"/history/events/{e.id}"))
    for ent in db.scalars(
        select(Entity).where(Entity.owner_id.in_(owners), Entity.event_id.is_(None), match_any([Entity.name], query))
        .order_by(Entity.owner_id != user.id).limit(wide)
    ):
        if not ok(ent.name) or sum(1 for h in hits if h.type == "entity") >= limit:
            continue
        hits.append(SearchHit(type="entity", id=str(ent.id), title=ent.name, snippet=ent.entity_type, url=f"/graph?focus={ent.id}"))
    for se in db.scalars(select(Series).where(Series.owner_id.in_(owners), match_any([Series.name], query))
                         .order_by(Series.owner_id != user.id).limit(wide)):
        if not ok(se.name) or sum(1 for h in hits if h.type == "series") >= limit:
            continue
        hits.append(SearchHit(type="series", id=str(se.id), title=se.name, snippet=se.source_label, url=f"/financial/series/{se.id}"))
    for rp in db.scalars(select(Report).where(Report.owner_id == user.id, match_any([Report.title], query)).limit(wide)):
        if not ok(rp.title):
            continue
        hits.append(SearchHit(type="report", id=str(rp.id), title=rp.title, snippet="approvato" if rp.status == "approved" else "bozza", url=f"/studio/reports/{rp.id}"))
    q = query.lower()
    for m in MODULES:
        if q in m.name.lower() or q in m.summary.lower():
            hits.append(
                SearchHit(
                    type="module",
                    id=m.id,
                    title=f"{m.code} · {m.name}",
                    snippet=m.summary,
                    url=f"/modules/{m.id}",
                )
            )

    db.add(SearchQuery(user_id=user.id, query=query, results_count=len(hits)))
    db.commit()
    return SearchResultOut(
        query=query,
        hits=hits,
        searched_scopes=["progetti", "documenti", "eventi storici", "entità", "serie", "rapporti", "catalogo moduli"],
        unavailable_scopes=UNAVAILABLE_SCOPES,
    )


def recent_queries(db: Session, user: User, limit: int = 8) -> list[SearchQuery]:
    """Ultime ricerche distinte (la ripetizione di una query mostra solo la più recente)."""
    rows = db.scalars(
        select(SearchQuery)
        .where(SearchQuery.user_id == user.id)
        .order_by(SearchQuery.created_at.desc(), SearchQuery.id.desc())
        .limit(limit * 10)
    )
    seen: set[str] = set()
    result: list[SearchQuery] = []
    for row in rows:
        key = row.query.casefold()
        if key not in seen:
            seen.add(key)
            result.append(row)
        if len(result) == limit:
            break
    return result
