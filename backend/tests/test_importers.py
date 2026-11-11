"""Importatori della Biblioteca NEXUS con risposte di rete SIMULATE (piccole fixture), mai dati presentati come reali."""

import json

import httpx
import pytest
from sqlalchemy import select

from nexus.core import library
from nexus.finance import connectors
from nexus.importers import biblio, common, docs, series, wikidata
from nexus.models import Document, Entity, HistoricalEvent, Relation, Series, Source


@pytest.fixture
def run(client, settings, tmp_path):
    library.reset_cache()
    r = common.Run(client.app.state.database, settings, area="test", pause=0, out_dir=tmp_path / "imports")
    yield r
    r.close()
    library.reset_cache()


def test_parse_time_handles_bce_precision_and_calendar():
    assert wikidata.parse_time("-0479-08-07T00:00:00Z", "11") == (-480, None, None, 11)  # 480 a.C., solo anno prima del 1583
    assert wikidata.parse_time("1929-10-24T00:00:00Z", "11") == (1929, 10, 24, 11)
    assert wikidata.parse_time("1929-10-01T00:00:00Z", "10") == (1929, 10, None, 10)
    assert wikidata.parse_time("-3000-01-01T00:00:00Z", "7")[0] == -3000  # secolo: anno «tondo»
    assert wikidata.parse_time("http://www.wikidata.org/.well-known/genid/x", "9")[0] is None


def test_balance_spreads_across_centuries():
    cands = [{"_year": 1900 + i, "sl": 100 - i, "item": f"Q{i}"} for i in range(10)] + [{"_year": -480, "sl": 1, "item": "Q99"}]
    picked = wikidata.balance(cands, 2)
    assert {c["_year"] // 100 for c in picked} == {-5, 19}


class FakeWikimedia:
    """Risposte simulate dell'endpoint SPARQL e delle API di Wikipedia."""

    def __init__(self):
        self.calls = []

    def sparql(self, query):
        self.calls.append(query)
        if "rdfs:label ?l" in query and "VALUES ?q" in query:
            out = [{"q": f"http://www.wikidata.org/entity/{q}", "l": spec[0]} for q, spec in
                   {**wikidata.EVENT_CLASSES, **wikidata.FOUNDING_CLASSES, **wikidata.ENTITY_CLASSES}.items()]
            return out
        if "wd:Q114380 ; wikibase:sitelinks" in query:  # financial crisis
            return [{"item": "http://www.wikidata.org/entity/Q1", "label": "test crisis", "sl": "5", "t": "1907-10-01T00:00:00Z",
                     "tp": "10", "article": "https://en.wikipedia.org/wiki/Test_crisis"}]
        if "wdt:P17 wdt:P276 wdt:P828 wdt:P1542" in query:
            return [{"item": "http://www.wikidata.org/entity/Q1", "p": "http://www.wikidata.org/prop/direct/P828", "oLabel": "cause A"}]
        if "prov:wasDerivedFrom" in query:
            return [{"item": "http://www.wikidata.org/entity/Q1", "n": "3"}]
        if "wdt:P106 wd:Q188094" in query:  # economists
            return [{"item": "http://www.wikidata.org/entity/Q2", "label": "Economist A", "desc": "economist", "sl": "9",
                     "b": "1850-01-01T00:00:00Z", "d": "1920-01-01T00:00:00Z"}]
        if "VALUES ?s" in query:
            return [{"s": "http://www.wikidata.org/entity/Q2", "p": "http://www.wikidata.org/prop/direct/P793", "o": "http://www.wikidata.org/entity/Q1"}]
        return []

    def extracts(self, titles):
        return {"Test crisis": "A test crisis () happened. It is a fixture."}


def test_events_and_graph_from_simulated_wikidata(run):
    wm = FakeWikimedia()
    wikidata.run_events(run, wm)
    e = run.db.scalar(select(HistoricalEvent).where(HistoricalEvent.external_id == "Q1"))
    assert e.title == "Test crisis" and e.start_year == 1907 and e.start_month == 10 and e.start_day is None
    assert e.reliability == "probable" and "P828" in e.causes and e.description == "A test crisis happened. It is a fixture."
    assert e.owner_id == run.lib.id and e.origin == "wikidata"
    src = run.db.scalar(select(Source).where(Source.external_id == "Q1"))
    assert "CC0" in src.notes and "CC BY-SA" in src.notes and src.url.endswith("/Q1")
    # Idempotenza: una seconda esecuzione non duplica.
    wikidata.run_events(run, wm)
    assert run.db.scalar(select(HistoricalEvent.id).where(HistoricalEvent.external_id == "Q1")) == e.id
    assert len(list(run.db.scalars(select(HistoricalEvent).where(HistoricalEvent.origin == "wikidata")))) == 1

    wikidata.run_graph(run, wm)
    person = run.db.scalar(select(Entity).where(Entity.external_id == "Q2"))
    assert person.entity_type == "person" and person.start_year == 1850
    rel = run.db.scalar(select(Relation).where(Relation.origin == "wikidata"))
    assert rel.provenance == "sourced" and rel.relation_type == "involved_in" and "P793" in rel.evidence_note and rel.source_id
    # Cancellazione per lotto: tocca solo la Biblioteca.
    out = common.delete_origin(run.database, "wikidata")
    assert out["historical_events"] == 1 and out["relations"] == 1


def test_series_import_goes_through_service_and_is_idempotent(run, monkeypatch):
    calls = []

    def fake_wb(f, indicator, country, force=False):
        calls.append((indicator, country))
        if country == "EMPTY":
            raise connectors.ConnectorError("Nessun dato World Bank per EMPTY")
        return connectors.FetchResult(name=f"{indicator} — {country}", unit="%", frequency="A", source_label="World Bank (fixture)",
                                      source_url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}", license_note="fixture", source_last_updated="",
                                      observations=[("2000-01-01", 1.0), ("2001-01-01", None), ("2002-01-01", 3.0)], description="",
                                      country=country)

    monkeypatch.setattr(connectors, "fetch_world_bank", fake_wb)
    from nexus.api.schemas_finance import SeriesImportIn

    for c in ("ITA", "EMPTY", "ITA"):
        series._import(run, "world-bank", f"X:{c}", SeriesImportIn(connector="world-bank", indicator="X", country=c, category="gdp"))
    s = run.db.scalar(select(Series).where(Series.origin == "world-bank"))
    assert s.external_id == "X:ITA" and s.missing_count == 1  # il buco resta un buco
    assert run.report.counts["series"] == {"created": 1, "skipped": 1, "errors": 0}  # il terzo è già «fatto»
    assert calls.count(("X", "ITA")) == 1


