"""Infrastruttura comune agli importatori: Biblioteca, report, ripresa, log degli errori, pause tra richieste.

Principi: nessun dato inventato (ogni riga arriva da una fonte scaricata davvero e registrata),
idempotenza (origin + external_id), ripresa (--resume), limiti di velocità gentili verso le fonti.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..core.config import Settings
from ..core.library import ensure_library_user

USER_AGENT = "NEXUS/0.1 (open-data research platform)"


@dataclass
class Report:
    counts: dict = field(default_factory=lambda: defaultdict(lambda: {"created": 0, "skipped": 0, "errors": 0}))
    notes: list[str] = field(default_factory=list)

    def add(self, table: str, what: str, n: int = 1) -> None:
        self.counts[table][what] += n

    def note(self, msg: str) -> None:
        if msg not in self.notes:
            self.notes.append(msg)

    def render(self) -> str:
        lines = [f"{'tabella':<28}{'create':>10}{'saltate':>10}{'errori':>10}"]
        for t, c in sorted(self.counts.items()):
            lines.append(f"{t:<28}{c['created']:>10}{c['skipped']:>10}{c['errors']:>10}")
        if self.notes:
            lines += ["", "Note:"] + [f"- {n}" for n in self.notes]
        return "\n".join(lines)


class Run:
    """Contesto di un'esecuzione: sessione DB, utente Biblioteca, stato di ripresa, log errori."""

    def __init__(self, database, settings: Settings, *, area: str, limit: int | None = None, resume: bool = False,
                 pause: float = 0.25, out_dir: Path | None = None):
        self.database, self.settings, self.area = database, settings, area
        self.limit, self.resume, self.pause = limit, resume, pause
        self.report = Report()
        base = out_dir or (settings.data_dir / "imports")
        base.mkdir(parents=True, exist_ok=True)
        self.state_path = base / f"{area}.state.json"
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        self.log_path = base / f"{area}-{stamp}.errors.log"
        self.done: set[str] = set(json.loads(self.state_path.read_text())) if resume and self.state_path.exists() else set()
        self.db = database.session_factory()
        self.lib = ensure_library_user(self.db)
        self._processed = 0

    # --- ripresa e limiti ---------------------------------------------------------------
    def is_done(self, key: str) -> bool:
        return key in self.done

    def mark(self, key: str) -> None:
        self.done.add(key)
        if len(self.done) % 50 == 0:
            self.save_state()

    def save_state(self) -> None:
        self.state_path.write_text(json.dumps(sorted(self.done)))

    def budget_left(self) -> bool:
        return self.limit is None or self._processed < self.limit

    def tick(self) -> None:
        self._processed += 1

    def sleep(self) -> None:
        if self.pause:
            time.sleep(self.pause)

    # --- errori ------------------------------------------------------------------------------
    def error(self, table: str, key: str, exc: Exception | str) -> None:
        self.report.add(table, "errors")
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(UTC).isoformat()}\t{table}\t{key}\t{exc}\n")
        try:
            self.db.rollback()
        except Exception:  # noqa: BLE001
            pass

    def close(self) -> None:
        self.save_state()
        self.db.close()


def delete_origin(database, origin: str) -> dict:
    """Cancella dalla Biblioteca tutto ciò che è stato importato con un certo `origin` (i dati degli utenti restano)."""
    from sqlalchemy import delete, select

    from ..core.library import LIBRARY_EXTERNAL_ID
    from ..models import Entity, HistoricalEvent, Relation, Series, Source, User

    out = {}
    with database.session_factory() as db:
        lib = db.scalar(select(User.id).where(User.external_id == LIBRARY_EXTERNAL_ID))
        if lib is None:
            return out
        for model in (Relation, Entity, HistoricalEvent, Series, Source):
            res = db.execute(delete(model).where(model.owner_id == lib, model.origin == origin))
            out[model.__tablename__] = res.rowcount
        db.commit()
    return out
