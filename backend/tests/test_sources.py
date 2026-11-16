import httpx

from nexus.research import citations


def test_create_source_and_citation(client):
    r = client.post("/api/sources", json={
        "source_type": "book", "title": "Titolo di prova", "authors": ["Anna Bianchi"], "year": 2001,
        "publisher": "Editore", "isbn": "978-88-04-12345-7" if False else "",
    })
    assert r.status_code == 201
    s = r.json()
    assert s["verification_status"] == "unverified"
    assert s["citation"].startswith("Anna Bianchi. (2001). Titolo di prova")


def test_invalid_identifiers_rejected(client):
    for payload in ({"doi": "abc"}, {"isbn": "1234567890"}, {"url": "ftp://x"}, {"year": 3000}, {"accessed_at": "ieri"}):
        r = client.post("/api/sources", json={"title": "x", **payload})
        assert r.status_code == 422, payload


def test_isbn_and_doi_validation():
    assert citations.valid_isbn("0-306-40615-2") and citations.valid_isbn("978-0-306-40615-7")
    assert not citations.valid_isbn("978-0-306-40615-8")
    assert citations.valid_doi("https://doi.org/10.1000/xyz123")
    assert citations.normalize_doi("doi:10.1000/ABC") == "10.1000/ABC"


def test_user_verification_and_reset_on_edit(client):
    s = client.post("/api/sources", json={"title": "Fonte"}).json()
    v = client.post(f"/api/sources/{s['id']}/verify", json={"method": "user", "note": "Controllata in biblioteca"}).json()
    assert v["verification_status"] == "verified_user" and v["verified_at"]
    e = client.put(f"/api/sources/{s['id']}", json={"title": "Fonte modificata"}).json()
    assert e["verification_status"] == "unverified"


def test_registry_verification_requires_doi(client):
    s = client.post("/api/sources", json={"title": "Senza DOI"}).json()
    assert client.post(f"/api/sources/{s['id']}/verify", json={"method": "registry"}).status_code == 422


def test_crossref_lookup_parsing():
    payload = {"message": {"DOI": "10.1000/x", "title": ["A Paper"], "author": [{"given": "Ada", "family": "Lovelace"}],
                           "issued": {"date-parts": [[1843]]}, "container-title": ["Journal"], "publisher": "P", "page": "1-10",
                           "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}], "URL": "https://doi.org/10.1000/x"}}
    ok = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))
    res = citations.crossref_lookup("10.1000/x", client=ok)
    # «found» = il DOI esiste; non dice ancora nulla sulla corrispondenza della scheda.
    assert res.status == "found" and res.metadata["authors"] == ["Ada Lovelace"] and res.metadata["year"] == 1843
    assert res.metadata["families"] == ["Lovelace"] and res.metadata["licenses"][0].startswith("https://creativecommons")
    nf = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    assert citations.crossref_lookup("10.1000/x", client=nf).status == "not_found"


META = {"doi": "10.1000/abc", "title": "The Great Divergence", "subtitle": "China, Europe, and the Making of the Modern World Economy",
        "authors": ["Kenneth Pomeranz"], "families": ["Pomeranz"], "year": 2000, "years": [2000, 2021],
        "container": "", "registry": "Crossref", "registry_url": "https://api.crossref.org/works/10.1000/abc",
        "url": "https://doi.org/10.1000/abc", "licenses": []}


def _crossref(monkeypatch, meta):
    from nexus.services import sources as svc

    monkeypatch.setattr(svc, "crossref_lookup", lambda doi: citations.RegistryResult("found", "Il DOI esiste in Crossref.", dict(meta)))


def _verify(client, **fields):
    s = client.post("/api/sources", json={"doi": "10.1000/abc", **fields}).json()
    return client.post(f"/api/sources/{s['id']}/verify", json={"method": "registry"}).json()


def test_registry_match_on_all_fields(client, monkeypatch):
    _crossref(monkeypatch, META)
    v = _verify(client, title="The great divergence: China, Europe and the making of the modern world economy",
                authors=["Pomeranz, Kenneth"], year=2000)
    assert v["verification_status"] == "verified_registry", v["verification_note"]
    f = v["verification_details"]["fields"]
    assert {k: x["status"] for k, x in f.items()} == {"doi": "match", "title": "match", "authors": "match", "year": "match"}
    d = v["verification_details"]
    assert d["doi_exists"] and d["registry_url"].startswith("https://api.crossref.org") and d["checked_at"]
    assert v["url"] == "https://doi.org/10.1000/abc"  # URL conservato dal registro
    assert v["provenance"] == "Inserita manualmente dall'utente" and v["verification_details"]["registry"] == "Crossref"


