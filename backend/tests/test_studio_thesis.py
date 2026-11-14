"""Rapporti da tesi: citazioni da Ask the Archive, stili di citazione, tabelle da CSV, confronti, modello tesi, checklist."""

import io
import zipfile

from nexus.studio import citations

from .factories import upload

CSV = "Paese;Aiuti (mln $)\nRegno Unito;3.189,8\nFrancia;2.713,6\n\nFonte;CRS R45079, Tabella 2\nURL;https://crsreports.congress.gov\n"


def _src(client, **kw):
    r = client.post("/api/sources", json={"title": "The Marshall Plan: Design, Accomplishments, and Significance", "authors": ["Tarnoff, Curt"], "year": 2018,
                                         "publisher": "Congressional Research Service", **kw})
    assert r.status_code == 201, r.text
    return r.json()


def _series(client, name, rows):
    csv = "date,value\n" + "\n".join(f"{y}-01-01,{v}" for y, v in rows)
    r = client.post("/api/finance/series/upload", files={"file": ("s.csv", csv.encode())}, data={"name": name, "source_label": "Maddison 2023"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"] if "id" in r.json() else r.json()["series"]["id"]


def test_footnotes_short_form_and_ivi():
    class S:
        def __init__(self, i, a, t, y):
            self.id, self.authors, self.title, self.year = i, a, t, y
    a, b = S(1, ["Tarnoff, Curt"], "The Marshall Plan: Design, Accomplishments, and Significance", 2018), S(2, ["Milward, Alan S."], "The Reconstruction of Western Europe", 1984)
    n = citations.Notes(lambda s: f"{s.authors[0]} ({s.year}). {s.title}.")
    out = citations.render_styled("Primo [@1, p. 5]. Ancora [@1, p. 9]. Altro [@2]. Di nuovo [@1].", "footnotes", {}, {1: a, 2: b}, n)
    assert citations.FN_RX.findall(out) == ["1", "2", "3", "4"] and " \x00" not in out
    assert n.items[0] == "Tarnoff, Curt (2018). The Marshall Plan: Design, Accomplishments, and Significance, p. 5."
    assert n.items[1] == "Ivi, p. 9." and n.items[3] == "Tarnoff, The Marshall Plan: Design, Accomplishments…"
    assert citations.render_styled("Vedi [@2, p. 3].", "author_date", {}, {2: b}, None) == "Vedi (Milward 1984, p. 3)."


def test_quote_from_document_requires_bibliographic_record(client):
    rep = client.post("/api/reports", json={"title": "Piano Marshall"}).json()
    sec = next(s for s in rep["sections"] if s["key"] == "evidence")
    doc = upload(client, "crs.txt", b"The top recipients of Marshall Plan aid were the United Kingdom and France.").json()
    q = {"text": "The top recipients of Marshall Plan aid were the United Kingdom", "document_id": doc["id"], "locator": "p. 9"}
    r = client.post(f"/api/reports/{rep['id']}/sections/{sec['id']}/quote", json=q)
    assert r.status_code == 422 and r.json()["error"]["details"]["code"] == "no_source"
    s = _src(client)
    assert client.patch(f"/api/documents/{doc['id']}", json={"source_id": s["id"]}).status_code == 200
    r = client.post(f"/api/reports/{rep['id']}/sections/{sec['id']}/quote", json={**q, "comment": "Secondo il CRS,"})
    body = next(x for x in r.json()["sections"] if x["key"] == "evidence")["body"]
    assert body == f"Secondo il CRS, «The top recipients of Marshall Plan aid were the United Kingdom» [@{s['id']}, p. 9]"


def test_table_from_csv_document(client):
    doc = upload(client, "aiuti.csv", CSV.encode("utf-8"), category="dataset").json()
    t = client.get(f"/api/reports-tables/{doc['id']}").json()
    assert t["columns"] == ["Paese", "Aiuti (mln $)"] and t["rows"] == [["Regno Unito", "3.189,8"], ["Francia", "2.713,6"]]
    assert t["source_note"] == "Fonte: CRS R45079, Tabella 2 — https://crsreports.congress.gov"
    txt = upload(client, "a.txt", b"testo").json()
    assert client.get(f"/api/reports-tables/{txt['id']}").status_code == 422


def test_thesis_export_with_footnotes_tables_compare_and_chronology(client):
    s = _src(client)
    ev = client.post("/api/history/events", json={"title": "Il Senato approva il programma", "start_year": 1948, "start_month": 3, "start_day": 13}).json()
    client.post(f"/api/history/events/{ev['id']}/sources", json={"source_id": s["id"], "pages": "p. 5"})
    it = _series(client, "PIL Italia", [(1938, 4000), (1946, 3805), (1950, 5582), (1960, 9000)])
    fr = _series(client, "PIL Francia", [(1946, 5000), (1950, 6000), (1960, 9500)])
    rep = client.post("/api/reports", json={"title": "Il Piano Marshall", "author": "M. Rossi", "citation_style": "footnotes", "template": "thesis"}).json()
    assert rep["citation_style"] == "footnotes" and rep["template"] == "thesis"
    for sec in rep["sections"]:
        body = f"Testo di {sec['title']} [@{s['id']}, p. 5]. Ancora [@{s['id']}, p. 9]."
        embeds = []
        if sec["key"] == "analysis":
            embeds = [{"type": "compare", "series_ids": [it, fr], "start_year": 1946, "end_year": 1955, "rebase": True, "caption": "PIL pro capite"},
                      {"type": "table", "caption": "Aiuti per paese", "columns": ["Paese", "mln $"], "rows": [["Italia", "1.508,8"]], "source_note": "Fonte: CRS"}]
        r = client.put(f"/api/reports/{rep['id']}/sections/{sec['id']}", json={"body": body, "embeds": embeds})
        assert r.status_code == 200, r.text
    chk = client.get(f"/api/reports/{rep['id']}/check").json()
    keys = {c["key"]: c for c in chk["checklist"]}
    assert keys["sections"]["ok"] and keys["cited"]["ok"] and not keys["verified"]["ok"] and not keys["length"]["ok"]

    import docx
    d = docx.Document(io.BytesIO(client.get(f"/api/reports/{rep['id']}/export/docx").content))
    text = "\n".join(p.text for p in d.paragraphs)
    assert "1. Introduzione" in text and "Indice" in text and "Appendice A. Cronologia" in text and "Appendice B. Nota sulle fonti" in text
    assert "Figura 1." in text and "Tabella 1." in text and "Elenco delle figure" in text
    assert "[1" not in text  # niente numeri tra parentesi con lo stile a note
    parts = {str(p.partname) for p in d.part.package.iter_parts()}
    assert "/word/footnotes.xml" in parts
    foot = next(p for p in d.part.package.iter_parts() if str(p.partname) == "/word/footnotes.xml").blob.decode()
    assert "Tarnoff, Curt. (2018)" in foot and "Ivi, p. 9." in foot
    assert "13/3/1948" in "\n".join(c.text for t in d.tables for row in t.rows for c in row.cells)

    pdf = client.get(f"/api/reports/{rep['id']}/export/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    z = zipfile.ZipFile(io.BytesIO(client.get(f"/api/reports/{rep['id']}/export/latex").content))
    tex = z.read("main.tex").decode()
    assert r"\documentclass[11pt,a4paper]{report}" in tex and r"\tableofcontents" in tex and r"\footnote{Ivi, p. 9.}" in tex and r"\appendix" in tex


def test_author_date_bibliography_is_alphabetical(client):
    a = _src(client)
    b = client.post("/api/sources", json={"title": "The Reconstruction of Western Europe", "authors": ["Milward, Alan S."], "year": 1984}).json()
    rep = client.post("/api/reports", json={"title": "R", "citation_style": "author_date"}).json()
    sec = rep["sections"][1]
    client.put(f"/api/reports/{rep['id']}/sections/{sec['id']}", json={"body": f"Uno [@{a['id']}, p. 2] e due [@{b['id']}]."})
    import docx
    d = docx.Document(io.BytesIO(client.get(f"/api/reports/{rep['id']}/export/docx").content))
    text = "\n".join(p.text for p in d.paragraphs)
    assert "Uno (Tarnoff 2018, p. 2) e due (Milward 1984)." in text
    assert text.index("Milward, Alan S. (1984)") < text.index("Tarnoff, Curt. (2018)")
    assert client.patch(f"/api/reports/{rep['id']}", json={"citation_style": "bad"}).status_code == 422
