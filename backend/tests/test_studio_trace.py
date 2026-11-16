"""Research Studio: tracciabilità affermazioni ↔ fonti, uso della bibliografia, coerenza e versioni."""

from nexus.studio import trace

from .test_studio import _report


def _src(client, **kw):
    r = client.post("/api/sources", json={"title": "Fonte", "authors": ["A. Rossi"], "year": 1950, **kw})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _section(rep, key):
    return next(s for s in rep["sections"] if s["key"] == key)


def _put(client, rep, key, **data):
    r = client.put(f"/api/reports/{rep['id']}/sections/{_section(rep, key)['id']}", json=data)
    assert r.status_code == 200, r.text
    return r.json()


def test_sentence_split_keeps_citations_with_dots():
    s = trace.sentences("Furono 1.204 milioni [@3, p. 12]. Poi crebbe del 40% nel 1952. [@4]")
    assert s == ["Furono 1.204 milioni [@3, p. 12].", "Poi crebbe del 40% nel 1952. [@4]"]


def test_claims_linked_to_sources_and_pages(client):
    p = _src(client, evidence_class="primary", source_type="archive")
    q = _src(client, evidence_class="secondary")
    rep = _report(client)
    rep = _put(client, rep, "analysis", body=(
        f"L'Italia ricevette 1.204 milioni di dollari dal Piano Marshall [@{p}, p. 12]. "
        "La produzione industriale crebbe del 40% tra il 1948 e il 1952 a causa degli aiuti.\n\n"
        f"Gli aiuti furono decisivi per la ripresa del 1950 in tutta l'Europa occidentale. Lo conferma lo studio di sintesi [@{q}].\n\n"
        "Il 1953 vide un'ulteriore espansione delle esportazioni [@999]."))
    t = client.get(f"/api/reports/{rep['id']}/trace").json()
    claims = next(x for x in t["sections"] if x["key"] == "analysis")["claims"]
    by_status = {c["status"] for c in claims}
    assert by_status == {"supported", "unsupported", "paragraph", "invalid_citation"}
    first = claims[0]
    assert first["status"] == "supported" and first["citations"][0] == {
        "source_id": p, "locator": "p. 12", "has_page": True, "valid": True, "evidence_class": "primary"}
    assert claims[1]["status"] == "unsupported" and "40%" in claims[1]["text"]
    sm = t["summary"]
    assert sm["unsupported"] == 1 and sm["primary_cited"] == 1 and sm["secondary_cited"] == 1 and sm["invalid"] == 1
    # La checklist evidenzia le affermazioni senza supporto (non bloccante).
    items = {c["key"]: c for c in client.get(f"/api/reports/{rep['id']}/check").json()["checklist"]}
    assert not items["claims_supported"]["ok"] and "40%" in items["claims_supported"]["detail"]
    assert not items["pages"]["ok"] and "1 su 2" in items["pages"]["detail"]
    assert items["evidence_class"]["ok"]


def test_methodology_sentences_need_no_source(client):
    rep = _report(client)
    rep = _put(client, rep, "methodology", body="Abbiamo analizzato 120 documenti d'archivio datati tra il 1945 e il 1960.")
    t = client.get(f"/api/reports/{rep['id']}/trace").json()
    assert t["summary"]["unsupported"] == 0 and t["summary"]["exempt"] == 1


def test_bibliography_entries_cited_consulted_or_unused(client):
    a, b, c = _src(client, title="Citata"), _src(client, title="Consultata"), _src(client, title="Dimenticata")
    rep = _report(client)
    rep = _put(client, rep, "analysis", body=f"Nel 1950 il debito scese al 60% del PIL [@{a}, p. 3].")
    rep = client.patch(f"/api/reports/{rep['id']}", json={"source_ids": [c], "consulted_ids": [b]}).json()
    assert set(rep["source_ids"]) == {b, c} and rep["consulted_ids"] == [b]
    t = client.get(f"/api/reports/{rep['id']}/trace").json()
    status = {u["source_id"]: u["status"] for u in t["bibliography"]}
    assert status == {a: "cited", b: "consulted", c: "unused"}
    assert next(u for u in t["bibliography"] if u["source_id"] == a)["locators"] == ["p. 3"]
    items = {i["key"]: i for i in client.get(f"/api/reports/{rep['id']}/check").json()["checklist"]}
    assert not items["bib_used"]["ok"] and "Dimenticata" in items["bib_used"]["detail"]
    # Fonti di altri utenti o inesistenti non possono essere indicate come consultate.
    assert client.patch(f"/api/reports/{rep['id']}", json={"consulted_ids": [9999]}).status_code == 422


