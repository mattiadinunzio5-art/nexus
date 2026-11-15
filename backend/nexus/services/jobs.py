"""Coda persistente delle ricerche della War Room, nel database (nessun servizio esterno).

Ogni ricerca è una riga di `research_runs` con stato, tentativi, battito del worker e checkpoint delle fasi.
- Presa in carico atomica (UPDATE condizionato): la stessa ricerca non può essere eseguita due volte.
- Battito (`heartbeat_at`) a ogni passo: una ricerca «in esecuzione» senza battito da LEASE secondi è orfana
  (server riavviato o caduto) e viene ripresa dall'ultima fase completata.
- Errori temporanei: nuovo tentativo dopo un'attesa crescente, fino a MAX_ATTEMPTS.
- Tempo massimo complessivo: oltre RUN_TIMEOUT la ricerca è chiusa con un errore esplicito.
- Il worker gira in un thread a parte: le richieste HTTP non aspettano le ricerche.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.logging import logger
from ..database.base import utcnow
from ..database.session import Database
from ..models import ResearchRun

LEASE_SECONDS = 120
MAX_ATTEMPTS = 3
RUN_TIMEOUT = timedelta(minutes=20)
BACKOFF_SECONDS = (0, 30, 120)


def _aware(dt: datetime | None) -> datetime | None:
    return None if dt is None else (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))


def _claimable(now: datetime):
    stale = now - timedelta(seconds=LEASE_SECONDS)
    return or_(
        and_(ResearchRun.status == "queued", or_(ResearchRun.next_attempt_at.is_(None), ResearchRun.next_attempt_at <= now)),
        and_(ResearchRun.status == "running", or_(ResearchRun.heartbeat_at.is_(None), ResearchRun.heartbeat_at < stale)),
    )


def claim(db: Session, run_id: int | None = None) -> ResearchRun | None:
    """Prende in carico una ricerca (quella indicata o la più vecchia in attesa); None se non ce n'è o è già presa."""
    now = utcnow()
    ids = [run_id] if run_id is not None else list(
        db.scalars(select(ResearchRun.id).where(_claimable(now)).order_by(ResearchRun.id).limit(5)))
    for rid in ids:
        res = db.execute(update(ResearchRun).where(ResearchRun.id == rid, _claimable(now))
                         .values(status="running", heartbeat_at=now, attempts=ResearchRun.attempts + 1)
                         .execution_options(synchronize_session=False))
        db.commit()
        if res.rowcount == 1:
            run = db.get(ResearchRun, rid)
            db.refresh(run)
            return run
    return None


def _fail(db: Session, run: ResearchRun, message: str) -> None:
    run.status, run.error, run.finished_at = "failed", message[:2000], utcnow()
    db.commit()


def process(database: Database, settings: Settings, run_id: int | None = None) -> bool:
    """Esegue una ricerca presa dalla coda. Vero se ne ha trovata una."""
    from ..agents import llm, workflow
    from ..models import User
    from . import activity, ai, notifications

    with database.session_factory() as db:
        run = claim(db, run_id)
        if run is None:
            return False
        if run.created_at and utcnow() - _aware(run.created_at) > RUN_TIMEOUT:
            _fail(db, run, f"Tempo massimo superato ({int(RUN_TIMEOUT.total_seconds() // 60)} minuti): la ricerca è stata chiusa. "
                           "I passaggi completati restano visibili; puoi avviarla di nuovo.")
            return True
        if run.attempts > MAX_ATTEMPTS:
            _fail(db, run, f"Ricerca non completata dopo {MAX_ATTEMPTS} tentativi. Ultimo problema: {run.error or 'interruzione del server'}")
            return True
        resumed = bool(run.checkpoint)
        run.started_at = run.started_at or utcnow()
        db.commit()
        user = db.get(User, run.owner_id)
        try:
            client = ai.client_for(db, user, settings) if run.mode == "ai" else None
        except llm.ProviderError as exc:
            _fail(db, run, str(exc))
            return True
        if resumed:
            logger.info("Ripresa della ricerca #%s dalla fase %s (tentativo %s)", run.id, list(run.checkpoint), run.attempts)
        try:
            workflow.execute(db, run, user, settings, client)
        except workflow.RetryableError as exc:
            run = db.get(ResearchRun, run.id)
            if run.attempts >= MAX_ATTEMPTS:
                _fail(db, run, f"Ricerca non completata dopo {MAX_ATTEMPTS} tentativi: {exc}")
            else:
                wait = BACKOFF_SECONDS[min(run.attempts, len(BACKOFF_SECONDS) - 1)]
                run.status, run.next_attempt_at = "queued", utcnow() + timedelta(seconds=wait)
                run.error = f"Tentativo {run.attempts} non riuscito ({exc}): nuovo tentativo tra {wait} secondi."
                db.commit()
                logger.warning("Ricerca #%s: errore temporaneo, nuovo tentativo tra %ss: %s", run.id, wait, exc)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.exception("Errore imprevisto nella ricerca #%s", run.id)
            db.rollback()
            _fail(db, db.get(ResearchRun, run.id), f"Errore durante la ricerca: {exc}")
            return True
        activity.record(db, user=None, actor="ai" if run.mode == "ai" else "system", action="research.finish",
                        entity_type="research_run", entity_id=run.id,
                        summary=f"Ricerca #{run.id} terminata: {run.status}" + (" (ripresa dopo un'interruzione)" if resumed else ""))
        if run.status == "awaiting_approval":
            notifications.create(db, user, f"Ricerca #{run.id} pronta per l'approvazione", run.question[:200])
        else:
            notifications.create(db, user, f"Ricerca #{run.id} non riuscita", (run.error or "")[:300], level="error")
        db.commit()
        return True


def requeue_interrupted(db: Session) -> int:
    """All'avvio: le ricerche rimaste «in esecuzione» erano del processo precedente; tornano in coda per riprendere."""
    res = db.execute(update(ResearchRun).where(ResearchRun.status == "running")
                     .values(status="queued", next_attempt_at=None, heartbeat_at=None).execution_options(synchronize_session=False))
    db.commit()
    return res.rowcount or 0


class Worker:
    """Thread che svuota la coda; uno per processo."""

    def __init__(self, database: Database, settings: Settings, interval: float = 3.0):
        self.database, self.settings, self.interval = database, settings, interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="nexus-research-queue", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                while not self._stop.is_set() and process(self.database, self.settings):
                    pass
            except Exception:  # noqa: BLE001 - il worker non deve mai fermarsi
                logger.exception("Errore nel worker della coda delle ricerche")
            self._stop.wait(self.interval)
