"""Accesso con gli account di Supabase (versione online: stesso account del sito pubblico).

Il frontend ottiene un token di sessione da Supabase Auth e lo invia come
``Authorization: Bearer``. Il backend lo verifica chiedendo a Supabase chi è
l'utente (``GET /auth/v1/user``): così non dipende dall'algoritmo di firma dei
token. L'esito è tenuto in memoria per pochi minuti (solo l'hash del token).
Al primo accesso viene creato l'utente NEXUS collegato all'account Supabase.
"""

from __future__ import annotations

import hashlib
import threading
import time

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..database.base import utcnow
from ..models import User

CACHE_SECONDS = 120


class _Cache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> dict | None:
        with self._lock:
            hit = self._data.get(key)
            if hit and hit[0] > time.monotonic():
                return hit[1]
            self._data.pop(key, None)
            return None

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            if len(self._data) > 5000:
                self._data.clear()
            self._data[key] = (time.monotonic() + CACHE_SECONDS, value)


cache = _Cache()
_client: httpx.Client | None = None


def http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=10.0)
    return _client


def verify_token(settings: Settings, token: str) -> dict:
    """Restituisce {id, email} dell'account Supabase oppure solleva AuthError."""
    from ..services.auth import AuthError

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise AuthError("Accesso online non configurato sul server (NEXUS_SUPABASE_URL / NEXUS_SUPABASE_ANON_KEY).")
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = cache.get(key)
    if hit:
        return hit
    try:
        r = http().get(f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                       headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"})
    except httpx.HTTPError as exc:
        raise AuthError("Il servizio di accesso non è raggiungibile: riprova tra poco.") from exc
    if r.status_code != 200:
        raise AuthError("Sessione scaduta o non valida: accedi di nuovo.")
    data = r.json()
    if not data.get("id") or not data.get("email"):
        raise AuthError("Account non valido.")
    if not data.get("email_confirmed_at") and not data.get("confirmed_at"):
        raise AuthError("Conferma prima il tuo indirizzo email.")
    info = {"id": str(data["id"]), "email": str(data["email"]).lower()}
    cache.put(key, info)
    return info


def user_for(db: Session, settings: Settings, info: dict) -> User:
    """Utente NEXUS collegato all'account Supabase (creato al primo accesso)."""
    from ..services.auth import ForbiddenError

    user = db.scalar(select(User).where(User.external_id == info["id"]))
    if user is None:
        user = db.scalar(select(User).where(func.lower(User.email) == info["email"], User.is_local.is_(False)))
        if user is not None:
            user.external_id = info["id"]
    if user is None:
        admins = {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}
        user = User(email=info["email"], display_name=info["email"].split("@")[0][:120], external_id=info["id"],
                    role="admin" if info["email"] in admins else "user", plan="free", is_local=False, is_active=True)
        db.add(user)
    if not user.is_active:
        raise ForbiddenError("Account disattivato.")
    now = utcnow()
    if user.last_login_at is None or (now - _aware(user.last_login_at)).total_seconds() > 3600:
        user.last_login_at = now
    db.commit()
    db.refresh(user)
    return user


def _aware(dt):
    from datetime import UTC

    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
