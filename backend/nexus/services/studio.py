"""Research Studio: rapporti, capitoli, appunti, citazioni verificabili, esportazione."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas_studio import ChapterIn, CheckItem, DocTable, NoteIn, QuoteIn, ReportCheck, ReportCreate, ReportUpdate, SectionIn
from ..core.errors import ConfirmationRequiredError, NotFoundError, ValidationFailedError
from ..models import Document, Note, Project, Report, ReportSection, ResearchRun, Series, SimulationRun, Source, User
from ..models.studio import STANDARD_SECTIONS
from ..research.citations import VERIFICATION_LABEL, format_citation
from ..studio import charts, citations, export
from . import activity

VERIFIED = ("verified_user", "verified_registry")


def _project(db: Session, user: User, project_id: int | None) -> None:
    from . import sharing

    if project_id is not None and sharing.RANK.get(sharing.role_in(db, user, project_id) or "", 0) < sharing.RANK["editor"]:
        raise ValidationFailedError("Progetto inesistente o senza permessi di modifica.")


def create_report(db: Session, user: User, data: ReportCreate, origin: str = "manual") -> Report:
    _project(db, user, data.project_id)
    r = Report(owner_id=user.id, origin=origin, **data.model_dump())
    r.sections = [ReportSection(ordinal=i, key=k, title=t, body="", embeds=[]) for i, (k, t) in enumerate(STANDARD_SECTIONS)]
    db.add(r)
    db.flush()
    activity.record(db, user=user, actor="user", action="report.create", entity_type="report", entity_id=r.id, summary=f"Creato il rapporto «{r.title}»")
    db.commit()
    db.refresh(r)
    return r


def list_reports(db: Session, user: User, project_id: int | None = None) -> list[Report]:
    from . import sharing

    shared = sharing.shared_project_ids(db, user)
    stmt = select(Report).where((Report.owner_id == user.id) | (Report.project_id.in_(shared)))
    if project_id is not None:
        stmt = stmt.where(Report.project_id == project_id)
    return list(db.scalars(stmt.order_by(Report.updated_at.desc())))


def get_report(db: Session, user: User, report_id: int, minimum: str = "viewer") -> Report:
    """Accesso: proprietario, oppure membro del progetto del rapporto con il ruolo minimo richiesto."""
    from . import sharing

    r = db.get(Report, report_id)
    if r is None:
        raise NotFoundError("Rapporto non trovato.")
    if r.owner_id == user.id:
        return r
    role = sharing.role_in(db, user, r.project_id)
    if role is None:
        raise NotFoundError("Rapporto non trovato.")
    if sharing.RANK[role] < sharing.RANK[minimum]:
        from .auth import ForbiddenError

        raise ForbiddenError("Permessi insufficienti: accesso in sola lettura.")
    return r


def _owner(db: Session, r: Report) -> User:
    # Fonti, serie e simulazioni di un rapporto appartengono al suo proprietario.
    return db.get(User, r.owner_id)


def _to_draft(r: Report) -> None:
    # Ogni modifica a un rapporto approvato lo riporta in bozza: l'approvazione vale per il contenuto approvato.
    r.status = "draft"


def update_report(db: Session, user: User, report_id: int, data: ReportUpdate) -> Report:
    r = get_report(db, user, report_id, "editor")
    changes = data.model_dump(exclude_unset=True)
    if "project_id" in changes:
        _project(db, user, changes["project_id"])
    if changes.get("source_ids") is not None:
        ids = list(dict.fromkeys(changes["source_ids"]))
        found = set(db.scalars(select(Source.id).where(Source.owner_id == r.owner_id, Source.id.in_(ids))))
        if set(ids) - found:
            raise ValidationFailedError(f"Fonti inesistenti: {sorted(set(ids) - found)}")
        changes["source_ids"] = ids
    for k, v in changes.items():
        setattr(r, k, v)
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def update_section(db: Session, user: User, report_id: int, section_id: int, data: SectionIn) -> Report:
    r = get_report(db, user, report_id, "editor")
    sec = next((s for s in r.sections if s.id == section_id), None)
    if sec is None:
        raise NotFoundError("Sezione non trovata.")
    if data.title is not None:
        if sec.key != "chapter":
            raise ValidationFailedError("Il titolo delle sezioni obbligatorie non è modificabile.")
        sec.title = data.title
    if data.body is not None:
        sec.body = data.body
    if data.embeds is not None:
        sec.embeds = [e.model_dump() for e in data.embeds]
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def add_chapter(db: Session, user: User, report_id: int, data: ChapterIn) -> Report:
    r = get_report(db, user, report_id, "editor")
    anchor = next((s for s in r.sections if s.key == data.after_key or str(s.id) == data.after_key), None)
    if anchor is None:
        raise ValidationFailedError("Sezione di riferimento inesistente.")
    for s in r.sections:
        if s.ordinal > anchor.ordinal:
            s.ordinal += 1
    r.sections.append(ReportSection(ordinal=anchor.ordinal + 1, key="chapter", title=data.title, body="", embeds=[]))
    _to_draft(r)
    db.commit()
    db.refresh(r)
    r.sections.sort(key=lambda s: s.ordinal)
    return r


def delete_chapter(db: Session, user: User, report_id: int, section_id: int) -> Report:
    r = get_report(db, user, report_id, "editor")
    sec = next((s for s in r.sections if s.id == section_id), None)
    if sec is None or sec.key != "chapter":
        raise ValidationFailedError("Si possono eliminare solo i capitoli aggiuntivi, non le sezioni obbligatorie.")
    r.sections.remove(sec)
    for i, s in enumerate(sorted(r.sections, key=lambda x: x.ordinal)):
        s.ordinal = i
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def move_chapter(db: Session, user: User, report_id: int, section_id: int, direction: int) -> Report:
    r = get_report(db, user, report_id, "editor")
    ordered = sorted(r.sections, key=lambda s: s.ordinal)
    i = next((k for k, s in enumerate(ordered) if s.id == section_id), None)
    if i is None or ordered[i].key != "chapter":
        raise ValidationFailedError("Solo i capitoli aggiuntivi possono essere spostati.")
    j = i + direction
    if 0 <= j < len(ordered):
        ordered[i].ordinal, ordered[j].ordinal = ordered[j].ordinal, ordered[i].ordinal
    _to_draft(r)
    db.commit()
    db.refresh(r)
    return r


def delete_report(db: Session, user: User, report_id: int, confirm: bool) -> None:
    r = get_report(db, user, report_id)
    if r.owner_id != user.id:
        from .auth import ForbiddenError

        raise ForbiddenError("Solo il proprietario può eliminare il rapporto.")
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un rapporto richiede conferma (confirm=true).")
    db.delete(r)
    activity.record(db, user=user, actor="user", action="report.delete", entity_type="report", entity_id=report_id, summary=f"Eliminato il rapporto «{r.title}»")
    db.commit()


# --- Verifica e bibliografia -------------------------------------------------------------------


def _bibliography(db: Session, user: User, r: Report) -> tuple[list[Source], list[int], dict[int, int]]:
    ordered = sorted(r.sections, key=lambda s: s.ordinal)
    cited = citations.cited_ids([s.body for s in ordered])
    sources = {s.id: s for s in db.scalars(select(Source).where(Source.owner_id == user.id, Source.id.in_(cited + list(r.source_ids))))}
    invalid = [i for i in cited if i not in sources]
    order = [i for i in cited if i in sources] + [i for i in r.source_ids if i in sources and i not in cited]
    numbering = {sid: n for n, sid in enumerate(order, start=1)}
    return [sources[i] for i in order], invalid, numbering


def check(db: Session, user: User, report_id: int) -> ReportCheck:
    r = get_report(db, user, report_id)
    user = _owner(db, r)
    bib, invalid, numbering = _bibliography(db, user, r)
    empty = [s.title for s in r.sections if s.key != "chapter" and not s.body.strip()]
    unverified = [{"id": s.id, "citation": format_citation(s), "status": VERIFICATION_LABEL[s.verification_status]} for s in bib if s.verification_status not in VERIFIED]
    problems = []
    for s in r.sections:
        for e in s.embeds:
            if e["type"] == "series" and not _owned(db, Series, e["series_id"], user):
                problems.append(f"«{s.title}»: serie {e['series_id']} inesistente")
            if e["type"] == "simulation" and not _owned(db, SimulationRun, e["simulation_id"], user):
                problems.append(f"«{s.title}»: simulazione {e['simulation_id']} inesistente")
            if e["type"] == "compare":
                for sid in e["series_ids"]:
                    if not _owned(db, Series, sid, user):
                        problems.append(f"«{s.title}»: serie {sid} inesistente nel confronto")
    warnings = []
    if r.contains_ai_text:
        warnings.append("Il rapporto contiene testo generato o estratto automaticamente: rivedilo prima dell'approvazione.")
    if not bib:
        warnings.append("Nessuna fonte in bibliografia.")
    cited_n = len(citations.cited_ids([s.body for s in r.sections]))
    body_sections = [s for s in r.sections if s.key not in ("abstract", "limitations") and s.body.strip()]
    uncited = [s.title for s in body_sections if not citations.CITE_RX.search(s.body)]
    embeds = [e for s in r.sections for e in s.embeds]
    no_caption = sum(1 for e in embeds if not (e.get("caption") or "").strip() and e["type"] != "series")
    words = sum(len(s.body.split()) for s in r.sections)
    checklist = [
        CheckItem(key="sections", label="Tutte le sezioni sono compilate", ok=not empty, blocking=True, detail=", ".join(empty)),
        CheckItem(key="citations_valid", label="Le citazioni rimandano a fonti esistenti", ok=not invalid, blocking=True,
                  detail=", ".join(f"@{i}" for i in invalid)),
        CheckItem(key="embeds", label="Grafici e tabelle sono disponibili", ok=not problems, blocking=True, detail="; ".join(problems)),
        CheckItem(key="cited", label="Il testo cita le fonti", ok=cited_n > 0, blocking=False,
                  detail=f"{cited_n} fonti citate" if cited_n else "Nessuna citazione [@id] nel testo: la bibliografia non dimostra nulla."),
        CheckItem(key="sections_cited", label="Ogni capitolo argomentativo ha almeno una citazione", ok=not uncited, blocking=False, detail=", ".join(uncited)),
        CheckItem(key="verified", label="Le fonti citate sono verificate sull'originale", ok=not unverified, blocking=False,
                  detail=f"{len(unverified)} da verificare in Bibliography" if unverified else ""),
        CheckItem(key="captions", label="Tabelle e confronti hanno una didascalia", ok=no_caption == 0, blocking=False,
                  detail=f"{no_caption} senza didascalia" if no_caption else ""),
        CheckItem(key="author", label="Autore indicato (frontespizio)", ok=bool(r.author.strip()), blocking=False),
        CheckItem(key="length", label="Lunghezza adeguata (almeno 1.500 parole per una tesina)", ok=words >= 1500, blocking=False, detail=f"{words} parole"),
    ]
    if r.contains_ai_text:
        checklist.append(CheckItem(key="ai", label="Testo automatico rivisto", ok=False, blocking=False, detail="Rileggi le parti estratte o generate da NEXUS."))
    return ReportCheck(ready=not (empty or invalid or problems), checklist=checklist, empty_sections=empty, invalid_citations=invalid, unverified_sources=unverified,
                       cited_sources=len([1 for s in bib if s.id in numbering]), bibliography_size=len(bib), embed_problems=problems, warnings=warnings)


def _owned(db: Session, model, oid: int, user: User):
    o = db.get(model, oid)
    return o if o is not None and o.owner_id == user.id else None


def set_status(db: Session, user: User, report_id: int, status: str) -> Report:
    r = get_report(db, user, report_id, "editor")
    if status == "approved":
        c = check(db, user, report_id)
        if not c.ready:
            raise ValidationFailedError("Il rapporto non può essere approvato: completa le sezioni e correggi citazioni e allegati.", details=c.model_dump())
    r.status = status
    activity.record(db, user=user, actor="user", action=f"report.{status}", entity_type="report", entity_id=r.id,
                    summary=f"Rapporto «{r.title}» {'approvato' if status == 'approved' else 'riportato in bozza'}")
    db.commit()
    db.refresh(r)
    return r


# --- Vista ed esportazione ----------------------------------------------------------------------


def _in_range(date: str, e: dict) -> bool:
    try:
        y = int(date[:5] if date.startswith("-") else date[:4])
    except ValueError:
        return True
    return (e.get("start_year") is None or y >= e["start_year"]) and (e.get("end_year") is None or y <= e["end_year"])


def _period(e: dict) -> str:
    a, b = e.get("start_year"), e.get("end_year")
    return f", {a if a is not None else '…'}–{b if b is not None else '…'}" if a is not None or b is not None else ""


def _compare_figure(db: Session, user: User, e: dict) -> export.Figure:
    series = [x for x in (_owned(db, Series, sid, user) for sid in e["series_ids"]) if x is not None]
    if not series:
        return export.Figure(caption=e.get("caption") or "Confronto non disponibile", note="serie eliminate o inesistenti")
    annual = all(s.frequency == "A" for s in series)
    key = (lambda d: d[:4]) if annual else (lambda d: d[:7])
    data = {s.name: {key(o.date): o.value for o in s.observations if _in_range(o.date, e) and o.value is not None} for s in series}
    x = sorted(set().union(*[set(v) for v in data.values()]))
    note_extra = ""
    if e.get("rebase"):
        common = [d for d in x if all(d in v for v in data.values())]
        if common:
            b = common[0]
            data = {n: {d: (val / v[b] * 100 if v[b] else None) for d, val in v.items()} for n, v in data.items()}
            note_extra = f" Valori ribasati: {b} = 100."
    units = sorted({s.unit for s in series if s.unit})
    png = charts.line_chart(e.get("caption") or "Confronto", x, {n: [v.get(d) for d in x] for n, v in data.items()},
                            "indice" if e.get("rebase") else (units[0] if len(units) == 1 else ""))
    sources = "; ".join(dict.fromkeys(s.source_label for s in series))
    return export.Figure(caption=(e.get("caption") or "Confronto tra serie") + _period(e), png=png, note=f"Fonti: {sources}.{note_extra}")


def _figure(db: Session, user: User, e: dict) -> export.Figure:
    if e["type"] == "compare":
        return _compare_figure(db, user, e)
    if e["type"] == "series":
        s = _owned(db, Series, e["series_id"], user)
        if s is None:
            return export.Figure(caption=e.get("caption") or "Serie non disponibile", note="serie eliminata o inesistente")
        obs = [o for o in s.observations if _in_range(o.date, e)]
        png = charts.line_chart(s.name, [o.date[:7] if s.frequency != "A" else o.date[:4] for o in obs], {s.name: [o.value for o in obs]}, s.unit, s.source_label)
        return export.Figure(caption=(e.get("caption") or s.name) + _period(e), png=png,
                             note=f"Fonte: {s.source_label}; unità: {s.unit or 'n.d.'}; ultimo aggiornamento dichiarato: {s.source_last_updated or 'n.d.'}")
    sim = _owned(db, SimulationRun, e["simulation_id"], user)
    if sim is None:
        return export.Figure(caption=e.get("caption") or "Simulazione non disponibile", note="simulazione eliminata o inesistente")
    res = sim.result.get("results", {})
    label = sim.result.get("label", "")
    png = None
    if sim.kind == "debt":
        series = {"Base": res["baseline"]["debt"]}
        if "rate_shock" in res:
            series["Shock tassi"] = res["rate_shock"]["debt"]
        if "crisis" in res:
            series["Crisi"] = res["crisis"]["debt"]
        png = charts.line_chart(sim.title, [str(y) for y in res["years"]], series, "% PIL")
    elif "fan" in res:
        fan = res["fan"]
        png = charts.line_chart(sim.title, [str(f["t"]) for f in fan], {"95° perc.": [f["p95"] for f in fan], "Mediana": [f["p50"] for f in fan], "5° perc.": [f["p5"] for f in fan]})
    elif sim.kind == "backtest":
        eq = res["equity"]
        png = charts.line_chart(sim.title, [x["date"][:7] for x in eq], {"Strategia": [x["strategy"] for x in eq], "Buy & hold": [x["benchmark"] for x in eq]})
    return export.Figure(caption=e.get("caption") or sim.title, png=png, note=f"{label} Metodo: {sim.result.get('method', '')}")


def _alpha_key(src: Source) -> str:
    return ((src.authors[0] if src.authors else "") or src.title or "").lower()


def _match_bib(linked: Source, bib: list[Source]) -> Source | None:
    """La fonte collegata all'evento è in bibliografia, oppure ne cita il titolo (es. una nota «… «Titolo» (R45079) …» del kit)."""
    import re

    for b in bib:
        if b.id == linked.id:
            return b
    text = (linked.title or "").lower()
    for b in bib:
        core = re.sub(r"\s*\([^)]*\)\s*$", "", b.title or "").strip().lower()
        if len(core) >= 20 and core in text:
            return b
    return None


