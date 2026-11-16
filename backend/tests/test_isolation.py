"""Isolamento tra utenti e ruoli, in modo sistematico.

Quattro account (modalità multi-utente): Anna (proprietaria), Bruno (editor del progetto condiviso),
Carla (viewer del progetto condiviso), Dario (estraneo). Anna crea dati in ogni area dell'app.
Si chiamano TUTTE le rotte dell'API che hanno un identificativo nel percorso (elenco preso dallo schema
OpenAPI, quindi una rotta nuova entra da sola nel controllo) con gli ID di Anna:

* l'estraneo e i membri non devono mai ottenere 2xx sui dati privati di Anna, né vederne il contenuto;
* dopo tutti i tentativi i dati di Anna devono essere identici a prima (nessuna modifica riuscita);
* manipolazione degli ID nei corpi delle richieste (collegare risorse altrui ai propri oggetti);
* permessi dei ruoli sul progetto condiviso (viewer sola lettura, editor senza poteri da proprietario).
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from nexus.core.config import Settings
from nexus.main import create_app
from nexus.services import auth as auth_svc

H = {"X-Nexus-Client": "web"}
PWD = "Archivio-Storico-2026"
SECRET = "SEGRETO-ANNA"
SHARED = "CONDIVISO"


def _signup(app, email):
    c = TestClient(app)
    r = c.post("/api/auth/register", json={"email": email, "password": PWD, "display_name": email.split("@")[0]})
    assert r.status_code == 201, r.text
    c.headers.update(H)
    return c, r.json()


def ok(r, code=(200, 201)):
    assert r.status_code in (code if isinstance(code, tuple) else (code,)), r.text
    return r.json() if r.content else None


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("iso")
    s = Settings(env="test", database_url=f"sqlite:///{tmp / 'i.db'}", data_dir=tmp / "data", auth_mode="multi", secret_key="iso-key")
    auth_svc.limiter._fails.clear()
    app = create_app(s)
    with TestClient(app):
        _signup(app, "root@example.org")  # primo account = amministratore: gli altri sono utenti normali
        a, ua = _signup(app, "anna@example.org")
        b, ub = _signup(app, "bruno@example.org")
        c, uc = _signup(app, "carla@example.org")
        d, ud = _signup(app, "dario@example.org")
        ids = _populate(app, a, ua)
        ok(a.post(f"/api/projects/{ids['shared_project']}/members?confirm=true", json={"email": "bruno@example.org", "role": "editor"}))
        ok(a.post(f"/api/projects/{ids['shared_project']}/members?confirm=true", json={"email": "carla@example.org", "role": "viewer"}))
        ids.update(member_user_id=ub["id"], anna_id=ua["id"])
        yield {"app": app, "a": a, "b": b, "c": c, "d": d, "ids": ids, "users": {"a": ua, "b": ub, "c": uc, "d": ud}}


def _populate(app, a, ua) -> dict:
    from nexus.database.base import utcnow
    from nexus.models import (AuthSession, SeriesAlert, DiscoveryAnalysis, DiscoveryAnomaly, DiscoveryConnection, DiscoveryHypothesis,
                              DiscoverySession, Notification, ResearchRun)

    ids: dict = {}
    ids["project_id"] = ok(a.post("/api/projects", json={"title": f"Progetto {SECRET}"}))["id"]
    ids["shared_project"] = ok(a.post("/api/projects", json={"title": f"Progetto {SHARED}"}))["id"]
    ids["document_id"] = ok(a.post("/api/documents", files={"file": ("n.txt", f"Appunti {SECRET} sulla lira del 1861.".encode())}))["id"]
    gone = ok(a.post("/api/documents", files={"file": ("g.txt", f"Bozza {SECRET} eliminata.".encode())}))["id"]
    ok(a.delete(f"/api/documents/{gone}?confirm=true"))
    ids["trash_id"] = ok(a.get("/api/documents/trash"))[0]["id"]
    ids["source_id"] = ok(a.post("/api/sources", json={"title": f"Fonte {SECRET}", "year": 1950}))["id"]
    ev = ok(a.post("/api/history/events", json={"title": f"Evento {SECRET}", "start_year": 1948}))
    ids["event_id"] = ev["id"]
    ok(a.post(f"/api/history/events/{ev['id']}/sources", json={"source_id": ids["source_id"], "pages": "1"}))
    ids["item_id"] = ok(a.post(f"/api/history/events/{ev['id']}/knowledge", json={"content": f"Nota {SECRET}", "known_since_year": 1948}))["knowledge"][0]["id"]
    e1 = ok(a.post("/api/graph/entities", json={"entity_type": "person", "name": f"Persona {SECRET}"}))["id"]
    e2 = ok(a.post("/api/graph/entities", json={"entity_type": "institution", "name": f"Ente {SECRET}"}))["id"]
    ids["entity_id"] = e1
    ids["relation_id"] = ok(a.post("/api/graph/relations", json={"source_entity_id": e1, "target_entity_id": e2, "relation_type": "influenced",
                                                                 "provenance": "user_hypothesis"}))["id"]
    ids["series_id"] = ok(a.post("/api/finance/series/upload", files={"file": ("s.csv", b"anno,valore\n2001,1\n2002,2\n2003,3\n")},
                                 data={"name": f"Serie {SECRET}", "source_label": "Dati riservati"}))["id"]
    ok(a.put("/api/credentials", json={"provider": "fred", "secret": "chiave-di-anna-1234567890"}))
    rep = ok(a.post("/api/reports", json={"title": f"Rapporto {SECRET}"}))
    ids["report_id"] = rep["id"]
    ids["section_id"] = rep["sections"][3]["id"]
    ok(a.put(f"/api/reports/{rep['id']}/sections/{ids['section_id']}", json={"body": f"Prima {SECRET}"}))
    ok(a.put(f"/api/reports/{rep['id']}/sections/{ids['section_id']}", json={"body": f"Seconda {SECRET}"}))
    ids["version_id"] = ok(a.get(f"/api/reports/{rep['id']}/sections/{ids['section_id']}/versions"))[0]["id"]
    srep = ok(a.post("/api/reports", json={"title": f"Rapporto {SHARED}", "project_id": ids["shared_project"]}))
    ids["shared_report"], ids["shared_section"] = srep["id"], srep["sections"][3]["id"]
    ids["note_id"] = ok(a.post("/api/notes", json={"title": f"Nota {SECRET}"}))["id"]
    ids["shared_note"] = ok(a.post("/api/notes", json={"title": f"Nota {SHARED}", "project_id": ids["shared_project"]}))["id"]
    ids["comment_id"] = ok(a.post(f"/api/projects/{ids['shared_project']}/comments", json={"body": f"Commento {SHARED}"}))["id"]
    ok(a.post(f"/api/projects/{ids['project_id']}/items", json={"item_type": "document", "item_id": ids["document_id"]}))
    ids["sim_id"] = ok(a.post("/api/lab/simulations/inflation", json={"title": f"Simulazione {SECRET}", "amount": 100, "nominal_rate": 0.02,
                                                                      "years": 5, "inflation_levels": [0.02]}))["id"]
    ids["briefing_id"] = ok(a.post("/api/briefings", json={}))["id"]
    with app.state.database.session_factory() as db:
        run = ResearchRun(owner_id=ua["id"], question=f"Domanda {SECRET}", mode="local", status="approved", plan={}, evidence=[], result={})
        sess = DiscoverySession(owner_id=ua["id"], mode="guided", query=f"Ricerca {SECRET}", status="completed")
        db.add_all([run, sess])
        db.flush()
        conn = DiscoveryConnection(owner_id=ua["id"], session_id=sess.id, fingerprint="f1", kind="shared_actors", title=f"Connessione {SECRET}")
        db.add(conn)
        db.flush()
        hyp = DiscoveryHypothesis(owner_id=ua["id"], connection_id=conn.id, fingerprint="f1", title=f"Ipotesi {SECRET}")
        an = DiscoveryAnomaly(owner_id=ua["id"], fingerprint="f1", kind="series_change", title=f"Anomalia {SECRET}")
        aa = DiscoveryAnalysis(owner_id=ua["id"], kind="causal_chain", title=f"Analisi {SECRET}", params={}, result={})
        note = Notification(user_id=ua["id"], title=f"Notifica {SECRET}")
        alert = SeriesAlert(owner_id=ua["id"], series_id=ids["series_id"], kind="above", threshold=10)
        db.add_all([hyp, an, aa, note, alert])
        db.commit()
        ids.update(alert_id=alert.id, run_id=run.id, sid=sess.id, cid=conn.id, hid=hyp.id, aid=an.id, analysis_id=aa.id, notification_id=note.id)
        ids["session_id"] = db.query(AuthSession).filter_by(user_id=ua["id"]).first().id
    return ids


FIXED = {"module_id": "history", "lesson_id": "x", "plan_id": "premium", "connector_id": "fred", "provider": "fred", "fmt": "pdf",
         "action": "pause", "item_type": "document"}
# Rotte che agiscono solo sui dati di chi chiama (o su cataloghi pubblici): un 2xx è lecito, purché non mostri dati altrui.
NEUTRAL = {"/api/modules/{module_id}", "/api/lessons/{lesson_id}", "/api/lessons/{lesson_id}/start", "/api/billing/checkout/{plan_id}",
           "/api/connectors/{connector_id}/check", "/api/credentials/{provider}", "/api/projects/linked/{item_type}/{item_id}"}


def _routes(app):
    out = []
    for path, ops in app.openapi()["paths"].items():
        if "{" in path:
            out += [(m.upper(), path) for m in ops]
    return out


def _url(path: str, ids: dict) -> str:
    def sub(m):
        name = m.group(1)
        if name in FIXED:
            return FIXED[name]
        if name == "aid" and "analyses" in path:
            return str(ids["analysis_id"])
        if name == "user_id":
            return str(ids["anna_id"])
        if name == "item_id" and "/projects/" in path:
            return str(ids["document_id"])
        return str(ids[name])
    return re.sub(r"{(\w+)}", sub, path)


# Corpi validi: senza, la validazione risponderebbe 422 prima del controllo dei permessi e il test non proverebbe nulla.
BODIES = {
    "/api/projects/{project_id}/members": {"email": "dario@example.org", "role": "editor"},
    "/api/projects/{project_id}/comments": {"body": "commento"},
    "/api/projects/{project_id}/items": {"item_type": "source", "item_id": 1},
    "/api/sources/{source_id}": {"title": "rubata"},
    "/api/sources/{source_id}/verify": {"method": "user"},
    "/api/history/events/{event_id}": {"title": "rubato", "start_year": 1900},
    "/api/history/events/{event_id}/sources": {"source_id": 1},
    "/api/history/events/{event_id}/knowledge": {"content": "x", "known_since_year": 1950},
    "/api/history/events/{event_id}/links": {"target_event_id": 1, "relation_type": "related_to", "provenance": "user_hypothesis"},
    "/api/graph/entities/{entity_id}": {"entity_type": "person", "name": "rubata"},
    "/api/research/runs/{run_id}/decision": {"decision": "reject", "note": "x"},
    "/api/lab/simulations/{sim_id}": {"title": "rubata"},
    "/api/reports/{report_id}/sections/{section_id}/quote": {"text": "testo citato", "document_id": 1},
    "/api/reports/{report_id}/chapters": {"title": "capitolo"},
    "/api/notes/{note_id}": {"title": "rubata"},
    "/api/discovery/connections/{cid}/status": {"status": "dismissed"},
    "/api/discovery/hypotheses/{hid}/decision": {"status": "rejected", "note": "x"},
    "/api/discovery/anomalies/{aid}": {"status": "dismissed", "note": "x"},
    "/api/discovery/hypotheses/{hid}": {"title": "Ipotesi rubata"},
    "/api/reports/{report_id}/sections/{section_id}": {"body": "testo rubato"},
    "/api/reports/{report_id}": {"title": "rubato"},
    "/api/projects/{project_id}": {"title": "rubato"},
    "/api/documents/{document_id}": {"title": "rubato"},
    "/api/finance/series/{series_id}": {"name": "rubata"},
}
QUERY = {"/api/projects/{project_id}/items": "item_type=document", "/api/finance/alerts/{alert_id}": "active=false",
         "/api/reports/{report_id}/status": "value=approved"}


def _call(client, method, url, path=""):
    q = "confirm=true" + (f"&{QUERY[path]}" if path in QUERY else "")
    url = f"{url}{'&' if '?' in url else '?'}{q}"
    if method in ("GET", "DELETE"):
        return client.request(method, url)
    return client.request(method, url, json=BODIES.get(path, {}))


def _snapshot(a, ids):
    gets = ["/api/projects", "/api/documents", "/api/documents/trash", "/api/sources", "/api/history/events", "/api/graph/entities",
            "/api/finance/series", "/api/finance/alerts", "/api/credentials", "/api/notes", "/api/lab/simulations", "/api/notifications",
            f"/api/reports/{ids['report_id']}", f"/api/reports/{ids['shared_report']}", f"/api/history/events/{ids['event_id']}",
            f"/api/reports/{ids['report_id']}/sections/{ids['section_id']}/versions", f"/api/projects/{ids['shared_project']}/members",
            f"/api/projects/{ids['shared_project']}/comments", f"/api/discovery/hypotheses/{ids['hid']}", f"/api/research/runs/{ids['run_id']}",
            f"/api/graph/entities/{ids['entity_id']}/relations", f"/api/finance/series/{ids['series_id']}"]
    out = {}
    for g in gets:
        r = a.get(g)
        assert r.status_code == 200, (g, r.text)
        out[g] = re.sub(r'"(last_seen_at|updated_at|read_at)":"[^"]*"', "", r.text)
    return out


def test_every_id_route_is_mapped(world):
    """Garanzia di copertura: ogni parametro di percorso dell'API ha un ID di prova (una rotta nuova non sfugge)."""
    for _, path in _routes(world["app"]):
        _url(path, {**world["ids"], **{k: 1 for k in ()}})


