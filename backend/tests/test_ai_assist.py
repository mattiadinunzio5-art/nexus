"""AI condivisa dalla piattaforma e aiuti AI (revisione, traduzione, proposte dai documenti)."""

import json

import pytest

from nexus.agents import llm


class EchoLLM(llm.LLMClient):
    provider, model = "fake", "fake-1"

    def __init__(self, body: dict):
        self.body, self.calls = body, 0

    def complete(self, system, user, max_tokens=4000):
        self.calls += 1
        return llm.LLMResult(text=json.dumps(self.body), provider=self.provider, model=self.model)


def test_platform_ai_shared_with_daily_limit(client, monkeypatch):
    from nexus.api.schemas_finance import CredentialIn
    from nexus.models import User
    from nexus.services import ai, credentials

    settings = client.app.state.settings
    db = client.app.state.database.session_factory()
    try:
        admin = User(email="admin@example.org", display_name="Admin", role="admin")
        student = User(email="student@example.org", display_name="Studente")
        db.add_all([admin, student])
        db.commit()
        assert ai.client_for(db, student, settings) is None  # nessuna AI condivisa: modalità locale
        with pytest.raises(Exception):
            ai.set_platform(db, admin, settings, True, "anthropic", 2)  # senza credenziali non si attiva
        credentials.set_credential(db, admin, settings, CredentialIn(provider="anthropic", secret="sk-test"))
        ai.set_platform(db, admin, settings, True, "anthropic", 2)
        st = ai.status(db, student, settings)
        assert st["shared"] and st["provider"] == "anthropic" and st["daily_limit"] == 2

        inner = EchoLLM({"ok": True})
        monkeypatch.setattr(llm, "AnthropicClient", lambda *a, **k: inner)
        c = ai.client_for(db, student, settings)
        assert isinstance(c, ai.LimitedClient)
        c.complete("s", "u")
        c.complete("s", "u")
        with pytest.raises(llm.ProviderError, match="Limite giornaliero"):
            c.complete("s", "u")
        assert inner.calls == 2 and ai.usage_today(db, student) == 2

        ai.select_provider(db, student, settings, "none")  # scelta esplicita della modalità locale
        assert ai.client_for(db, student, settings) is None
    finally:
        db.close()


def _report_with_text(client, body):
    r = client.post("/api/reports", json={"title": "Tesi"}).json()
    sec = next(s for s in r["sections"] if s["key"] == "analysis")
    client.put(f"/api/reports/{r['id']}/sections/{sec['id']}", json={"body": body, "embeds": []})
    return r["id"], sec["id"]


BODY = ("La produzione mondiale di plastica è passata da 2 milioni di tonnellate nel 1950 a oltre 400 nel 2022. "
        "Questo dimostra che il riciclo ha sempre fallito. Il riciclo resta limitato secondo l'OCSE [@1].")


def test_section_review_local_without_ai(client):
    rid, sid = _report_with_text(client, BODY)
    r = client.post(f"/api/reports/{rid}/sections/{sid}/review").json()
    assert r["mode"] == "local"
    kinds = {i["kind"] for i in r["issues"]}
    assert {"uncited", "overclaim"} <= kinds
    assert all("[@1]" not in i["quote"] for i in r["issues"])


def test_section_review_ai_drops_invented_quotes(client, monkeypatch):
    from nexus.services import ai

    fake = EchoLLM({"issues": [
        {"kind": "overclaim", "quote": "Questo dimostra che il riciclo ha sempre fallito.", "comment": "Generalizzazione."},
        {"kind": "uncited", "quote": "Frase che non esiste nel testo.", "comment": "x"},
    ]})
    monkeypatch.setattr(ai, "client_for", lambda *a, **k: fake)
    rid, sid = _report_with_text(client, BODY)
    r = client.post(f"/api/reports/{rid}/sections/{sid}/review").json()
    assert r["mode"] == "ai"
    quotes = [i["quote"] for i in r["issues"]]
    assert "Questo dimostra che il riciclo ha sempre fallito." in quotes
    assert "Frase che non esiste nel testo." not in quotes and "scartate" in r["note"]


def test_document_extraction_keeps_only_anchored_proposals(client, monkeypatch):
    from nexus.services import ai

    text = b"In 1973 the OPEC oil embargo quadrupled oil prices. The Organization of the Petroleum Exporting Countries led the embargo.\n"
    doc = client.post("/api/documents", files={"file": ("opec.txt", text * 2)}, data={"title": "OPEC", "category": "source_material"}).json()
    assert client.post(f"/api/documents/{doc['id']}/extract").status_code == 422  # senza AI: dichiarato
    fake = EchoLLM({
        "events": [{"title": "Embargo petrolifero OPEC", "start_year": 1973, "countries": [], "description": "Embargo.", "evidence": "P1",
                    "quote": "In 1973 the OPEC oil embargo quadrupled oil prices."},
                   {"title": "Inventato", "start_year": 1980, "evidence": "P1", "quote": "Something not in the text at all."}],
        "entities": [{"name": "OPEC", "entity_type": "organization", "evidence": "P1", "quote": "The Organization of the Petroleum Exporting Countries led the embargo."}],
        "relations": [{"source": "OPEC", "target": "Embargo petrolifero OPEC", "relation_type": "caused", "evidence": "P9", "quote": "x x x x x x x x"}],
    })
    monkeypatch.setattr(ai, "client_for", lambda *a, **k: fake)
    r = client.post(f"/api/documents/{doc['id']}/extract").json()
    assert [e["title"] for e in r["events"]] == ["Embargo petrolifero OPEC"]
    assert r["entities"][0]["name"] == "OPEC" and r["relations"] == []
    assert "scartate" in r["note"]


def test_ask_with_ai_adds_translation(client, monkeypatch):
    from nexus.services import ai

    client.post("/api/documents", files={"file": ("w.txt", b"Plastic waste reached the oceans after 1980.\n" * 3)}, data={"title": "W", "category": "source_material"})

    class Fake(llm.LLMClient):
        provider, model = "fake", "f"

        def complete(self, system, user, max_tokens=4000):
            if "Traduci" in user:
                return llm.LLMResult(text='{"translations": ["ocean plastic waste"]}', provider="fake", model="f")
            return llm.LLMResult(text='{"claims": [], "notes": ""}', provider="fake", model="f")

    monkeypatch.setattr(ai, "client_for", lambda *a, **k: Fake())
    r = client.post("/api/research/ask", json={"question": "spazzatura negli oceani", "use_ai": True}).json()
    assert any("ocean plastic waste" in i for i in r["issues"])
    assert r["passages"] and "Plastic waste" in r["passages"][0]["text"]