def test_registry_mismatch_is_never_verified(client, monkeypatch):
    _crossref(monkeypatch, META)
    v = _verify(client, title="Titolo sbagliato", authors=["Kenneth Pomeranz"], year=2011)
    assert v["verification_status"] == "registry_mismatch"
    assert "titolo" in v["verification_note"] and "anno" in v["verification_note"]
    assert v["verification_details"]["fields"]["year"] == {"status": "mismatch", "local": 2011, "registry": 2000, "label": "anno"}
    # Né il registro né l'utente possono marcarla verificata finché la scheda non viene corretta.
    assert client.post(f"/api/sources/{v['id']}/verify", json={"method": "user"}).status_code == 422
    fixed = client.put(f"/api/sources/{v['id']}", json={"title": "The Great Divergence", "authors": ["Kenneth Pomeranz"],
                                                       "year": 2000, "doi": "10.1000/abc"}).json()
    assert fixed["verification_status"] == "unverified" and fixed["verification_details"] is None
    again = client.post(f"/api/sources/{v['id']}/verify", json={"method": "registry"}).json()
    assert again["verification_status"] == "verified_registry"


def test_registry_wrong_author_flagged(client, monkeypatch):
    _crossref(monkeypatch, META)
    v = _verify(client, title="The Great Divergence", authors=["Joel Mokyr"], year=2000)
    assert v["verification_status"] == "registry_mismatch"
    assert v["verification_details"]["fields"]["authors"]["status"] == "mismatch"


def test_registry_incomplete_when_essential_fields_missing(client, monkeypatch):
    _crossref(monkeypatch, {**META, "container": "Journal of Economic History"})
    v = _verify(client, title="The Great Divergence")
    assert v["verification_status"] == "registry_incomplete"
    f = v["verification_details"]["fields"]
    assert f["authors"]["status"] == "missing_local" and f["year"]["status"] == "missing_local"
    assert f["container"]["status"] == "missing_local"
    assert "autori" in v["verification_note"] and "anno" in v["verification_note"]


def test_registry_journal_mismatch(client, monkeypatch):
    _crossref(monkeypatch, {**META, "container": "Journal of Economic History", "short_container": "J. Econ. Hist."})
    ok = _verify(client, title="The Great Divergence", authors=["K. Pomeranz"], year=2000, container="Journal of Economic History")
    assert ok["verification_status"] == "verified_registry"
    bad = _verify(client, title="The Great Divergence", authors=["K. Pomeranz"], year=2000, container="Past & Present")
    assert bad["verification_status"] == "registry_mismatch" and "rivista" in bad["verification_note"]


def test_registry_not_found_records_details(client, monkeypatch):
    from nexus.services import sources as svc

    monkeypatch.setattr(svc, "crossref_lookup", lambda doi: citations.RegistryResult("not_found", "Crossref non conosce questo DOI.", {"registry_url": "u"}))
    v = _verify(client, title="x")
    assert v["verification_status"] == "not_found" and v["verification_details"]["doi_exists"] is False


def test_source_license_provenance_and_class(client):
    s = client.post("/api/sources", json={"title": "Censimento 1861", "source_type": "archive", "evidence_class": "primary",
                                          "license": "Pubblico dominio", "url": "https://example.org/c", "accessed_at": "2026-11-01"}).json()
    assert s["evidence_class"] == "primary" and s["license"] == "Pubblico dominio" and s["accessed_at"] == "2026-11-01"
    assert s["provenance"] == "Inserita manualmente dall'utente"
    assert client.post("/api/sources", json={"title": "x", "evidence_class": "terziaria"}).status_code == 422


def test_document_linked_to_source_cites_it(client):
    from .factories import upload

    s = client.post("/api/sources", json={"title": "Storia monetaria", "authors": ["Luca Verdi"], "year": 1990}).json()
    d = upload(client, "m.txt", b"La lira fu introdotta nel 1861 come moneta nazionale.").json()
    client.patch(f"/api/documents/{d['id']}", json={"source_id": s["id"]})
    hit = client.get("/api/research/search?q=lira moneta").json()["hits"][0]
    assert hit["source_label"].startswith("Luca Verdi. (1990)")


def test_delete_source_requires_confirmation(client):
    s = client.post("/api/sources", json={"title": "x"}).json()
    assert client.delete(f"/api/sources/{s['id']}").status_code == 409
    assert client.delete(f"/api/sources/{s['id']}?confirm=true").status_code == 204