@pytest.mark.parametrize("who", ["d", "c", "b"])
def test_no_access_to_private_data_by_id(world, who):
    """Estraneo, viewer ed editor del progetto condiviso: nessun accesso ai dati PRIVATI di Anna, per nessuna rotta."""
    ids, client = world["ids"], world[who]
    before = _snapshot(world["a"], ids)
    violations = []
    for method, path in _routes(world["app"]):
        if path.startswith("/api/admin/") or "shared" in path:
            continue
        url = _url(path, ids)
        r = _call(client, method, url, path)
        if r.status_code == 422:
            violations.append(f"NON VERIFICATA (422 prima dei permessi) {method} {url}: {r.text[:160]}")
        if SECRET in r.text:
            violations.append(f"FUGA DI DATI {method} {url} → {r.status_code}")
        if 200 <= r.status_code < 300 and path not in NEUTRAL:
            violations.append(f"ACCESSO {method} {url} → {r.status_code} {r.text[:120]}")
    after = _snapshot(world["a"], ids)
    changed = [k for k in before if before[k] != after[k]]
    assert not violations, "\n".join(violations)
    assert not changed, f"Dati di Anna modificati da {who}: {changed}"


def test_admin_routes_need_admin_role(world):
    for who in ("a", "b", "c", "d"):
        for method, path in (("GET", "/api/admin/users"), ("GET", "/api/admin/stats"), ("POST", "/api/admin/storage/check"),
                             ("POST", "/api/admin/storage/cleanup?confirm=true"), ("PATCH", f"/api/admin/users/{world['ids']['anna_id']}")):
            r = world[who].request(method, path, json={"role": "admin"} if method == "PATCH" else None)
            assert r.status_code == 403, (who, path, r.status_code)


