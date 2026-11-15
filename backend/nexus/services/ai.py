"""Selezione del provider AI per utente e costruzione del client."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..agents import llm
from ..agents.providers import AI_PROVIDERS
from ..core.config import Settings
from ..core.errors import ValidationFailedError
from ..models import User, UserPreference
from . import activity, credentials

PREF_KEY = "ai.provider"
PLATFORM_KEY = "ai.platform"  # preferenza dell'amministratore: AI condivisa con tutti gli utenti
USAGE_KEY = "ai.usage"
DEFAULT_DAILY_LIMIT = 30


def platform(db: Session) -> tuple[User, dict] | None:
    """L'AI della piattaforma, se un amministratore attivo l'ha condivisa: (amministratore, impostazioni)."""
    from sqlalchemy import select

    row = db.execute(
        select(User, UserPreference).join(UserPreference, UserPreference.user_id == User.id)
        .where(UserPreference.key == PLATFORM_KEY, User.role == "admin", User.is_active.is_(True)).order_by(User.id)
    ).first()
    if row is None or not row[1].value.get("enabled"):
        return None
    return row[0], dict(row[1].value)


def _own_choice(db: Session, user: User) -> str | None:
    """Provider scelto dall'utente; None se non ha scelto (o se «nessuno» non era una scelta esplicita)."""
    pref = db.get(UserPreference, (user.id, PREF_KEY))
    if not pref:
        return None
    p = pref.value.get("provider", "none")
    if p == "none" and not pref.value.get("explicit"):
        return None
    return p


def uses_platform(db: Session, user: User, settings: Settings) -> bool:
    own = _own_choice(db, user)
    if own is not None:
        return False
    return platform(db) is not None


def selected_provider(db: Session, user: User, settings: Settings) -> str:
    own = _own_choice(db, user)
    if own is not None:
        return own
    plat = platform(db)
    if plat:
        return plat[1].get("provider", "none")
    return settings.ai_provider if settings.ai_provider in {p.id for p in AI_PROVIDERS} else "none"


def usage_today(db: Session, user: User) -> int:
    from datetime import date

    pref = db.get(UserPreference, (user.id, USAGE_KEY))
    if not pref or pref.value.get("day") != date.today().isoformat():
        return 0
    return int(pref.value.get("count", 0))


class LimitedClient(llm.LLMClient):
    """Client dell'AI condivisa: conta le chiamate dell'utente e si ferma al limite giornaliero."""

    def __init__(self, inner: llm.LLMClient, db: Session, user: User, daily_limit: int):
        self.inner, self.db, self.user, self.limit = inner, db, user, daily_limit
        self.provider, self.model = inner.provider, inner.model

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> llm.LLMResult:
        from datetime import date

        today = date.today().isoformat()
        used = usage_today(self.db, self.user)
        if used >= self.limit:
            raise llm.ProviderError(f"Limite giornaliero dell'AI condivisa raggiunto ({self.limit} richieste): riprova domani "
                                    "o configura un tuo provider in Sistema. Le funzioni locali restano disponibili.")
        pref = self.db.get(UserPreference, (self.user.id, USAGE_KEY))
        value = {"day": today, "count": used + 1}
        if pref:
            pref.value = value
        else:
            self.db.add(UserPreference(user_id=self.user.id, key=USAGE_KEY, value=value))
        self.db.commit()
        return self.inner.complete(system, user, max_tokens)


def set_platform(db: Session, admin: User, settings: Settings, enabled: bool, provider: str, daily_limit: int) -> dict:
    """L'amministratore condivide (o smette di condividere) il proprio provider con tutti gli utenti."""
    if provider not in ("ollama", "openai-compatible", "anthropic"):
        raise ValidationFailedError("Scegli un provider AI da condividere.")
    if enabled:
        secret, cfg = credentials.get_secret(db, admin, settings, provider)
        if secret is None and not cfg:
            raise ValidationFailedError("Configura prima le credenziali di questo provider (Sistema → Credenziali).")
    value = {"enabled": enabled, "provider": provider, "daily_limit": daily_limit}
    pref = db.get(UserPreference, (admin.id, PLATFORM_KEY))
    if pref:
        pref.value = value
    else:
        db.add(UserPreference(user_id=admin.id, key=PLATFORM_KEY, value=value))
    activity.record(db, user=admin, actor="user", action="ai.platform",
                    summary=f"AI condivisa con tutti gli utenti: {'attiva' if enabled else 'disattivata'} ({provider}, {daily_limit} richieste al giorno)")
    db.commit()
    return value


def status(db: Session, user: User, settings: Settings) -> dict:
    plat = platform(db)
    shared = uses_platform(db, user, settings)
    limit = int(plat[1].get("daily_limit", DEFAULT_DAILY_LIMIT)) if plat else 0
    return {"provider": effective_provider(db, user, settings), "shared": shared, "shared_available": plat is not None,
            "daily_limit": limit if shared else None, "used_today": usage_today(db, user) if shared else None}


def select_provider(db: Session, user: User, settings: Settings, provider: str, effort: str = "medium") -> dict:
    if provider not in {p.id for p in AI_PROVIDERS}:
        raise ValidationFailedError("Provider sconosciuto.")
    if provider != "none":
        secret, cfg = credentials.get_secret(db, user, settings, provider)
        if secret is None and not cfg:
            raise ValidationFailedError("Configura prima le credenziali di questo provider (Sistema → Credenziali).")
    value = {"provider": provider, "effort": effort, "explicit": True}
    pref = db.get(UserPreference, (user.id, PREF_KEY))
    if pref:
        pref.value = value
    else:
        db.add(UserPreference(user_id=user.id, key=PREF_KEY, value=value))
    activity.record(db, user=user, actor="user", action="ai.provider", summary=f"Provider AI selezionato: {provider}")
    db.commit()
    return value


def client_for(db: Session, user: User, settings: Settings) -> llm.LLMClient | None:
    """Client del provider selezionato, oppure None in modalità locale."""
    provider = selected_provider(db, user, settings)
    if provider == "none":
        return None
    plat = platform(db) if uses_platform(db, user, settings) else None
    owner = plat[0] if plat else user  # con l'AI condivisa si usano le credenziali dell'amministratore, mai mostrate
    secret, cfg = credentials.get_secret(db, owner, settings, provider)
    pref = db.get(UserPreference, (owner.id, PREF_KEY))
    effort = (pref.value.get("effort") if pref else None) or "medium"
    client: llm.LLMClient | None = None
    if provider == "ollama":
        client = llm.OllamaClient(cfg.get("base_url", ""), cfg.get("model", ""))
    elif provider == "openai-compatible":
        client = llm.OpenAICompatibleClient(cfg.get("base_url", ""), secret, cfg.get("model", ""))
    elif provider == "anthropic":
        if not secret:
            raise llm.ProviderError("Chiave Anthropic non configurata.")
        client = llm.AnthropicClient(secret, cfg.get("model") or None, effort=effort)
    if client is not None and plat:
        return LimitedClient(client, db, user, int(plat[1].get("daily_limit", DEFAULT_DAILY_LIMIT)))
    return client


def effective_provider(db: Session, user: User, settings: Settings) -> str:
    """Provider realmente utilizzabile: 'none' se mancano le credenziali."""
    provider = selected_provider(db, user, settings)
    if provider == "none":
        return "none"
    plat = platform(db) if uses_platform(db, user, settings) else None
    secret, cfg = credentials.get_secret(db, plat[0] if plat else user, settings, provider)
    if provider in ("anthropic",) and not secret:
        return "none"
    if provider in ("ollama", "openai-compatible") and not cfg:
        return "none"
    return provider
