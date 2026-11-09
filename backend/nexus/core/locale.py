"""Lingua dei testi generati dal server per la richiesta corrente (default italiano).

Oggi serve solo alla demo pubblica in inglese: un middleware imposta "en" quando
la richiesta usa un token della demo inglese.
"""

from contextvars import ContextVar

current_lang: ContextVar[str] = ContextVar("nexus_lang", default="it")