def test_id_manipulation_in_request_bodies(world):
    """Dario prova a collegare ai propri oggetti le risorse di Anna passando i loro ID nei corpi."""
    ids, d = world["ids"], world["d"]
    my_project = ok(d.post("/api/projects", json={"title": "Progetto di Dario"}))["id"]
    my_report = ok(d.post("/api/reports", json={"title": "Rapporto di Dario"}))
    my_event = ok(d.post("/api/history/events", json={"title": "Evento di Dario", "start_year": 1950}))["id"]
    my_entity = ok(d.post("/api/graph/entities", json={"entity_type": "person", "name": "Persona di Dario"}))["id"]
    sec = my_report["sections"][3]["id"]
    attempts = [
        ("POST", "/api/reports", {"title": "x", "project_id": ids["project_id"]}),
        ("POST", "/api/notes", {"title": "x", "project_id": ids["project_id"]}),
        ("POST", "/api/notes", {"title": "x", "source_id": ids["source_id"]}),
        ("POST", "/api/notes", {"title": "x", "document_id": ids["document_id"]}),
        ("PATCH", f"/api/reports/{my_report['id']}", {"source_ids": [ids["source_id"]]}),
        ("PATCH", f"/api/reports/{my_report['id']}", {"consulted_ids": [ids["source_id"]]}),
        ("PATCH", f"/api/reports/{my_report['id']}", {"project_id": ids["project_id"]}),
        ("POST", f"/api/reports/{my_report['id']}/sections/{sec}/quote", {"text": "testo copiato", "document_id": ids["document_id"]}),
        ("POST", f"/api/history/events/{my_event}/sources", {"source_id": ids["source_id"], "pages": "1"}),
        ("POST", f"/api/history/events/{my_event}/knowledge", {"content": "x", "known_since_year": 1950, "source_id": ids["source_id"]}),
        ("POST", "/api/graph/relations", {"source_entity_id": my_entity, "target_entity_id": ids["entity_id"], "relation_type": "influenced"}),
        ("POST", "/api/finance/alerts", {"series_id": ids["series_id"], "kind": "above", "threshold": 1}),
        ("POST", "/api/finance/compare", {"series_ids": [ids["series_id"], ids["series_id"]]}),
        ("POST", "/api/lab/simulations/monte_carlo_bootstrap", {"series_id": ids["series_id"], "years": 1}),
        ("POST", "/api/lab/simulations/scenarios", {"series_id": ids["series_id"], "scenarios": [{"name": "a", "growth": 0.01}]}),
        ("POST", "/api/lab/simulations/regression", {"y_series_id": ids["series_id"], "x_series_ids": [ids["series_id"]]}),
        ("POST", "/api/discovery/causal/transmission", {"series_ids": [ids["series_id"], ids["series_id"]]}),
        ("POST", "/api/discovery/causal/chains", {"start": my_entity, "end": ids["entity_id"]}),
        ("POST", "/api/discovery/causal/chains", {"start": ids["entity_id"], "end": my_entity}),
        ("POST", "/api/discovery/foresight", {"variables": [{"series_id": ids["series_id"]}]}),
        ("POST", f"/api/projects/{my_project}/items", {"item_type": "document", "item_id": ids["document_id"]}),
        ("POST", f"/api/projects/{my_project}/items", {"item_type": "source", "item_id": ids["source_id"]}),
        ("POST", f"/api/projects/{my_project}/items", {"item_type": "series", "item_id": ids["series_id"]}),
        ("POST", f"/api/projects/{ids['project_id']}/items", {"item_type": "document", "item_id": ids["document_id"]}),
        ("POST", "/api/documents", None),
    ]
    leaks = []
    for method, url, body in attempts:
        if body is None:
            r = d.post(url, files={"file": ("x.txt", b"ok")}, data={"project_id": str(ids["project_id"])})
        else:
            r = d.request(method, url, json=body)
        if r.status_code == 405 or '"message":"Not Found"' in r.text:  # rotta inesistente: il controllo non verificherebbe nulla
            leaks.append(f"ROTTA INESISTENTE {method} {url} → {r.status_code}")
        if r.status_code < 300 or SECRET in r.text:
            leaks.append(f"{method} {url} {body} → {r.status_code} {r.text[:150]}")
    # Un grafico con la serie di Anna nel proprio rapporto: accettato come dato, ma la verifica lo segnala e l'export non lo mostra.
    r = d.put(f"/api/reports/{my_report['id']}/sections/{sec}", json={"embeds": [{"type": "series", "series_id": ids["series_id"]}]})
    if r.status_code == 200:
        chk = d.get(f"/api/reports/{my_report['id']}/check").json()
        assert any(str(ids["series_id"]) in p for p in chk["embed_problems"])
        pdf = d.get(f"/api/reports/{my_report['id']}/export/docx")
        assert SECRET.encode() not in pdf.content
    assert not leaks, "\n".join(leaks)