def _chronology(db: Session, user: User, bib: list[Source]) -> list[export.ChronoItem]:
    from ..models import EventSource, HistoricalEvent

    if not bib:
        return []
    rows = db.execute(select(HistoricalEvent, EventSource, Source).join(EventSource, EventSource.event_id == HistoricalEvent.id)
                      .join(Source, Source.id == EventSource.source_id).where(HistoricalEvent.owner_id == user.id)).all()
    seen: dict[int, export.ChronoItem] = {}
    order: dict[int, tuple] = {}
    for ev, link, linked in rows:
        src = _match_bib(linked, bib)
        if src is None:
            continue
        who = citations._surname(src)
        ref = (f"{who} {src.year or 's.d.'}" if who else citations.short_title(src)) + (f", {link.pages}" if link.pages else "")
        if ev.id in seen:
            if ref not in seen[ev.id].source:
                seen[ev.id].source += f"; {ref}"
            continue
        date = "/".join(str(x) for x in (ev.start_day, ev.start_month) if x) + ("/" if ev.start_month else "") + str(ev.start_year)
        seen[ev.id] = export.ChronoItem(date=date, text=ev.title, source=ref)
        order[ev.id] = (ev.start_year, ev.start_month or 0, ev.start_day or 0)
    return [seen[k] for k in sorted(seen, key=lambda k: order[k])]


