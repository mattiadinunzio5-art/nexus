"""Demo pubblica in sola lettura: nessun account, contenuti reali con fonti, nessuna scrittura."""

import time


from nexus.services import demo
from tests.test_online import as_, online  # noqa: F401 — fixture


def _open(c):
    r = c.post("/api/auth/demo")
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_demo_opens_without_account_and_has_real_content(online):  # noqa: F811
    tok = _open(online)
    me = online.get("/api/me", headers=as_(tok)).json()
    assert me["email"] == demo.DEMO_EMAIL
    projects = online.get("/api/projects", headers=as_(tok)).json()
    assert [p["title"] for p in projects] == [demo.DEMO_PROJECT_TITLE]
    events = online.get("/api/history/events", headers=as_(tok)).json()
    items = events["items"] if isinstance(events, dict) else events
    assert len(items) == len(demo.EVENTS)
    assert all(e["reliability"] == "established" for e in items)
    series = online.get("/api/finance/series", headers=as_(tok)).json()
    assert len(series) == len(demo.SERIES)
    assert all(s["source_url"].startswith("https://fred.stlouisfed.org/series/") for s in series)
    sources = online.get("/api/sources", headers=as_(tok)).json()
    assert len(sources) == len(demo.SOURCES)
    # Riaprire la demo non duplica i contenuti.
    tok2 = _open(online)
    assert len(online.get("/api/projects", headers=as_(tok2)).json()) == 1


def test_demo_is_read_only(online):  # noqa: F811
    tok = _open(online)
    r = online.post("/api/projects", json={"title": "Spam"}, headers=as_(tok))
    assert r.status_code == 403 and "sola lettura" in r.json()["error"]["message"]
    sid = online.get("/api/finance/series", headers=as_(tok)).json()[0]["id"]
    assert online.delete(f"/api/finance/series/{sid}?confirm=true", headers=as_(tok)).status_code == 403


def test_demo_tokens_are_signed_and_expire(online):  # noqa: F811
    _open(online)
    assert online.get("/api/me", headers=as_("demo.9999999999.forged")).status_code == 401
    settings = online.app.state.settings
    old, _ = demo.make_token(settings, now=time.time() - 24 * 3600)
    assert online.get("/api/me", headers=as_(old)).status_code == 401


def test_demo_not_available_in_local_mode(client):
    assert client.post("/api/auth/demo").status_code == 403
    assert client.get("/api/auth/config").json()["demo"] is False
