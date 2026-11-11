"""NEXUS Copyright & Data Policy: registro delle licenze, collegamento agli elementi, blocco in Biblioteca."""

import pytest

from nexus.core import library, licenses
from nexus.core.errors import NexusError
from nexus.services import documents, finance

FIELDS = {"name", "homepage", "license", "license_url", "attribution", "commercial", "redistribution", "territorial",
          "modifications", "verified_on", "terms_url", "status"}


def test_every_entry_has_all_policy_fields():
    for e in licenses.registry():
        assert FIELDS <= e.keys()
        assert all(e[k] for k in FIELDS), e["id"]
        assert e["commercial"] in ("yes", "conditional", "no") and e["redistribution"] in ("yes", "conditional", "no")
        assert e["terms_url"].startswith("https://") and e["license_url"].startswith("https://")
    assert set(licenses.LIBRARY_LICENSES) <= set(licenses.LICENSES)


@pytest.mark.parametrize("url, sid, expected", [
    ("https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=ITA", "FP.CPI.TOTL.ZG:ITA", "world_bank_wdi"),
    ("https://ourworldindata.org/grapher/gdp-per-capita-maddison-project-database", "x", "maddison"),
    ("https://ourworldindata.org/grapher/population", "x", "owid"),
    ("https://ec.europa.eu/eurostat/databrowser/view/une_rt_a/default/table", "x", "eurostat"),
    ("https://data.ecb.europa.eu/data/datasets/EXR/EXR.M.USD.EUR.SP00.A", "x", "ecb"),
    ("https://fred.stlouisfed.org/series/M1109BUSM293NNBR", "M1109BUSM293NNBR", "fred_nber"),
    ("https://fred.stlouisfed.org/series/INDPRO", "INDPRO", "fred"),
    ("https://example.org/my.csv", "", None),
    ("", "", None),
])
def test_series_are_matched_to_their_license(url, sid, expected):
    assert licenses.for_series(url, sid) == expected


def test_sources_and_documents_are_matched():
    assert licenses.for_source("https://www.wikidata.org/wiki/Q1") == "wikidata"
    assert licenses.for_source("https://doi.org/10.1/x") is None
    assert licenses.for_document("gutenberg", "https://www.gutenberg.org/ebooks/3300") == "gutenberg"
    assert licenses.for_document("upload", "") is None


def test_public_registry_endpoint_with_library_counts(client):
    library.reset_cache()
    r = client.get("/api/licenses")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] and {e["id"] for e in body["licenses"]} == set(licenses.LICENSES)
    it = next(e for e in body["licenses"] if e["id"] == "wikidata")
    en = next(e for e in client.get("/api/licenses", headers={"X-Nexus-Lang": "en"}).json()["licenses"] if e["id"] == "wikidata")
    assert it["attribution"] != en["attribution"] and en["attribution"].startswith("Not required")
    library.reset_cache()


def test_series_and_documents_expose_license_id(client):
    csv = "date,value\n2020-01-01,1\n2021-01-01,2\n"
    s = client.post("/api/finance/series/upload", data={"name": "Mia", "source_label": "Mio archivio", "category": "other", "unit": "x"},
                    files={"file": ("a.csv", csv, "text/csv")})
    assert s.status_code in (200, 201), s.text
    assert s.json()["license_id"] is None


def test_library_rejects_items_without_registered_license(client, settings):
    library.reset_cache()
    with client.app.state.database.session_factory() as db:
        lib = library.ensure_library_user(db)
        with pytest.raises(NexusError, match="licenza registrata"):
            finance.import_csv(db, lib, name="X", source_label="Ignota", source_url="https://example.org/x.csv",
                               category="other", unit="x", text="date,value\n2020-01-01,1\n", date_col=None, value_col=None)
        with pytest.raises(NexusError, match="licenza registrata"):
            documents.import_bytes(db, lib, settings, filename="x.txt", data=b"testo qualunque", origin="upload")
    library.reset_cache()


def test_event_sources_carry_wikidata_and_wikipedia_licenses(client):
    from nexus.models import EventSource, Source

    library.reset_cache()
    e = client.post("/api/history/events", json={"title": "Panic of 1907", "start_year": 1907}).json()
    with client.app.state.database.session_factory() as db:
        src = Source(owner_id=e["owner_id"] if "owner_id" in e else 1, title="Wikidata Q1", source_type="web",
                     url="https://www.wikidata.org/wiki/Q1", notes="Dati strutturati: CC0. Descrizione: estratto da Wikipedia.")
        db.add(src)
        db.flush()
        db.add(EventSource(event_id=e["id"], source_id=src.id))
        db.commit()
    out = client.get(f"/api/history/events/{e['id']}").json()
    assert out["sources"][0]["license_ids"] == ["wikidata", "wikipedia"]
    library.reset_cache()


def test_website_policy_page_is_in_sync_with_registry():
    """La pagina pubblica del sito è generata dal registro: se cambia una licenza va rigenerata (scripts/export_licenses.py)."""
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "export_licenses.py"
    spec = importlib.util.spec_from_file_location("export_licenses", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.OUT.read_text(encoding="utf-8") == mod.render()
