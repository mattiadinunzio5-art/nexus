"""Collaborazione nei progetti condivisi: commenti e cronologia delle modifiche."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.errors import NotFoundError, ValidationFailedError
from ..models import ActivityLog, Note, ProjectComment, ProjectMember, Report, User
from . import activity, notifications, sharing


def _comment_out(c: ProjectComment, author: User | None) -> dict:
    return {"id": c.id, "project_id": c.project_id, "body": c.body, "created_at": c.created_at,
            "author": {"user_id": author.id, "display_name": author.display_name} if author else None}


def list_comments(db: Session, user: User, project_id: int) -> list[dict]:
    sharing.require(db, user, project_id, "viewer")
    rows = db.execute(select(ProjectComment, User).outerjoin(User, User.id == ProjectComment.user_id)
                      .where(ProjectComment.project_id == project_id).order_by(ProjectComment.created_at, ProjectComment.id))
    return [_comment_out(c, u) for c, u in rows]


def add_comment(db: Session, user: User, project_id: int, body: str) -> dict:
    p, _ = sharing.require(db, user, project_id, "viewer")  # anche chi legge può commentare
    body = body.strip()
    if not body:
        raise ValidationFailedError("Il commento è vuoto.")
    c = ProjectComment(project_id=p.id, user_id=user.id, body=body[:5000])
    db.add(c)
    db.flush()
    others = {p.owner_id} | set(db.scalars(select(ProjectMember.user_id).where(ProjectMember.project_id == p.id)))
    for uid in others - {user.id}:
        notifications.create(db, db.get(User, uid), f"Nuovo commento in «{p.title}»", f"{user.display_name}: {body[:200]}")
    activity.record(db, user=user, actor="user", action="project.comment", entity_type="project", entity_id=p.id,
                    summary=f"Commento nel progetto «{p.title}»")
    db.commit()
    return _comment_out(c, user)


def delete_comment(db: Session, user: User, project_id: int, comment_id: int) -> None:
    _, role = sharing.require(db, user, project_id, "viewer")
    c = db.get(ProjectComment, comment_id)
    if c is None or c.project_id != project_id:
        raise NotFoundError("Commento non trovato.")
    if c.user_id != user.id and role != "owner":
        from .auth import ForbiddenError

        raise ForbiddenError("Puoi eliminare solo i tuoi commenti.")
    db.delete(c)
    db.commit()


def history(db: Session, user: User, project_id: int, limit: int = 100) -> list[dict]:
    """Cronologia: azioni sul progetto, sui suoi appunti e sui suoi rapporti, da tutti i membri."""
    sharing.require(db, user, project_id, "viewer")
    note_ids = [str(i) for i in db.scalars(select(Note.id).where(Note.project_id == project_id))]
    report_ids = [str(i) for i in db.scalars(select(Report.id).where(Report.project_id == project_id))]
    cond = [(ActivityLog.entity_type == "project") & (ActivityLog.entity_id == str(project_id))]
    if note_ids:
        cond.append((ActivityLog.entity_type == "note") & ActivityLog.entity_id.in_(note_ids))
    if report_ids:
        cond.append((ActivityLog.entity_type == "report") & ActivityLog.entity_id.in_(report_ids))
    rows = db.execute(select(ActivityLog, User).outerjoin(User, User.id == ActivityLog.user_id).where(or_(*cond))
                      .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit))
    return [{"id": a.id, "action": a.action, "summary": a.summary, "actor": a.actor, "created_at": a.created_at,
             "user": u.display_name if u else None} for a, u in rows]