def build_view(db: Session, user: User, report_id: int) -> export.ReportView:
    r = get_report(db, user, report_id)
    user = _owner(db, r)
    bib, invalid, numbering = _bibliography(db, user, r)
    style = r.citation_style or "numeric"
    by_id = {s.id: s for s in bib}
    notes = citations.Notes(format_citation) if style == "footnotes" else None
    sections = []
    for s in sorted(r.sections, key=lambda x: x.ordinal):
        figs = [_figure(db, user, e) for e in s.embeds if e["type"] in ("series", "simulation", "compare")]
        tables = [export.Table(e.get("caption", ""), e["columns"], e["rows"], e.get("source_note", "")) for e in s.embeds if e["type"] == "table"]
        if notes:
            notes.new_chapter()
        body = export.paragraphs(citations.render_styled(s.body, style, numbering, by_id, notes))
        sections.append(export.SectionView(s.title, body, figs, tables, key=s.key, numbered=s.key != "abstract"))
    notices = []
    if r.status != "approved":
        notices.append("BOZZA: rapporto non ancora approvato dall'autore.")
    if r.contains_ai_text:
        notices.append("Parti del testo sono state generate o estratte automaticamente da NEXUS: verificare prima dell'uso.")
    if invalid:
        notices.append(f"Citazioni non valide (fonti inesistenti): {invalid}.")
    unv = sum(1 for s in bib if s.verification_status not in VERIFIED)
    if unv:
        notices.append(f"{unv} fonti in bibliografia non sono verificate (segnalate).")
    entries = [export.BibEntry(numbering[s.id] if style == "numeric" else None, format_citation(s), s.verification_status in VERIFIED,
                               VERIFICATION_LABEL[s.verification_status]) for s in (bib if style == "numeric" else sorted(bib, key=_alpha_key))]
    project = ""
    if r.project_id:
        p = db.get(Project, r.project_id)
        project = p.title if p else ""
    thesis = r.template == "thesis"
    return export.ReportView(r.title, r.subtitle, r.author, "Approvato" if r.status == "approved" else "Bozza",
                             datetime.now().strftime("%d/%m/%Y %H:%M"), sections, entries, notices,
                             style=style, template=r.template or "standard", footnotes=notes.items if notes else [], project=project,
                             chronology=_chronology(db, user, bib) if thesis else [],
                             source_notes=[export.BibEntry(None, format_citation(s), s.verification_status in VERIFIED, VERIFICATION_LABEL[s.verification_status])
                                           for s in sorted(bib, key=_alpha_key)] if thesis else [])


