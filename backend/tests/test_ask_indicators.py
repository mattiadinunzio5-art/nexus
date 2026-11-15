"""Ask the Archive: rilevanza, copertura e supporto sono tre indicatori distinti; le risposte non sostenute sono dichiarate."""

from .factories import make_pdf


def _upload(client, name, data, title):
    r = client.post("/api/documents", files={"file": (name, data)}, data={"title": title, "category": "source_material"})
    assert r.status_code == 201, r.text
    return r.json()


def test_supported_answer_has_quote_document_and_page(client):
    pdf = make_pdf(["Introduction to the report.", "Global plastic production rose from 2 million tonnes in 1950 to 380 million tonnes in 2015."])
    _upload(client, "geyer.pdf", pdf, "Geyer 2017")
    r = client.post("/api/research/ask", json={"question": "produzione di plastica nel 1950"}).json()
    assert r["answer_status"] in ("supported", "partial")
    claim = r["claims"][0]
    assert claim["type"] == "documented_fact" and "plastic production" in claim["text"]
    assert claim["citations"] == ["Geyer 2017, p. 2"]
    hit = r["passages"][0]
    assert hit["relevance"] == 1.0 and hit["coverage"] > 0 and hit["citation"] == "Geyer 2017, p. 2"
    assert {"produzione", "plastica"} <= set(hit["matched_terms"])  # concetti italiani trovati nel testo inglese


def test_scattered_terms_are_not_support(client):
    text = (b"The plastic bag was introduced in Sweden. Many years later the oceans were studied by marine biologists. "
            b"Production figures for steel are discussed in the appendix.\n")
    _upload(client, "mix.txt", text * 2, "Miscellanea")
    r = client.post("/api/research/ask", json={"question": "plastic production in the oceans"}).json()
    hit = r["passages"][0]
    assert hit["coverage"] >= 0.6  # il passaggio contiene i termini…
    assert hit["support"] in ("weak", "partial")  # …ma nessuna frase li riunisce tutti
    assert r["answer_status"] == "unsupported"
    assert r["claims"][0]["type"] == "missing" and "non sostengono" in r["claims"][0]["text"]


def test_no_documents_is_declared(client):
    r = client.post("/api/research/ask", json={"question": "inflazione in Germania nel 1923"}).json()
    assert r["answer_status"] == "unsupported" and r["claims"][0]["type"] == "missing"
