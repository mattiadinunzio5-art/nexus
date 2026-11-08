"""Engine e sessioni del database.

L'URL è configurabile (``NEXUS_DATABASE_URL``): SQLite in locale, PostgreSQL in
futuro senza modifiche al codice applicativo.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def normalize_url(url: str) -> str:
    """Accetta anche gli URL PostgreSQL «nudi» (es. quelli forniti da Supabase) usando il driver psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def build_engine(url: str) -> Engine:
    url = normalize_url(url)
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        db_path = url.split("///", 1)[-1]
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    kwargs: dict = {}
    if url.startswith("postgresql"):
        # Connessioni gestite dal pooler di Supabase: verifica prima dell'uso, pool piccolo (server gratuito).
        kwargs.update(pool_pre_ping=True, pool_size=3, max_overflow=2, pool_recycle=300)
    engine = create_engine(url, connect_args=connect_args, future=True, **kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _):  # pragma: no cover - driver hook
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    return engine


class Database:
    """Contenitore di engine + session factory, creato una volta per app."""

    def __init__(self, url: str):
        self.url = url
        self.engine = build_engine(url)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def session(self) -> Iterator[Session]:
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()
