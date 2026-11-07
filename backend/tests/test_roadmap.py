"""Avvisi sulle serie, commenti e cronologia dei progetti condivisi."""

import copy

import httpx
import pytest

from nexus.finance import connectors
from tests.test_business import H, app, signup  # noqa: F401
from tests.test_finance import WB_DATA, WB_META


@pytest.fixture
def wb_live(monkeypatch):
    """Fonte World Bank simulata i cui dati possono cambiare durante il test."""
    from nexus.services import finance as svc

    state = {"data": copy.deepcopy(WB_DATA)}

    def handler(req):
        return httpx.Response(200, json=WB_META if "/country/" not in req.url.path else state["data"])

    monkeypatch.setattr(svc, "_fetcher", lambda settings: connectors.HttpFetcher(
        connectors.Cache(settings.cache_dir, 24), client=httpx.Client(transport=httpx.MockTransport(handler))))
    return state


def test_alerts_fire_once_per_new_observation(client, wb_live):
    s = client.post("/api/finance/series/import", json={"connector": "world-bank", "indicator": "FP.CPI.TOTL.ZG", "country": "ITA"}).json()
    assert client.post("/api/finance/alerts", json={"series_id": s["id"], "kind": "above"}).status_code == 422
    client.post("/api/finance/alerts", json={"series_id": s["id"], "kind": "above", "threshold": 2})
    client.post("/api/finance/alerts", json={"series_id": s["id"], "kind": "new_data"})
    before = len(client.get("/api/notifications").json())
    # Nessun dato nuovo: nessuna notifica.
    assert client.post("/api/finance/alerts/check").json() == {"checked": 1, "errors": []}
    assert len(client.get("/api/notifications").json()) == before
    # Esce il dato 2025 = 3.1: scattano entrambi gli avvisi.
    wb_live["data"][1].insert(0, {"country": {"value": "Italy"}, "date": "2025", "value": 3.1})
    client.post("/api/finance/alerts/check")
    titles = [n["title"] for n in client.get("/api/notifications").json()]
    assert len(titles) == before + 2 and any("sopra la soglia 2" in t for t in titles) and any("Nuovo dato" in t for t in titles)
    # Stesso dato ricontrollato: nessuna nuova notifica.
    client.post("/api/finance/alerts/check")
    assert len(client.get("/api/notifications").json()) == before + 2
    alerts = client.get(f"/api/finance/alerts?series_id={s['id']}").json()
    assert all(a["last_seen_date"] == "2025-01-01" for a in alerts)
    assert client.patch(f"/api/finance/alerts/{alerts[0]['id']}?active=false").json()["active"] is False
    assert client.delete(f"/api/finance/alerts/{alerts[0]['id']}").status_code == 204


def test_comments_and_history_in_shared_project(app):  # noqa: F811
    a, _ = signup(app, "anna@example.org", "Anna")
    b, _ = signup(app, "bruno@example.org", "Bruno")
    c, _ = signup(app, "carla@example.org", "Carla")
    p = a.post("/api/projects", json={"title": "Tesi"}, headers=H).json()
    a.post(f"/api/projects/{p['id']}/members?confirm=true", json={"email": "bruno@example.org", "role": "viewer"}, headers=H)
    r = b.post(f"/api/projects/{p['id']}/comments", json={"body": "Manca la fonte del grafico 2"}, headers=H)
    assert r.status_code == 201 and r.json()["author"]["display_name"] == "Bruno"
    assert a.get("/api/notifications").json()[0]["title"] == "Nuovo commento in «Tesi»"
    assert c.get(f"/api/projects/{p['id']}/comments").status_code == 404  # non membro
    assert b.post(f"/api/projects/{p['id']}/comments", json={"body": "  "}, headers=H).status_code == 422
    cid = r.json()["id"]
    a.post(f"/api/projects/{p['id']}/comments", json={"body": "Aggiunta"}, headers=H)
    own = a.get(f"/api/projects/{p['id']}/comments").json()[1]["id"]
    assert b.delete(f"/api/projects/{p['id']}/comments/{own}", headers=H).status_code == 403
    assert a.delete(f"/api/projects/{p['id']}/comments/{cid}", headers=H).status_code == 204
    hist = b.get(f"/api/projects/{p['id']}/history").json()
    assert {"project.share", "project.comment"} <= {h["action"] for h in hist}
    assert any(h["user"] == "Bruno" for h in hist)


def test_lessons_start_creates_project_guide_and_unverified_readings(client):
    from nexus.core.lessons import LESSONS
    from nexus.finance.connectors import _SDMX_KEY

    lst = client.get("/api/lessons").json()
    assert [x["id"] for x in lst] == ["crisi-1929", "inflazione-anni-70", "crisi-2008"]
    for lesson in LESSONS:
        for s in lesson["series"]:  # ogni serie proposta è un import valido
            from nexus.api.schemas_finance import SeriesImportIn

            SeriesImportIn(category=s["category"], **s["params"])
            if s["params"]["connector"] == "ecb":
                assert _SDMX_KEY.fullmatch(s["params"]["key"])
    assert client.get("/api/lessons/nessuna").status_code == 404
    r = client.post("/api/lessons/crisi-1929/start")
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["sources_added"] == 3
    notes = client.get(f"/api/notes?project_id={out['project_id']}").json()
    assert len(notes) == 1 and "1929-10-24" in notes[0]["body"]
    srcs = client.get("/api/sources").json()
    assert all(s["verification_status"] == "unverified" for s in srcs)
    # Seconda volta: nuovo progetto, letture non duplicate.
    assert client.post("/api/lessons/crisi-1929/start").json()["sources_added"] == 0
