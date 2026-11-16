"""Punto d'ingresso dell'applicazione FastAPI.

Avvio locale::

    uvicorn nexus.main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.router import api_router
from .core.config import Settings, get_settings
from .core.errors import register_exception_handlers
from .core.logging import configure_logging, logger
from .database.migrate import upgrade_to_head
from .database.session import Database
from .services.bootstrap import bootstrap


# L'API restituisce JSON e file: nessuna risorsa da caricare, nessun incorporamento in altri siti.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; sandbox"
# La documentazione interattiva (/docs, /redoc) carica script e stili da cdn.jsdelivr.net.
DOCS_CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; worker-src blob:; frame-ancestors 'none'; base-uri 'none'")


def security_headers(request: Request) -> dict[str, str]:
    path = request.url.path
    h = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
        "Content-Security-Policy": DOCS_CSP if path in ("/docs", "/redoc", "/docs/oauth2-redirect") else API_CSP,
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
        "Cross-Origin-Opener-Policy": "same-origin",
        "X-Permitted-Cross-Domain-Policies": "none",
    }
    # HSTS solo su HTTPS (anche dietro il proxy di Render, che indica lo schema in X-Forwarded-Proto).
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https":
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return h


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_migrate:
            upgrade_to_head(settings.database_url)
        with app.state.database.session_factory() as db:
            bootstrap(db, create_local_user=settings.auth_mode == "local")
            from .services import warroom

            n = warroom.fail_interrupted_runs(db)
            if n:
                logger.info("%s ricerche interrotte rimesse in coda per la ripresa", n)
        worker = None
        if settings.job_worker and settings.env != "test":
            from .services.jobs import Worker

            worker = Worker(app.state.database, settings)
            worker.start()
        logger.info("NEXUS %s avviato (%s, db=%s)", __version__, settings.env, settings.database_label)
        yield
        if worker:
            worker.stop()
        app.state.database.engine.dispose()

    app = FastAPI(
        title="NEXUS API",
        version=__version__,
        description="Historical & Financial Intelligence Platform — API REST.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = Database(settings.database_url)

    @app.middleware("http")
    async def unhandled_errors(request: Request, call_next):
        # Dentro il CORS: anche un errore imprevisto arriva al browser come risposta leggibile (non «backend non raggiungibile»).
        try:
            return await call_next(request)
        except Exception:  # noqa: BLE001
            logger.exception("Errore non gestito su %s %s", request.method, request.url.path)
            return JSONResponse(status_code=500, content={"error": {"code": "internal_error",
                                "message": "Errore interno del server: l'operazione non è riuscita. Riprova; se il problema continua, segnalalo con «Suggerisci»."}})

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-Nexus-Client", "X-Nexus-Lang", "Authorization"],
        expose_headers=["Content-Disposition"],
    )

    @app.middleware("http")
    async def security(request: Request, call_next):
        # Protezione CSRF: le richieste che modificano dati e si autenticano con il cookie
        # devono portare un'intestazione personalizzata (non inviabile da un sito terzo senza CORS).
        if (request.method in ("POST", "PUT", "PATCH", "DELETE") and request.cookies.get("nexus_session")
                and not request.headers.get("authorization") and request.headers.get("x-nexus-client") != "web"):
            return JSONResponse(status_code=403, content={"error": {"code": "csrf", "message": "Richiesta non consentita (intestazione X-Nexus-Client mancante)."}},
                                headers=security_headers(request))
        from .core.locale import current_lang

        # Lingua dei testi generati dal server: demo inglese, oppure interfaccia in inglese (intestazione X-Nexus-Lang).
        en = request.headers.get("authorization", "").startswith("Bearer demo.en.") or request.headers.get("x-nexus-lang", "") == "en"
        token = current_lang.set("en" if en else "it")
        try:
            response = await call_next(request)
        finally:
            current_lang.reset(token)
        for k, v in security_headers(request).items():
            response.headers.setdefault(k, v)
        return response
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