def export_report(db: Session, user: User, report_id: int, fmt: str) -> tuple[bytes, str]:
    v = build_view(db, user, report_id)
    if fmt == "latex":
        from ..studio.bibtex import cite_key, source_to_bibtex

        r = get_report(db, user, report_id)
        bib, _, _ = _bibliography(db, _owner(db, r), r)
        taken: set[str] = set()
        data = export.to_latex_zip(v, "\n".join(source_to_bibtex(s, cite_key(s.authors, s.year, s.title, taken)) for s in bib))
    else:
        data = export.to_pdf(v) if fmt == "pdf" else export.to_docx(v)
    activity.record(db, user=user, actor="user", action=f"report.export_{fmt}", entity_type="report", entity_id=report_id,
                    summary=f"Esportato «{v.title}» in {fmt.upper()} ({v.status})")
    db.commit()
    return data, v.title


# --- Citazioni da Ask the Archive e tabelle dai documenti ------------------------------------------


def add_quote(db: Session, user: User, report_id: int, section_id: int, data: QuoteIn) -> Report:
    """Aggiunge alla sezione una citazione testuale con il riferimento [@fonte, collocazione]."""
    r = get_report(db, user, report_id, "editor")
    sec = next((s for s in r.sections if s.id == section_id), None)
    if sec is None:
        raise NotFoundError("Sezione non trovata.")
    doc = db.get(Document, data.document_id)
    owner = _owner(db, r)
    if doc is None or doc.owner_id != owner.id:
        raise NotFoundError("Documento non trovato.")
    if not doc.source_id:
        raise ValidationFailedError("Il documento non ha una scheda bibliografica: collegala nella pagina del documento, poi riprova.",
                                    details={"document_id": doc.id, "code": "no_source"})
    loc = data.locator.strip()
    text = " ".join(data.text.split()).strip("«»\"' ")
    para = (data.comment.strip() + " " if data.comment.strip() else "") + f"«{text}» [@{doc.source_id}{', ' + loc if loc else ''}]"
    sec.body = (sec.body.rstrip() + "\n\n" + para) if sec.body.strip() else para
    _to_draft(r)
    activity.record(db, user=user, actor="user", action="report.quote", entity_type="report", entity_id=r.id,
                    summary=f"Citazione da «{doc.title}» aggiunta a «{sec.title}»")
    db.commit()
    db.refresh(r)
    return r


