"""Reimposta la password di un account NEXUS (modalità multi-utente, es. con dev.sh --lan).

Uso:  scripts/py.sh scripts/reset_password.py

Mostra gli account esistenti, chiede l'email e la nuova password. Funziona solo sul computer
dove gira NEXUS (serve accesso al database): nessuno può usarlo dalla rete.
Tutte le sessioni aperte di quell'account vengono chiuse.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import delete, func, select  # noqa: E402

from nexus.core.config import get_settings  # noqa: E402
from nexus.database.migrate import upgrade_to_head  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.models import AuthSession, User  # noqa: E402
from nexus.security.passwords import hash_password, password_problems  # noqa: E402


def main() -> int:
    settings = get_settings()
    upgrade_to_head(settings.database_url)
    with Database(settings.database_url).session_factory() as db:
        users = list(db.scalars(select(User).where(User.is_local.is_(False)).order_by(User.id)))
        if not users:
            print("Nessun account registrato: apri NEXUS e usa «Crea account».")
            return 1
        print("Account presenti:")
        for u in users:
            print(f"  - {u.email}  ({u.display_name})")
        email = input("\nEmail dell'account: ").strip().lower()
        user = db.scalar(select(User).where(func.lower(User.email) == email, User.is_local.is_(False)))
        if user is None:
            print("Account non trovato.")
            return 1
        print("Attenzione: la password sarà visibile mentre la scrivi.")
        pw = input("Nuova password: ")
        problems = password_problems(pw)
        if problems:
            print("Password non valida: " + "; ".join(problems))
            return 1
        if input("Ripeti la password: ") != pw:
            print("Le password non coincidono.")
            return 1
        user.password_hash = hash_password(pw)
        db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
        db.commit()
        print(f"Password aggiornata per {user.email}. Riavvia NEXUS (Ctrl+C, poi scripts/dev.sh --lan) e accedi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
