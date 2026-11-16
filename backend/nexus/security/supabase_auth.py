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
# Token chiusi con il logout: rifiutati fino alla loro scadenza naturale (hash → istante monotonic di scadenza).
_revoked: dict[str, float] = {}
_revoked_lock = threading.Lock()
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
    if is_revoked(key):
        raise AuthError("Sessione chiusa: accedi di nuovo.")
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


def _token_ttl(token: str) -> float:
    """Secondi alla scadenza del JWT (campo exp, letto senza fidarsene: serve solo a non tenere la revoca per sempre)."""
    import base64
    import json

    try:
        payload = token.split(".")[1]
        exp = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["exp"]
        return max(60.0, min(float(exp) - time.time(), 7 * 24 * 3600))
    except Exception:  # noqa: BLE001 - token non JWT: si tiene la revoca per un'ora
        return 3600.0


def revoke(token: str) -> None:
    """Logout: il token non vale più su questo server, anche se Supabase lo considera ancora valido o è in cache."""
    key = hashlib.sha256(token.encode()).hexdigest()
    with cache._lock:
        cache._data.pop(key, None)
    now = time.monotonic()
    with _revoked_lock:
        for k in [k for k, t in _revoked.items() if t < now]:
            del _revoked[k]
        _revoked[key] = now + _token_ttl(token)


def is_revoked(key: str) -> bool:
    with _revoked_lock:
        t = _revoked.get(key)
        return t is not None and t > time.monotonic()