def test_biblio_and_docs_with_mocked_http(run, monkeypatch):
    def handler(req: httpx.Request):
        if req.url.host == "api.crossref.org" and req.url.path == "/works":
            return httpx.Response(200, json={"message": {"items": [
                {"DOI": "10.1000/xyz", "title": ["A history of banking (fixture)"], "author": [{"given": "A", "family": "B"}],
                 "issued": {"date-parts": [[1990]]}, "type": "book", "publisher": "P"},
                {"DOI": "10.1000/abc", "title": ["Autopoiesis"], "type": "book"}]}})
        if req.url.host == "openlibrary.org":
            return httpx.Response(200, json={"docs": [{"key": "/works/OL1W", "title": "Economic history (fixture)", "author_name": ["C"],
                                                       "first_publish_year": 1950, "isbn": ["9780306406157", "123"]}]})
        if req.url.host == "gutenberg.pglaf.org":
            return httpx.Response(200, content=b"Title: An Inquiry into the Nature and Causes of the Wealth of Nations\n\nBOOK I\n" + b"Labour and wages. " * 400)
        return httpx.Response(404)

    monkeypatch.setattr(biblio, "_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(biblio.sources, "verify_source", lambda *a, **k: None)
    monkeypatch.setattr(biblio, "TOPICS", ["banking"])
    monkeypatch.setattr(biblio, "OPEN_LIBRARY_SUBJECTS", ["economic history"])
    run.limit = 4
    biblio.run_biblio(run)
    titles = set(run.db.scalars(select(Source.title).where(Source.owner_id == run.lib.id)))
    assert titles == {"A history of banking (fixture)", "Economic history (fixture)"}  # «Autopoiesis» scartato: fuori tema
    ol = run.db.scalar(select(Source).where(Source.origin == "openlibrary"))
    assert ol.isbn == "9780306406157"

    monkeypatch.setattr(docs, "CLASSICS", docs.CLASSICS[:2])
    run.limit = None
    docs.run_docs(run, httpx.Client(transport=httpx.MockTransport(handler)))
    titles = list(run.db.scalars(select(Document.title).where(Document.owner_id == run.lib.id)))
    assert titles == ["An Inquiry into the Nature and Causes of the Wealth of Nations"]  # Ricardo: titolo non corrispondente, saltato
    _ = json
