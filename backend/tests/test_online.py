"""Versione online: accesso con gli account Supabase del sito e file su Supabase Storage (risposte simulate)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from nexus.core.config import Settings
from nexus.main import create_app
from nexus.security import supabase_auth
from nexus.services import storage

USERS = {
    "tok-anna": {"id": "uuid-anna", "email": "Anna@Example.org", "email_confirmed_at": "2026-11-08T10:00:00Z"},
    "tok-bruno": {"id": "uuid-bruno", "email": "bruno@example.org", "email_confirmed_at": "2026-11-08T10:00:00Z"},
    "tok-unconfirmed": {"id": "uuid-x", "email": "x@example.org", "email_confirmed_at": None},
}


def supabase_handler(req: httpx.Request) -> httpx.Response:
    assert req.headers["apikey"] == "sb_publishable_test"
    tok = req.headers["authorization"].removeprefix("Bearer ")
    if tok in USERS:
        return httpx.Response(200, json=USERS[tok])
    return httpx.Response(401, json={"msg": "invalid JWT"})


@pytest.fixture
def online(tmp_path, monkeypatch):
    monkeypatch.setattr(supabase_auth, "_client", httpx.Client(transport=httpx.MockTransport(supabase_handler)))
    supabase_auth.cache._data.clear()
    s = Settings(env="test", database_url=f"sqlite:///{tmp_path / 'o.db'}", data_dir=tmp_path / "data", auth_mode="supabase",
                 supabase_url="https://example.supabase.co", supabase_anon_key="sb_publishable_test", secret_key="k",
                 admin_emails="anna@example.org", site_url="https://nexus.example")
    with TestClient(create_app(s)) as c:
        yield c


def as_(token):
    return {"Authorization": f"Bearer {token}"}


def test_config_exposes_only_public_values(online):
    cfg = online.get("/api/auth/config").json()
    assert cfg == {"mode": "supabase", "allow_registration": False, "demo": True, "supabase_url": "https://example.supabase.co",
                   "supabase_anon_key": "sb_publishable_test", "site_url": "https://nexus.example"}


def test_supabase_accounts_map_to_nexus_users(online):
    assert online.get("/api/projects").status_code == 401
    assert online.get("/api/projects", headers=as_("forged")).status_code == 401
    r = online.get("/api/projects", headers=as_("tok-unconfirmed"))
    assert r.status_code == 401 and "Conferma" in r.json()["error"]["message"]
    me = online.get("/api/me", headers=as_("tok-anna")).json()
    assert me["email"] == "anna@example.org" and me["role"] == "admin" and me["plan"] == "free"
    assert online.get("/api/me", headers=as_("tok-bruno")).json()["role"] == "user"
    # Dati separati per account; nessuna richiesta CSRF con il token Bearer.
    p = online.post("/api/projects", json={"title": "Di Anna"}, headers=as_("tok-anna"))
    assert p.status_code == 201
    assert online.get("/api/projects", headers=as_("tok-bruno")).json() == []
    assert online.get("/api/me", headers=as_("tok-anna")).json()["id"] == me["id"]  # stesso utente al secondo accesso
    # Registrazione e password si gestiscono sul sito.
    assert online.post("/api/auth/login", json={"email": "a@b.c", "password": "x" * 12}, headers={"X-Nexus-Client": "web"}).status_code == 403


def test_supabase_storage_roundtrip():
    files: dict[str, bytes] = {}
    calls = []

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.headers["authorization"] == "Bearer service-secret"
        calls.append((req.method, req.url.path))
        path = req.url.path
        if path == "/storage/v1/bucket/docs":
            return httpx.Response(404, json={"error": "not found"})
        if path == "/storage/v1/bucket":
            return httpx.Response(200, json={"name": "docs"})
        key = path.removeprefix("/storage/v1/object/docs/")
        if req.method == "POST":
            files[key] = req.content
            return httpx.Response(200, json={"Key": key})
        if req.method == "GET":
            return httpx.Response(200, content=files[key]) if key in files else httpx.Response(400, json={"error": "not_found"})
        if req.method == "DELETE":
            import json

            for k in json.loads(req.content)["prefixes"]:
                files.pop(k, None)
            return httpx.Response(200, json=[])
        return httpx.Response(405)

    st = storage.SupabaseStorage("https://example.supabase.co", "service-secret", "docs", client=httpx.Client(transport=httpx.MockTransport(handler)))
    st.put("uploads/1/abc.pdf", b"%PDF-1")
    assert st.get("uploads/1/abc.pdf") == b"%PDF-1"
    st.delete("uploads/1/abc.pdf")
    with pytest.raises(Exception, match="non disponibile"):
        st.get("uploads/1/abc.pdf")
    assert ("POST", "/storage/v1/bucket") in calls  # bucket privato creato al primo uso


def test_local_storage_rejects_path_traversal(tmp_path):
    st = storage.LocalStorage(tmp_path)
    st.put("uploads/1/a.txt", b"x")
    assert st.get("uploads/1/a.txt") == b"x"
    with pytest.raises(Exception):
        st.get("../../etc/passwd")


def test_database_url_normalization():
    from nexus.database.session import normalize_url

    assert normalize_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert normalize_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_url("sqlite:///x.db") == "sqlite:///x.db"
