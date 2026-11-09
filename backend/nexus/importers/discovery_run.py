"""Discovery sulla Biblioteca: solo i rilevatori deterministici già presenti (connessioni evento-dato, anomalie nelle serie).
Nessun provider AI: nessuna ipotesi generata dall'AI, nessun elemento promosso a «fatto»."""

from __future__ import annotations

from ..services import discovery
from .common import Run


def run_discovery(run: Run) -> None:
    s = discovery.create_session(run.db, run.lib, run.settings, "autonomous", "")
    if s.limits.get("max_llm_calls"):
        run.report.note("Attenzione: la sessione avrebbe usato un provider AI; annullata.")
        return
    sid = s.id
    discovery.run_in_background(run.database, run.settings, sid)
    run.db.expire_all()
    s = discovery.get_session(run.db, run.lib, sid)
    counts = (s.result or {}).get("counts", {})
    for k, v in counts.items():
        run.report.add(f"discovery_{k}", "created", int(v or 0))
    run.report.note(f"Sessione Discovery #{sid}: stato «{s.status}»" + (f" — {s.error}" if s.error else "") + ".")