def test_viewer_is_read_only_on_shared_project(world):
    ids, c = world["ids"], world["c"]
    p, rep, sec = ids["shared_project"], ids["shared_report"], ids["shared_section"]
    assert c.get(f"/api/projects/{p}").status_code == 200
    assert c.get(f"/api/reports/{rep}").status_code == 200 and SHARED in c.get(f"/api/reports/{rep}").text
    assert c.get(f"/api/reports/{rep}/trace").status_code == 200
    writes = [("PATCH", f"/api/projects/{p}", {"title": "x"}), ("PUT", f"/api/reports/{rep}/sections/{sec}", {"body": "x"}),
              ("PATCH", f"/api/reports/{rep}", {"title": "x"}), ("POST", f"/api/reports/{rep}/chapters", {"title": "x"}),
              ("POST", f"/api/reports/{rep}/status?value=approved", None), ("DELETE", f"/api/reports/{rep}?confirm=true", None),
              ("POST", f"/api/projects/{p}/items", {"item_type": "source", "item_id": ids["source_id"]}),
              ("POST", f"/api/projects/{p}/members?confirm=true", {"email": "dario@example.org", "role": "viewer"}),
              ("DELETE", f"/api/projects/{p}/comments/{ids['comment_id']}", None), ("DELETE", f"/api/projects/{p}?confirm=true", None),
              ("PUT", f"/api/notes/{ids['shared_note']}", {"title": "x"}), ("DELETE", f"/api/notes/{ids['shared_note']}?confirm=true", None)]
    for m, url, body in writes:
        r = c.request(m, url, json=body)
        assert r.status_code in (403, 404), (m, url, r.status_code, r.text)