def document_table(db: Session, user: User, settings, document_id: int) -> DocTable:
    """Legge un CSV/XLSX importato come tabella (max 12 colonne, 200 righe) con la nota sulla fonte."""
    import csv
    import io

    from . import documents

    d = documents.get_document(db, user, document_id)
    if d.kind not in ("csv", "xlsx"):
        raise ValidationFailedError("Solo i documenti CSV o XLSX possono diventare tabelle.")
    raw = documents.file_bytes(settings, d)
    rows: list[list[str]] = []
    if d.kind == "csv":
        text = raw.decode("utf-8-sig", errors="replace")
        head = text.split("\n", 1)[0]
        delim = ";" if head.count(";") >= head.count(",") else ","
        rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text), delimiter=delim)]
    else:
        import openpyxl

        ws = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True).worksheets[0]
        rows = [["" if c is None else str(c).strip() for c in r] for r in ws.iter_rows(values_only=True)]
    # la tabella finisce alla prima riga vuota; dopo possono esserci righe «Fonte;…» e «URL;…»
    table: list[list[str]] = []
    tail: list[list[str]] = []
    for r in rows:
        if not any(r):
            if table:
                tail = rows[rows.index(r) + 1:]
                break
            continue
        table.append(r)
    if not table:
        raise ValidationFailedError("Il file non contiene una tabella leggibile.")
    meta = {r[0].strip().lower(): r[1].strip() for r in tail if len(r) >= 2}
    source_note = ""
    if meta.get("fonte"):
        source_note = "Fonte: " + meta["fonte"] + (f" — {meta['url']}" if meta.get("url") else "")
    elif d.source_id:
        src = db.get(Source, d.source_id)
        source_note = "Fonte: " + format_citation(src) if src else ""
    else:
        source_note = f"Fonte: documento «{d.title}»" + (f" — {d.license_note}" if d.license_note else "")
    columns = table[0][:12]
    body = [(r + [""] * len(columns))[: len(columns)] for r in table[1:201]]
    return DocTable(caption=d.title[:300], columns=columns, rows=body, source_note=source_note[:600], truncated=len(table) - 1 > 200 or len(table[0]) > 12)


