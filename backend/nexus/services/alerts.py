"""Avvisi sulle serie: nuovo dato pubblicato o soglia superata.

Gli avvisi vengono valutati quando una serie viene aggiornata dalla fonte
(«Aggiorna», «Controlla avvisi ora» o lo script scripts/check_alerts.py
pianificato dall'utente). Ogni avviso scatta una sola volta per ogni nuova
osservazione: nessuna notifica ripetuta sullo stesso dato.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.errors import NotFoundError, ValidationFailedError
from ..database.base import utcnow
from ..models import Series, SeriesAlert, User
from . import activity, notifications


def _fmt(v: float) -> str:
    return f"{v:,.4g}".replace(",", " ")


def _latest(s: Series) -> tuple[str, float] | None:
    for o in reversed(s.observations):
        if o.value is not None:
            return o.date, o.value
    return None


def create(db: Session, user: User, series_id: int, kind: str, threshold: float | None) -> SeriesAlert:
    s = db.get(Series, series_id)
    if s is None or s.owner_id != user.id:
        raise NotFoundError("Serie non trovata.")
    if kind in ("above", "below") and threshold is None:
        raise ValidationFailedError("Indica la soglia per questo avviso.")
    if kind == "new_data":
        threshold = None
    if s.connector == "upload":
        raise ValidationFailedError("Le serie caricate da CSV non si aggiornano da una fonte: nessun avviso possibile.")
    latest = _latest(s)
    a = SeriesAlert(owner_id=user.id, series_id=s.id, kind=kind, threshold=threshold, last_seen_date=latest[0] if latest else None)
    db.add(a)
    db.flush()
    activity.record(db, user=user, actor="user", action="alert.create", entity_type="series", entity_id=s.id,
                    summary=f"Creato un avviso sulla serie «{s.name}»")
    db.commit()
    db.refresh(a)
    return a


def list_for_user(db: Session, user: User, series_id: int | None = None) -> list[SeriesAlert]:
    stmt = select(SeriesAlert).where(SeriesAlert.owner_id == user.id)
    if series_id is not None:
        stmt = stmt.where(SeriesAlert.series_id == series_id)
    return list(db.scalars(stmt.order_by(SeriesAlert.id)))


def _get(db: Session, user: User, alert_id: int) -> SeriesAlert:
    a = db.get(SeriesAlert, alert_id)
    if a is None or a.owner_id != user.id:
        raise NotFoundError("Avviso non trovato.")
    return a


def set_active(db: Session, user: User, alert_id: int, active: bool) -> SeriesAlert:
    a = _get(db, user, alert_id)
    a.active = active
    db.commit()
    db.refresh(a)
    return a


def delete(db: Session, user: User, alert_id: int) -> None:
    db.delete(_get(db, user, alert_id))
    db.commit()


def evaluate(db: Session, s: Series) -> int:
    """Valuta gli avvisi attivi di una serie appena aggiornata. Restituisce quanti sono scattati."""
    latest = _latest(s)
    if latest is None:
        return 0
    date, value = latest
    fired = 0
    for a in db.scalars(select(SeriesAlert).where(SeriesAlert.series_id == s.id, SeriesAlert.active.is_(True))):
        if a.last_seen_date is not None and date <= a.last_seen_date:
            continue
        a.last_seen_date = date
        user = db.get(User, a.owner_id)
        src = f"Fonte: {s.source_label}. Dato del {date}: {_fmt(value)} {s.unit}".strip()
        if a.kind == "new_data":
            title = f"Nuovo dato per «{s.name}»"
        elif a.kind == "above" and value > a.threshold:
            title = f"«{s.name}» sopra la soglia {_fmt(a.threshold)}"
        elif a.kind == "below" and value < a.threshold:
            title = f"«{s.name}» sotto la soglia {_fmt(a.threshold)}"
        else:
            continue
        notifications.create(db, user, title[:300], src, level="warning" if a.kind != "new_data" else "info")
        a.last_triggered_at = utcnow()
        fired += 1
    return fired


def check_all(db: Session, user: User, settings: Settings) -> dict:
    """Aggiorna dalla fonte ogni serie con avvisi attivi e valuta gli avvisi."""
    from . import finance

    ids = sorted({a.series_id for a in list_for_user(db, user) if a.active})
    checked, errors = 0, []
    for sid in ids:
        try:
            finance.refresh(db, user, settings, sid)
            checked += 1
        except Exception as exc:  # una fonte irraggiungibile non blocca le altre
            db.rollback()
            errors.append({"series_id": sid, "error": str(exc)[:300]})
    return {"checked": checked, "errors": errors}
