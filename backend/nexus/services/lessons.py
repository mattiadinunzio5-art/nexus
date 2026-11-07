"""Avvio di una lezione guidata: crea progetto, appunto-guida e letture da verificare."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas import ProjectCreate
from ..core.errors import NotFoundError
from ..core.lessons import LESSONS_BY_ID
from ..models import Note, Source, User
from . import activity, projects


def get(lesson_id: str) -> dict:
    lesson = LESSONS_BY_ID.get(lesson_id)
    if lesson is None:
        raise NotFoundError("Lezione non trovata.")
    return lesson


def guide_markdown(lesson: dict) -> str:
    out = [lesson["summary"], "", "## Obiettivi", *[f"- {g}" for g in lesson["goals"]], "", "## Passi"]
    out += [f"{i}. **{s['title']}** — {s['detail']}" for i, s in enumerate(lesson["steps"], start=1)]
    out += ["", "## Date chiave (da inserire nella cronologia con una fonte)", *[f"- {d['date']}: {d['event']}" for d in lesson["key_dates"]]]
    out += ["", "## Serie da importare", *[f"- {s['label']}" for s in lesson["series"]]]
    out += ["", "Le letture consigliate sono state aggiunte alla bibliografia come «non verificate»: controllale sull'originale prima di citarle."]
    return "\n".join(out)


def start(db: Session, user: User, lesson_id: str) -> dict:
    lesson = get(lesson_id)
    p = projects.create_project(db, user, ProjectCreate(title=f"Lezione — {lesson['title']}"[:200], description=lesson["summary"]))
    note = Note(owner_id=user.id, project_id=p.id, title=f"Guida: {lesson['title']}"[:300], body=guide_markdown(lesson))
    db.add(note)
    existing = {t.lower() for t in db.scalars(select(Source.title).where(Source.owner_id == user.id))}
    added = 0
    for r in lesson["readings"]:
        if r["title"].lower() in existing:
            continue
        db.add(Source(owner_id=user.id, notes=f"Lettura consigliata dalla lezione NEXUS «{lesson['title']}». Da verificare sull'originale.", **r))
        added += 1
    db.flush()
    activity.record(db, user=user, actor="user", action="lesson.start", entity_type="project", entity_id=p.id,
                    summary=f"Iniziata la lezione «{lesson['title']}»")
    db.commit()
    return {"project_id": p.id, "note_id": note.id, "sources_added": added}