# --- Da una ricerca della War Room ------------------------------------------------------------------


CLAIM_LABEL = {"documented_fact": "Fatto documentato", "interpretation": "Interpretazione", "hypothesis": "Ipotesi", "estimate": "Stima", "missing": "Dato mancante"}


def from_research_run(db: Session, user: User, run_id: int) -> Report:
    run = db.get(ResearchRun, run_id)
    if run is None or run.owner_id != user.id:
        raise NotFoundError("Ricerca non trovata.")
    if run.status != "approved":
        raise ValidationFailedError("Solo una ricerca approvata può diventare un rapporto.")
    ev = {e["id"]: e for e in run.evidence}
    # Le evidenze da documenti collegati a una scheda bibliografica diventano citazioni verificabili.
    source_of: dict[str, int] = {}
    for e in run.evidence:
        if e["kind"] == "passage":
            d = db.get(Document, e["ref"].get("document_id"))
            if d and d.source_id:
                source_of[e["id"]] = d.source_id

    def cite(ids) -> str:
        parts = []
        for i in ids:
            key = i if isinstance(i, str) else next((k for k, e in ev.items() if e["ref"].get("chunk_id") == i), None)
            if key in source_of:
                parts.append(f"[@{source_of[key]}]")
            elif key in ev:
                parts.append(f"({ev[key]['label']})")
        return " ".join(parts)

    res = run.result
    claims = res.get("claims", [])
    r = create_report(db, user, ReportCreate(title=f"Ricerca: {run.question[:280]}", project_id=run.project_id), origin=f"research_run:{run.id}")
    r.contains_ai_text = run.mode == "ai"
    body = {
        "abstract": (res.get("abstract") or "") + ("\n\n[Abstract generato da modello AI]" if run.mode == "ai" and res.get("abstract") else ""),
        "introduction": f"Domanda di ricerca: {run.question}",
        "methodology": "\n".join([
            f"- Modalità: {'AI (' + run.provider + (', ' + run.model if run.model else '') + ')' if run.mode == 'ai' else 'motore locale, senza modelli AI'}",
            f"- Pianificazione: {run.plan.get('method', 'n.d.')}; query: {', '.join(run.plan.get('search_queries', []))}",
            f"- Evidenze raccolte: {len(run.evidence)} (documenti, eventi d'archivio, serie)",
            f"- Agenti: " + ", ".join(f"{s.agent} ({'non eseguito' if s.status == 'skipped' else s.executor})" for s in run.steps),
            f"- Approvata dall'utente il {run.decided_at:%d/%m/%Y}" if run.decided_at else "- Approvazione: n.d.",
        ]),
        "analysis": "\n\n".join(f"[{CLAIM_LABEL.get(c['type'], c['type'])}] {c['text']} {cite(c.get('evidence', []))}".strip()
                                for c in claims if c["type"] != "missing"),
        "evidence": "\n".join(f"- {e['id']}: {e['label']} — {e['source']}" + (f" {cite([e['id']])}" if e["id"] in source_of else "") for e in run.evidence),
        "counterarguments": "\n".join(f"- {x}" for x in res.get("limitations", [])),
        "conclusions": "",
        "limitations": "\n".join(f"- [Dato mancante] {c['text']}" for c in claims if c["type"] == "missing"),
    }
    for s in r.sections:
        s.body = body.get(s.key, "")
    db.commit()
    db.refresh(r)
    return r


