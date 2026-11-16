"""Confidence System: valutazione delle fonti per dimensioni distinte, indipendenza prudente, motivazioni esplicite.

Principi verificati:
* la conferma dei metadati su registro accerta l'identità dell'opera, non l'autorevolezza né il contenuto;
* l'autorevolezza si legge da tipo, editore e rivista, mai dal titolo;
* la classificazione primaria/secondaria indicata dall'utente prevale su quella dedotta dal tipo;
* stessa opera, stessa fonte primaria, autore in comune o stessa raccolta compilativa = una sola conferma;
* senza pagina o passaggio indicati il livello non supera «media»; ogni motivazione è esplicita.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from nexus.api.schemas_history import EventIn
from nexus.api.schemas_research import SourceIn
from nexus.discovery import connections as cx
from nexus.discovery import evidence as ev
from nexus.discovery import hypotheses as hy
from nexus.models import DiscoveryConnection, User
from nexus.services import history, sources


@pytest.fixture
def user(db):
    return db.scalar(select(User))


def _src(db, user, status="unverified", **kw):
    s = sources.create_source(db, user, SourceIn(**{"source_type": "book", "year": 2000, **kw}))
    s.verification_status = status
    db.commit()
    return s


def test_registry_confirmation_is_identity_not_authority_or_content(db, user):
    blog = _src(db, user, "verified_registry", source_type="web", title="Il blog della crisi", doi="10.1234/blog")
    a = ev.assess_source(blog)
    assert a["identity"] == "confirmed" and a["verified"] is True
    assert a["authority"] == "low" and a["qualified"] is False  # metadati confermati ≠ fonte autorevole
    assert any("il contenuto non è stato controllato" in r for r in a["reasons"])
    # Una scheda con DOI inesistente o metadati discordanti ha identità dubbia e non conta come conferma.
    bad = _src(db, user, "registry_mismatch", title="Studio citato male", publisher="Banca d'Italia")
    assert ev.assess_source(bad)["doubtful"] is True
    level, reasons, _ = ev.grade(db, [bad])
    assert level == "low" and any(r.startswith("Escluse: 1 fonti con identità dubbia") for r in reasons)


def test_authority_is_read_from_publisher_not_title(db, user):
    web = _src(db, user, source_type="web", title="Central Bank secrets revealed")
    book = _src(db, user, title="Storia della Banca centrale", publisher="Editore Pinco")
    inst = _src(db, user, title="Relazione annuale", publisher="Banca d'Italia")
    assert ev.assess_source(web)["authority"] == "low"
    assert ev.assess_source(book)["authority"] == "medium"
    assert ev.assess_source(inst)["authority"] == "high"
    archive = _src(db, user, source_type="archive", title="Carte private")
    assert ev.assess_source(archive)["authority"] == "medium"  # prima finiva tra le «pagine web»


def test_user_classification_of_originality_prevails(db, user):
    s = _src(db, user, source_type="book", title="Diario di un banchiere (1929)", evidence_class="primary")
    a = ev.assess_source(s)
    assert a["originality"] == "primary" and any("indicata in bibliografia" in r for r in a["reasons"])
    wd = _src(db, user, source_type="web", title="Wikidata Q1: crisi", url="https://www.wikidata.org/wiki/Q1")
    assert ev.assess_source(wd)["originality"] == "tertiary" and ev.assess_source(wd)["aggregator"] == "wikidata"


def test_common_origin_is_never_counted_as_independent_confirmation(db, user):
    a = _src(db, user, "verified_user", title="La grande crisi", authors=["Rossi, Mario"])
    b = _src(db, user, "verified_user", title="Banche e crisi", authors=["Bianchi, Anna", "Rossi, Mario"], year=2005)
    c = _src(db, user, "verified_user", title="Il 1929", authors=["Verdi, Luca"], year=2010)
    groups, notes = ev.independence(db, [a, b, c])
    assert len(groups) == 2 and any("autore in comune (Rossi, Mario)" in n for n in notes)
    # Più voci di Wikidata/Wikipedia vengono dalla stessa raccolta: una sola conferma.
    w1 = _src(db, user, source_type="web", title="Wikidata Q1", url="https://www.wikidata.org/wiki/Q1")
    w2 = _src(db, user, source_type="web", title="Wikidata Q2", url="https://www.wikidata.org/wiki/Q2")
    w3 = _src(db, user, source_type="web", title="Voce Wikipedia", url="https://it.wikipedia.org/wiki/Crisi")
    groups, notes = ev.independence(db, [w1, w2, w3])
    assert len(groups) == 1 and all("stessa raccolta compilativa" in n for n in notes)
    level, reasons, _ = ev.grade(db, [w1, w2, w3])
    assert level == "low" and "in 1 gruppi indipendenti" in reasons[0]
    # Stessa opera con schede diverse (stesso DOI) e fonte primaria dichiarata in comune.
    d1 = _src(db, user, title="Articolo", doi="10.5555/x1")
    d2 = _src(db, user, title="Articolo (copia)", doi="10.5555/X1")
    assert len(ev.independent_groups(db, [d1, d2])) == 1


def test_levels_are_prudent_and_explained(db, user):
    a = _src(db, user, "verified_registry", title="Studio A", authors=["Neri, P."], publisher="Cambridge University Press", doi="10.1234/a1")
    b = _src(db, user, "verified_user", title="Studio B", authors=["Gialli, R."], year=2003)
    level, reasons, assessed = ev.grade(db, [a, b])
    assert level == "high"
    assert any(r.startswith("Qualità: 2 gruppi") for r in reasons) and reasons[-1] == ev.CONTENT_NOTE
    # Senza pagina o passaggio indicati non si va oltre «media».
    level, reasons, _ = ev.grade(db, [a, b], claim_refs=0)
    assert level == "medium" and any(r.startswith("Ancoraggio: nessun collegamento") for r in reasons)
    level, reasons, _ = ev.grade(db, [a, b], claim_refs=2)
    assert level == "high" and any("indicarli non prova il sostegno" in r for r in reasons)
    # Fonti senza identità accertata: mai «alta», anche se indipendenti.
    u1, u2 = _src(db, user, title="U1", authors=["X"]), _src(db, user, title="U2", authors=["Y"])
    level, reasons, _ = ev.grade(db, [u1, u2])
    assert level == "medium" and any(r.startswith("Metadati: 2 fonti senza identità accertata") for r in reasons)
    # Una contraddizione abbassa di un livello.
    assert ev.grade(db, [a, b], contradictions=1)[0] == "medium"


def test_event_connections_use_page_anchoring(db, user):
    s1 = _src(db, user, "verified_user", title="Fonte uno", authors=["A"])
    s2 = _src(db, user, "verified_user", title="Fonte due", authors=["B"], year=2001)
    e1 = history.create_event(db, user, EventIn(title="Crollo di borsa", start_year=1929, reliability="probable"))
    e2 = history.create_event(db, user, EventIn(title="Crisi bancaria", start_year=1930, reliability="probable"))
    history.link_source(db, user, e1.id, s1.id, "", "")
    history.link_source(db, user, e2.id, s2.id, "", "")
    level, reasons, _ = cx._grade_events(db, [e1, e2])
    assert level == "medium" and any(r.startswith("Ancoraggio: nessun") for r in reasons)
    e3 = history.create_event(db, user, EventIn(title="Fallimenti a catena", start_year=1931, reliability="probable"))
    history.link_source(db, user, e3.id, s1.id, "45-47", "")
    level, reasons, _ = cx._grade_events(db, [e3, e2])
    assert level == "high" and any(r.startswith("Ancoraggio: 1 collegamenti") for r in reasons)
    # L'evento senza pagina lo segnala.
    out = history.to_out(db, e2)
    assert "Nessuna fonte indica la pagina" in out.source_warning


def test_hypothesis_source_check_needs_two_independent_qualified_groups(db, user):
    a = _src(db, user, "verified_user", title="Primo studio", authors=["Rossi, Mario"])
    b = _src(db, user, "verified_user", title="Secondo studio", authors=["Rossi, Mario"], year=2004)
    c = DiscoveryConnection(owner_id=user.id, fingerprint="t", kind="shared_actors", title="t", elements=[], sources=[a.id, b.id])
    out = hy._sources(db, c)
    assert out["outcome"] == "weak" and "1 gruppi indipendenti" in out["detail"] and "non sul contenuto" in out["detail"]
    assert out["common_origin"] and "autore in comune" in out["common_origin"][0]
    d = _src(db, user, "verified_user", title="Terzo studio", authors=["Verdi, Luca"], year=2008)
    c.sources = [a.id, b.id, d.id]
    assert hy._sources(db, c)["outcome"] == "supports"


def test_assessment_endpoint_shows_every_dimension(client):
    s = client.post("/api/sources", json={"source_type": "article", "title": "Articolo", "container": "Journal of Economic History",
                                          "evidence_class": "secondary", "provenance": "Catalogo SBN"}).json()
    a = client.get(f"/api/sources/{s['id']}/assessment").json()
    assert a["identity"] == "unchecked" and a["authority"] == "medium" and a["originality"] == "secondary"
    prefixes = {r.split(":")[0] for r in a["reasons"]}
    assert {"Metadati", "Autorevolezza", "Originalità", "Provenienza della scheda"} <= prefixes
    assert "non controlla che le fonti sostengano" in a["content_note"]
    assert client.get("/api/sources/999999/assessment").status_code == 404