def test_editor_can_edit_but_not_own(world):
    ids, b = world["ids"], world["b"]
    p, rep, sec = ids["shared_project"], ids["shared_report"], ids["shared_section"]
    assert ok(b.put(f"/api/reports/{rep}/sections/{sec}", json={"body": "Scritto da Bruno"}))
    for m, url, body in [("DELETE", f"/api/reports/{rep}?confirm=true", None), ("DELETE", f"/api/projects/{p}?confirm=true", None),
                         ("POST", f"/api/projects/{p}/members?confirm=true", {"email": "dario@example.org", "role": "editor"}),
                         ("DELETE", f"/api/projects/{p}/members/{world['users']['c']['id']}", None),
                         ("DELETE", f"/api/projects/{p}/comments/{ids['comment_id']}", None),
                         ("PUT", f"/api/notes/{ids['shared_note']}", {"title": "x"})]:
        r = b.request(m, url, json=body)
        assert r.status_code in (403, 404), (m, url, r.status_code, r.text)
    # I documenti privati di Anna restano privati anche per i membri del progetto.
    assert b.get(f"/api/documents/{ids['document_id']}").status_code == 404
    assert SECRET not in b.get(f"/api/documents?project_id={p}").text


def test_outsider_lists_never_contain_others_data(world):
    d = world["d"]
    for url in ["/api/projects", "/api/documents", "/api/sources?origin=mine", "/api/history/events?origin=mine", "/api/graph/entities",
                "/api/finance/series", "/api/finance/alerts", "/api/credentials", "/api/reports", "/api/notes", "/api/lab/simulations",
                "/api/notifications", "/api/research/runs", "/api/discovery/hypotheses", "/api/discovery/connections", "/api/discovery/anomalies",
                "/api/discovery/sessions", "/api/discovery/analyses", "/api/briefings", "/api/activity", "/api/search?q=SEGRETO",
                "/api/research/search?q=lira", "/api/documents/trash", "/api/auth/sessions", "/api/dashboard"]:
        r = d.get(url)
        assert SECRET not in r.text and "chiave-di-anna" not in r.text, url