# --- Appunti ------------------------------------------------------------------------------------------------


def _note_refs(db: Session, user: User, data: NoteIn) -> None:
    _project(db, user, data.project_id)
    if data.source_id is not None and not _owned(db, Source, data.source_id, user):
        raise ValidationFailedError("Fonte inesistente.")
    if data.document_id is not None and not _owned(db, Document, data.document_id, user):
        raise ValidationFailedError("Documento inesistente.")


def list_notes(db: Session, user: User, project_id: int | None = None) -> list[Note]:
    from . import sharing

    if project_id is not None:
        sharing.require(db, user, project_id, "viewer")
        stmt = select(Note).where(Note.project_id == project_id)
    else:
        stmt = select(Note).where(Note.owner_id == user.id)
    return list(db.scalars(stmt.order_by(Note.updated_at.desc())))


def create_note(db: Session, user: User, data: NoteIn) -> Note:
    _note_refs(db, user, data)
    n = Note(owner_id=user.id, **data.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def update_note(db: Session, user: User, note_id: int, data: NoteIn) -> Note:
    n = _owned(db, Note, note_id, user)
    if n is None:
        raise NotFoundError("Appunto non trovato.")
    _note_refs(db, user, data)
    for k, v in data.model_dump().items():
        setattr(n, k, v)
    db.commit()
    db.refresh(n)
    return n


def delete_note(db: Session, user: User, note_id: int, confirm: bool) -> None:
    n = _owned(db, Note, note_id, user)
    if n is None:
        raise NotFoundError("Appunto non trovato.")
    if not confirm:
        raise ConfirmationRequiredError("Eliminare un appunto richiede conferma (confirm=true).")
    db.delete(n)
    db.commit()
