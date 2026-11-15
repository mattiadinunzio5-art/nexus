"""Ambito di progetto: gli elementi (propri o della Biblioteca) collegati a un progetto e la panoramica della ricerca.

Un progetto raccoglie documenti, fonti, eventi, entità, serie e relazioni. Le schermate possono mostrare
«solo progetto» (gli elementi collegati), «le mie», «solo Biblioteca» o «tutto»: così migliaia di voci della
Biblioteca non sommergono la ricerca in corso. Collegare un elemento della Biblioteca non lo copia.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..core import library
from ..core.errors import NotFoundError, ValidationFailedError
from ..models import Document, Entity, HistoricalEvent, Project, ProjectItem, Relation, Series, Source, User
from ..models.project_item import PROJECT_ITEM_TYPES
from . import activity, sharing

MODELS = {"document": Document, "source": Source, "event": HistoricalEvent, "entity": Entity, "series": Series, "relation": Relation}
LABEL = {"document": "documento", "source": "fonte", "event": "evento", "entity": "entità", "series": "serie", "relation": "relazione"}


def _check_type(item_type: str) -> None:
    if item_type not in PROJECT_ITEM_TYPES:
        raise ValidationFailedError("Tipo di elemento non valido.")


def item_ids(db: Session, user: User, project_id: int, item_type: str):
    """Sottoquery degli id collegati al progetto (per i documenti anche quelli caricati con quel progetto)."""
    _check_type(item_type)
    sharing.require(db, user, project_id, "viewer")
    q = select(ProjectItem.item_id).where(ProjectItem.project_id == project_id, ProjectItem.item_type == item_type)
    if item_type == "document":
        q = q.union(select(Document.id).where(Document.project_id == project_id))
    return q


def scope_filter(db: Session, user: User, model, item_type: str, project_id: int | None):
    """Condizione da aggiungere a un elenco quando si chiede «solo progetto»; None se non serve."""
    if project_id is None:
        return None
    return model.id.in_(item_ids(db, user, project_id, item_type))


def _visible(db: Session, user: User, item_type: str, item_id: int):
    obj = db.get(MODELS[item_type], item_id)
    if obj is None or not library.can_read(db, user, obj.owner_id):
        raise NotFoundError(f"{LABEL[item_type].capitalize()} non trovato.")
    return obj


def add(db: Session, user: User, project_id: int, item_type: str, item_id: int, note: str = "") -> dict:
    _check_type(item_type)
    project, _ = sharing.require(db, user, project_id, "editor")
    obj = _visible(db, user, item_type, item_id)
    exists = db.scalar(select(ProjectItem).where(ProjectItem.project_id == project_id, ProjectItem.item_type == item_type,
                                                 ProjectItem.item_id == item_id))
    if exists is None:
        db.add(ProjectItem(project_id=project_id, item_type=item_type, item_id=item_id, added_by=user.id, note=note[:1000]))
        # Un evento porta con sé la sua entità nel grafo, e viceversa: restano collegati nel progetto.
        if item_type == "event":
            ent = db.scalar(select(Entity.id).where(Entity.event_id == item_id))
            if ent and not db.scalar(select(ProjectItem.id).where(ProjectItem.project_id == project_id, ProjectItem.item_type == "entity",
                                                                  ProjectItem.item_id == ent)):
                db.add(ProjectItem(project_id=project_id, item_type="entity", item_id=ent, added_by=user.id))
        activity.record(db, user=user, actor="user", action="project.item_add", entity_type="project", entity_id=project_id,
                        summary=f"Collegato al progetto «{project.title[:60]}»: {LABEL[item_type]} «{_label(item_type, obj)[:80]}»"
                                + (" (Biblioteca)" if library.is_library(db, obj.owner_id) else ""))
        from ..database.base import utcnow

        project.updated_at = utcnow()
        db.commit()
    return {"project_id": project_id, "item_type": item_type, "item_id": item_id, "linked": True}


def remove(db: Session, user: User, project_id: int, item_type: str, item_id: int) -> None:
    _check_type(item_type)
    sharing.require(db, user, project_id, "editor")
    row = db.scalar(select(ProjectItem).where(ProjectItem.project_id == project_id, ProjectItem.item_type == item_type,
                                              ProjectItem.item_id == item_id))
    if item_type == "document":
        d = db.get(Document, item_id)
        if d is not None and d.project_id == project_id and d.owner_id == user.id:
            d.project_id = None
    if row is not None:
        db.delete(row)
    db.commit()


def _label(item_type: str, obj) -> str:
    if item_type == "relation":
        return f"{obj.relation_type} ({obj.source_entity_id} → {obj.target_entity_id})"
    return getattr(obj, "title", None) or getattr(obj, "name", None) or f"#{obj.id}"


def projects_of(db: Session, user: User, item_type: str, item_id: int) -> list[int]:
    """I progetti dell'utente a cui l'elemento è collegato (per il pulsante «Aggiungi al progetto»)."""
    _check_type(item_type)
    from . import projects as projects_svc

    mine = {p.id for p in projects_svc.list_projects(db, user, None)}
    rows = set(db.scalars(select(ProjectItem.project_id).where(ProjectItem.item_type == item_type, ProjectItem.item_id == item_id)))
    if item_type == "document":
        d = db.get(Document, item_id)
        if d is not None and d.project_id:
            rows.add(d.project_id)
    return sorted(rows & mine)


def overview(db: Session, user: User, project_id: int) -> dict:
    """Stato della ricerca: elementi collegati e cosa manca, con controlli espliciti."""
    from ..models import Report, ResearchRun

    project, role = sharing.require(db, user, project_id, "viewer")
    counts = {}
    for t, model in MODELS.items():
        counts[t] = db.scalar(select(func.count()).select_from(model).where(model.id.in_(item_ids(db, user, project_id, t)))) or 0
    src_ids = item_ids(db, user, project_id, "source")
    verified = db.scalar(select(func.count()).select_from(Source).where(
        Source.id.in_(src_ids), Source.verification_status.in_(("verified_user", "verified_registry")))) or 0
    lib = library.library_user_id(db)
    from_library = 0
    if lib is not None:
        for t, model in MODELS.items():
            from_library += db.scalar(select(func.count()).select_from(model).where(model.id.in_(item_ids(db, user, project_id, t)),
                                                                                     model.owner_id == lib)) or 0
    reports = list(db.scalars(select(Report).where(Report.project_id == project_id)))
    runs = db.scalar(select(func.count()).select_from(ResearchRun).where(ResearchRun.project_id == project_id)) or 0
    filled = [r for r in reports if any((s.body or "").strip() for s in r.sections)]
    checks = [
        {"key": "question", "label": "Domanda di ricerca definita", "ok": bool(project.research_question.strip())},
        {"key": "objectives", "label": "Obiettivi definiti", "ok": bool(project.objectives.strip())},
        {"key": "hypotheses", "label": "Ipotesi di lavoro formulate", "ok": bool(project.hypotheses.strip())},
        {"key": "period", "label": "Periodo indicato", "ok": project.period_start is not None and project.period_end is not None},
        {"key": "scope", "label": "Perimetro (paesi, settori) indicato", "ok": bool(project.scope.strip())},
        {"key": "documents", "label": "Almeno un documento collegato", "ok": counts["document"] > 0},
        {"key": "sources", "label": "Almeno 3 fonti in bibliografia", "ok": counts["source"] >= 3, "detail": f"{counts['source']} fonti"},
        {"key": "verified", "label": "Almeno metà delle fonti verificate", "ok": counts["source"] > 0 and verified * 2 >= counts["source"],
         "detail": f"{verified} su {counts['source']} verificate"},
        {"key": "data", "label": "Dati o eventi collegati", "ok": counts["series"] + counts["event"] > 0},
        {"key": "report", "label": "Un rapporto con testo", "ok": bool(filled), "detail": f"{len(reports)} rapporti"},
    ]
    done = sum(1 for c in checks if c["ok"])
    return {"project_id": project_id, "role": role, "counts": counts, "from_library": from_library, "verified_sources": verified,
            "reports": [{"id": r.id, "title": r.title, "status": r.status} for r in reports], "research_runs": runs,
            "checks": checks, "progress": round(done / len(checks), 2)}


def list_items(db: Session, user: User, project_id: int, item_type: str, limit: int = 200) -> list[dict]:
    model = MODELS[item_type] if item_type in MODELS else None
    if model is None:
        raise ValidationFailedError("Tipo di elemento non valido.")
    rows = db.scalars(select(model).where(model.id.in_(item_ids(db, user, project_id, item_type)),
                                          or_(*[model.owner_id == o for o in library.visible_owner_ids(db, user)]))
                      .order_by(model.id.desc()).limit(limit))
    return [{"id": o.id, "label": _label(item_type, o), "library": library.is_library(db, o.owner_id)} for o in rows]


def ensure_project(db: Session, project_id: int) -> Project:
    p = db.get(Project, project_id)
    if p is None:
        raise NotFoundError("Progetto non trovato.")
    return p
