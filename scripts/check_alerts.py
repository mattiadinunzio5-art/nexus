"""Controlla gli avvisi sulle serie dalla riga di comando (programmabile).

Uso:  scripts/py.sh scripts/check_alerts.py [--email utente@esempio]

Riscarica dalla fonte ogni serie con avvisi attivi e crea una notifica in NEXUS
per ogni nuovo dato o soglia superata.

Pianificazione:
  Linux/macOS (crontab -e, ogni giorno alle 8:05):
    5 8 * * * cd /percorso/nexus && scripts/py.sh scripts/check_alerts.py
  Windows: Utilità di pianificazione → Crea attività di base → programma
    bash.exe con argomenti: -lc "cd /c/percorso/nexus && scripts/py.sh scripts/check_alerts.py"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from nexus.core.config import get_settings  # noqa: E402
from nexus.database.migrate import upgrade_to_head  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.models import User  # noqa: E402
from nexus.services import alerts  # noqa: E402
from nexus.services.bootstrap import bootstrap  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Controlla gli avvisi NEXUS sulle serie")
    ap.add_argument("--email", help="Utente (predefinito: utente locale)")
    args = ap.parse_args()
    settings = get_settings()
    upgrade_to_head(settings.database_url)
    with Database(settings.database_url).session_factory() as db:
        user = db.scalar(select(User).where(User.email == args.email)) if args.email else bootstrap(db)
        if user is None:
            print(f"Utente non trovato: {args.email}", file=sys.stderr)
            return 1
        res = alerts.check_all(db, user, settings)
        print(f"Serie controllate: {res['checked']}")
        for e in res["errors"]:
            print(f"  serie #{e['series_id']}: {e['error']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
