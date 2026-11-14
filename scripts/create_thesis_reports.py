"""Crea nei progetti di ricerca (Piano Marshall, FSE) un rapporto in formato tesi, con note a piè di pagina.

Uso:  scripts/py.sh scripts/create_thesis_reports.py --author "Nome Cognome"
Online si lancia dalla GitHub Action «Rapporti tesi». L'account è quello dell'amministratore attivo.
Carica i documenti (se mancano) e li collega alla scheda bibliografica, scrive le sezioni con citazioni
[@fonte, pagina], aggiunge tabelle, grafici e citazioni testuali da Ask the Archive. Il rapporto resta in
BOZZA: va riletto e approvato dall'autore. Idempotente: un rapporto con lo stesso titolo non viene ricreato.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select  # noqa: E402

from nexus.api.schemas_research import DocumentUpdate, SourceIn  # noqa: E402
from nexus.api.schemas_studio import ChapterIn, QuoteIn, ReportCreate, SectionIn  # noqa: E402
from nexus.core.config import get_settings  # noqa: E402
from nexus.core.research_kits import KITS_BY_ID  # noqa: E402
from nexus.database.migrate import upgrade_to_head  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.models import Document, Project, Report, Series, Source, User  # noqa: E402
from nexus.services import documents, research, research_kits, sources, studio  # noqa: E402

DATA = Path(__file__).resolve().parent / "thesis_data"


def build(db, user, settings, kit_id: str, spec: dict, author: str) -> str:
    proj = db.scalar(select(Project).where(Project.owner_id == user.id, Project.title == research_kits.project_title(KITS_BY_ID[kit_id])))
    if proj is None:
        return f"{kit_id}: progetto non trovato (crealo prima con «Progetti di ricerca»)"
    if db.scalar(select(Report.id).where(Report.owner_id == user.id, Report.title == spec["title"])):
        return f"{kit_id}: rapporto già presente, non modificato"
    # fonti: esistenti (per titolo) o nuove
    src: dict[str, int] = {}
    mine = list(db.scalars(select(Source).where(Source.owner_id == user.id)))
    for key, how in spec["sources"].items():
        if "match" in how:
            s = next((x for x in mine if x.title.strip() == how["match"] or x.title.startswith(how["match"])), None)
            if s is None:
                return f"{kit_id}: fonte «{how['match']}» non trovata"
        else:
            s = next((x for x in mine if x.title == how["create"]["title"]), None) or sources.create_source(db, user, SourceIn(**how["create"]))
        src[key] = s.id
    # documenti collegati alla loro scheda
    for d in spec["documents"]:
        doc = db.scalar(select(Document).where(Document.owner_id == user.id, Document.title == d["title"]))
        if doc is None:
            doc = documents.import_bytes(db, user, settings, filename=d["file"], data=(DATA / d["file"]).read_bytes(), title=d["title"],
                                         author=d["author"], project_id=proj.id)
        if doc.source_id != src[d["source"]]:
            documents.update_document(db, user, doc.id, DocumentUpdate(source_id=src[d["source"]]))

    def fill(text: str) -> str:
        return re.sub(r"\[@([A-Z0-9]+)", lambda m: f"[@{src[m.group(1)]}", text)

    rep = studio.create_report(db, user, ReportCreate(title=spec["title"], subtitle=spec.get("subtitle", ""), author=author, project_id=proj.id,
                                                      citation_style="footnotes", template="thesis"))
    for ch in reversed(spec.get("chapters", [])):  # ogni capitolo è inserito subito dopo «Analisi»
        rep = studio.add_chapter(db, user, rep.id, ChapterIn(title=ch["title"], after_key=ch.get("after", "analysis")))
    by_name = {s.key if s.key != "chapter" else s.title: s.id for s in rep.sections}
    bodies = {**spec["sections"], **{c["title"]: c["body"] for c in spec.get("chapters", [])}}
    series = {s.name: s.id for s in db.scalars(select(Series).where(Series.owner_id == user.id))}
    for name, body in bodies.items():
        embeds = []
        for e in spec.get("embeds", {}).get(name, []):
            if e["type"] == "table_doc":
                doc = db.scalar(select(Document).where(Document.owner_id == user.id, Document.title == e["doc_title"]))
                if doc:
                    t = studio.document_table(db, user, settings, doc.id)
                    embeds.append({"type": "table", "caption": e["caption"], "columns": t.columns, "rows": t.rows, "source_note": t.source_note, "document_id": doc.id})
            elif e["type"] == "compare":
                ids = [series[n] for n in e["series"] if n in series]
                if ids:
                    embeds.append({"type": "compare", "series_ids": ids, "caption": e["caption"], "start_year": e.get("start_year"),
                                   "end_year": e.get("end_year"), "rebase": e.get("rebase", False)})
            elif e["type"] == "series" and e["series"] in series:
                embeds.append({"type": "series", "series_id": series[e["series"]], "caption": e["caption"]})
        studio.update_section(db, user, rep.id, by_name[name], SectionIn.model_validate({"body": fill(body), "embeds": embeds}))
    notes = []
    for q in spec.get("quotes", []):
        ans = research.ask(db, user, settings, q["question"], None, 8)
        hit = next(((c, p) for c in ans.claims if c.type == "documented_fact" and q["contains"] in c.text
                    for p in ans.passages if c.evidence and p.chunk_id == c.evidence[0]), None)
        if hit is None:
            notes.append(f"citazione «{q['contains']}» non trovata")
            continue
        c, p = hit
        studio.add_quote(db, user, rep.id, by_name[q["section"]], QuoteIn(text=c.text, document_id=p.document_id,
                                                                          locator=q.get("page") or p.locator or "", comment=q.get("comment", "")))
    check = studio.check(db, user, rep.id)
    todo = [f"{i.label} ({i.detail})" if i.detail else i.label for i in check.checklist if not i.ok]
    return f"{kit_id}: rapporto #{rep.id} creato. Da completare: {'; '.join(todo) or 'nulla'}" + (f". Note: {'; '.join(notes)}" if notes else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default="", help="Autore da mostrare nel frontespizio")
    ap.add_argument("--kit", choices=sorted(KITS_BY_ID), action="append")
    args = ap.parse_args()
    settings = get_settings()
    upgrade_to_head(settings.database_url)
    spec = json.loads((DATA / "reports.json").read_text(encoding="utf-8"))
    with Database(settings.database_url).session_factory() as db:
        admins = list(db.scalars(select(User).where(User.role.in_(("admin", "owner")), User.is_active.is_(True)).order_by(User.id)))
        if not admins:
            sys.exit("Nessun amministratore attivo: impossibile scegliere l'account.")
        user = next((u for u in admins if u.role == "admin"), admins[0])
        print(f"Account: utente #{user.id} ({user.role})")
        for kit_id in args.kit or list(spec):
            print(build(db, user, settings, kit_id, spec[kit_id], args.author.strip()))


if __name__ == "__main__":
    main()