# --- Intestazioni di sicurezza, XSS, revoca delle sessioni ----------------------------------------------------


def test_security_headers_on_api(client):
    r = client.get("/api/health")
    h = r.headers
    assert h["content-security-policy"].startswith("default-src 'none'") and "frame-ancestors 'none'" in h["content-security-policy"]
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY" and h["referrer-policy"] == "no-referrer"
    assert "camera=()" in h["permissions-policy"] and h["cross-origin-opener-policy"] == "same-origin"
    assert "strict-transport-security" not in h  # HTTP locale: niente HSTS
    https = client.get("/api/health", headers={"X-Forwarded-Proto": "https"})
    assert https.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    assert "cdn.jsdelivr.net" in client.get("/docs").headers["content-security-policy"]
    # anche gli errori (404, 403 CSRF) portano le intestazioni
    assert "content-security-policy" in client.get("/api/non-esiste").headers


def test_uploaded_html_cannot_run_scripts(client):
    """Un file con HTML/JS caricato come documento viene servito come allegato, sandboxato, mai interpretato dal browser."""
    payload = b"<html><script>alert(document.cookie)</script><img src=x onerror=alert(1)></html>"
    r = client.post("/api/documents", files={"file": ("x.txt", payload)})
    if r.status_code == 201:
        f = client.get(f"/api/documents/{r.json()['id']}/file")
        assert "sandbox" in f.headers["content-security-policy"] and f.headers["x-content-type-options"] == "nosniff"
        assert not f.headers["content-type"].startswith("text/html")