def _series(client, name="Debito pubblico italiano", unit="% PIL"):
    csv = "date,value\n1950,60.1\n1951,58.4\n1952,57.0\n"
    return client.post("/api/finance/series/upload", files={"file": ("d.csv", csv.encode())},
                       data={"name": name, "source_label": "Dati di prova", "unit": unit, "category": "public_debt"}).json()["id"]


def test_coherence_between_text_charts_tables_and_sources(client):
    sid = _series(client)
    other = _series(client, name="Tasso di cambio", unit="lire per dollaro")
    rep = _report(client)
    rep = _put(client, rep, "analysis", body=(
        "Il debito pubblico italiano nel 1951 era pari al 62,0% del PIL (Figura 1). "
        "Nel 1950 il debito pubblico era al 60,1% del PIL. Si veda la Figura 4 e la Tabella 2."),
        embeds=[{"type": "series", "series_id": sid, "caption": "Debito", "start_year": 1990, "end_year": 2000},
                {"type": "compare", "series_ids": [sid, other], "caption": "Confronto"},
                {"type": "table", "caption": "Dati", "columns": ["Anno", "Valore"], "rows": [["1950", "60,1"]]}])
    t = client.get(f"/api/reports/{rep['id']}/trace").json()
    kinds = [i["kind"] for i in t["coherence"]]
    assert sorted(kinds) == ["figure_ref", "period", "table_ref", "table_source", "units", "value"]
    value = next(i for i in t["coherence"] if i["kind"] == "value")
    assert "1951" in value["detail"] and "62" in value["detail"] and "58.4" in value["detail"]
    items = {i["key"]: i for i in client.get(f"/api/reports/{rep['id']}/check").json()["checklist"]}
    assert not items["coherence"]["ok"]


def test_section_version_history_and_restore(client):
    rep = _report(client)
    sec = _section(rep, "analysis")
    _put(client, rep, "analysis", body="Prima stesura.")
    _put(client, rep, "analysis", body="Seconda stesura, riveduta.")
    rep = _put(client, rep, "analysis", body="Seconda stesura, riveduta.")  # nessuna modifica: nessuna versione
    url = f"/api/reports/{rep['id']}/sections/{sec['id']}/versions"
    versions = client.get(url).json()
    assert [v["body"] for v in versions] == ["Prima stesura."]
    assert versions[0]["reason"] == "edit" and versions[0]["author"]
    rep = client.post(f"{url}/{versions[0]['id']}/restore").json()
    assert _section(rep, "analysis")["body"] == "Prima stesura." and rep["status"] == "draft"
    # Il ripristino è a sua volta annullabile.
    versions = client.get(url).json()
    assert [(v["reason"], v["body"]) for v in versions] == [("restore", "Seconda stesura, riveduta."), ("edit", "Prima stesura.")]
    # Una versione di un'altra sezione non si può applicare.
    other = _section(rep, "introduction")
    assert client.post(f"/api/reports/{rep['id']}/sections/{other['id']}/versions/{versions[0]['id']}/restore").status_code == 404


def test_versions_are_capped(client, monkeypatch):
    from nexus.services import studio

    monkeypatch.setattr(studio, "MAX_VERSIONS", 3)
    rep = _report(client)
    for i in range(6):
        _put(client, rep, "analysis", body=f"Stesura {i}.")
    sec = _section(rep, "analysis")
    versions = client.get(f"/api/reports/{rep['id']}/sections/{sec['id']}/versions").json()
    assert [v["body"] for v in versions] == ["Stesura 4.", "Stesura 3.", "Stesura 2."]
