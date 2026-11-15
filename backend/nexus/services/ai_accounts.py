"""Collegamento del proprio account AI: Gemini, ChatGPT (OpenAI), Grok (xAI) o Claude (Anthropic).

Gli abbonamenti delle app (ChatGPT Plus, Claude Pro, Gemini, SuperGrok) non si collegano ad altre applicazioni:
serve una chiave API dalla console sviluppatori del servizio. Gemini, OpenAI e xAI espongono un'API compatibile
OpenAI; Claude usa l'API Anthropic. I modelli disponibili si leggono dal servizio stesso, con la chiave dell'utente.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from ..api.schemas_finance import CredentialIn
from ..core.config import Settings
from ..core.errors import ValidationFailedError
from ..models import User
from . import ai, credentials


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    provider: str  # provider NEXUS: openai-compatible o anthropic
    base_url: str
    key_url: str
    free: str
    keep: tuple[str, ...]
    drop: tuple[str, ...] = ()


SERVICES = {
    "gemini": Service("gemini", "Google Gemini", "openai-compatible", "https://generativelanguage.googleapis.com/v1beta/openai",
                      "https://aistudio.google.com/apikey",
                      "Ha un piano gratuito; in quel piano Google può usare i testi inviati per migliorare i suoi prodotti.",
                      ("gemini",), ("embedding", "imagen", "aqa", "tts", "image", "live", "audio")),
    "openai": Service("openai", "ChatGPT (OpenAI)", "openai-compatible", "https://api.openai.com/v1",
                      "https://platform.openai.com/api-keys", "A consumo, separato dall'abbonamento ChatGPT Plus.",
                      ("gpt", "o1", "o3", "o4", "o5"), ("embedding", "tts", "whisper", "dall-e", "moderation", "image", "audio", "realtime",
                                                       "transcribe", "search", "instruct")),
    "xai": Service("xai", "Grok (xAI)", "openai-compatible", "https://api.x.ai/v1", "https://console.x.ai",
                   "A consumo, separato dall'abbonamento a Grok/X.", ("grok",), ("image", "imagine", "vision", "video")),
    "anthropic": Service("anthropic", "Claude (Anthropic)", "anthropic", "https://api.anthropic.com/v1",
                         "https://console.anthropic.com/settings/keys", "A consumo, separato dall'abbonamento Claude Pro.", ("claude",)),
}


def catalog() -> list[dict]:
    return [{"id": s.id, "name": s.name, "key_url": s.key_url, "free": s.free} for s in SERVICES.values()]


def _service(sid: str) -> Service:
    if sid not in SERVICES:
        raise ValidationFailedError("Servizio AI sconosciuto.")
    return SERVICES[sid]


def list_models(sid: str, key: str, http: httpx.Client | None = None) -> list[str]:
    """I modelli di testo disponibili con questa chiave, letti dal servizio."""
    s = _service(sid)
    if not key.strip():
        raise ValidationFailedError("Incolla la chiave API.")
    headers = ({"x-api-key": key.strip(), "anthropic-version": "2023-06-01"} if s.provider == "anthropic"
               else {"Authorization": f"Bearer {key.strip()}"})
    c = http or httpx.Client(timeout=20)
    try:
        r = c.get(f"{s.base_url}/models", headers=headers, params={"limit": 100} if s.provider == "anthropic" else None)
    except httpx.HTTPError as exc:
        raise ValidationFailedError(f"{s.name} non raggiungibile: riprova tra poco.") from exc
    if r.status_code in (401, 403):
        raise ValidationFailedError(f"{s.name} ha rifiutato la chiave: controlla di averla copiata per intero e che sia attiva.")
    if r.status_code == 429:
        raise ValidationFailedError(f"{s.name}: troppe richieste o credito esaurito. Riprova più tardi o controlla il tuo account.")
    if r.status_code >= 400:
        raise ValidationFailedError(f"{s.name} ha risposto con un errore ({r.status_code}).")
    try:
        data = r.json().get("data", [])
    except ValueError as exc:
        raise ValidationFailedError(f"Risposta non valida da {s.name}.") from exc
    ids = [str(m.get("id", "")).removeprefix("models/") for m in data if isinstance(m, dict)]
    ok = [i for i in ids if i and any(k in i.lower() for k in s.keep) and not any(d in i.lower() for d in s.drop)]
    return sorted(dict.fromkeys(ok), reverse=True)


def connect(db: Session, user: User, settings: Settings, sid: str, key: str, model: str) -> dict:
    """Salva la chiave (cifrata) e usa subito questo account per le funzioni AI dell'utente."""
    s = _service(sid)
    if not model.strip():
        raise ValidationFailedError("Scegli un modello.")
    data = CredentialIn(provider=s.provider, secret=key.strip(), model=model.strip(),
                        base_url=s.base_url if s.provider == "openai-compatible" else "")
    credentials.set_credential(db, user, settings, data, service=s.id)
    ai.select_provider(db, user, settings, s.provider)
    return {"service": s.id, "name": s.name, "model": model.strip(), "provider": s.provider}