def test_xss_payloads_are_stored_as_text_and_dangerous_urls_rejected(client):
    xss = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
    s = client.post("/api/sources", json={"title": xss, "authors": [xss]}).json()
    assert s["title"] == xss  # salvato com'è: l'interfaccia lo mostra come testo (React fa l'escape)
    for bad in ("javascript:alert(1)", "data:text/html,<script>alert(1)</script>", "vbscript:msgbox(1)", "JaVaScRiPt:alert(1)"):
        assert client.post("/api/sources", json={"title": "x", "url": bad}).status_code == 422, bad


def test_logout_revokes_token_and_cookie(world):
    app = world["app"]
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"email": "dario@example.org", "password": PWD})
    assert r.status_code == 200
    token = c.cookies.get("nexus_session")
    bearer = TestClient(app)
    assert bearer.get("/api/projects", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert c.post("/api/auth/logout", headers=H).status_code == 204
    assert bearer.get("/api/projects", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    c.cookies.set("nexus_session", token, path="/api")
    assert c.get("/api/projects").status_code == 401


def test_revoked_session_and_deactivated_account(world):
    app = world["app"]
    c1, c2 = TestClient(app), TestClient(app)
    for c in (c1, c2):
        assert c.post("/api/auth/login", json={"email": "carla@example.org", "password": PWD}).status_code == 200
        c.headers.update(H)
    sessions = c1.get("/api/auth/sessions").json()
    other = next(s for s in sessions if not s.get("current"))
    assert c1.delete(f"/api/auth/sessions/{other['id']}").status_code == 204
    assert c2.get("/api/projects").status_code == 401 and c1.get("/api/projects").status_code == 200
    # una sessione altrui non si può revocare
    anna_session = world["ids"]["session_id"]
    assert c1.delete(f"/api/auth/sessions/{anna_session}").status_code == 404
    assert world["a"].get("/api/projects").status_code == 200


def test_series_source_url_must_be_http(client):
    r = client.post("/api/finance/series/upload", files={"file": ("s.csv", b"anno,valore\n2001,1\n2002,2\n")},
                    data={"name": "x", "source_label": "y", "source_url": "javascript:alert(1)"})
    assert r.status_code == 422
