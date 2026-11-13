"""Crea i progetti di ricerca (Piano Marshall, Fondo Sociale Europeo) nell'account dell'amministratore.

Uso:  scripts/py.sh scripts/create_research_projects.py [--kit piano-marshall] [--no-series]
Online si lancia dalla GitHub Action «Progetti di ricerca» (stessi segreti dell'import della Biblioteca).
L'account è quello dell'amministratore attivo: nessun dato personale va passato come parametro.
Idempotente: un progetto già creato non viene duplicato.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from nexus.core.config import get_settings  # noqa: E402
from nexus.core.research_kits import KITS_BY_ID  # noqa: E402
from nexus.database.migrate import upgrade_to_head  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.models import User  # noqa: E402
from nexus.services import research_kits  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", choices=sorted(KITS_BY_ID), action="append", help="Kit da creare (predefinito: tutti)")
    ap.add_argument("--no-series", action="store_true", help="Non scaricare le serie dalle fonti esterne")
    args = ap.parse_args()
    settings = get_settings()
    upgrade_to_head(settings.database_url)
    db_ = Database(settings.database_url)
    with db_.session_factory() as db:
        admins = list(db.scalars(select(User).where(User.role.in_(("admin", "owner")), User.is_active.is_(True)).order_by(User.id)))
        if not admins:
            sys.exit("Nessun amministratore attivo: impossibile scegliere l'account.")
        user = next((u for u in admins if u.role == "admin"), admins[0])
        print(f"Account: utente #{user.id} ({user.role})")
        for kit_id in args.kit or list(KITS_BY_ID):
            out = research_kits.create(db, user, settings, kit_id, fetch_series=not args.no_series)
            print(kit_id, json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
