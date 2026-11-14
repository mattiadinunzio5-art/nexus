"""Esportazione dei rapporti in PDF (ReportLab) e DOCX (python-docx).

L'input è una vista già risolta del rapporto (``ReportView``): sezioni con
testo in cui le citazioni sono già numerate, figure PNG, tabelle e bibliografia
con stato di verifica di ogni fonte.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field


@dataclass
class Figure:
    caption: str
    png: bytes | None = None
    note: str = ""


@dataclass
class Table:
    caption: str
    columns: list[str]
    rows: list[list[str]]
    note: str = ""


@dataclass
class SectionView:
    title: str
    paragraphs: list[str]
    figures: list[Figure] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    key: str = ""
    numbered: bool = True


@dataclass
class BibEntry:
    number: int | None
    citation: str
    verified: bool
    status_label: str


@dataclass
class ChronoItem:
    date: str
    text: str
    source: str


@dataclass
class ReportView:
    title: str
    subtitle: str
    author: str
    status: str
    generated_at: str
    sections: list[SectionView]
    bibliography: list[BibEntry]
    notices: list[str]
    style: str = "numeric"  # numeric | footnotes | author_date
    template: str = "standard"  # standard | thesis
    footnotes: list[str] = field(default_factory=list)
    project: str = ""
    chronology: list[ChronoItem] = field(default_factory=list)
    source_notes: list[BibEntry] = field(default_factory=list)

    @property
    def thesis(self) -> bool:
        return self.template == "thesis"

    def heading(self, s: SectionView, n: int | None) -> str:
        return f"{n}. {s.title}" if self.thesis and n else s.title

    def numbered_sections(self) -> list[tuple[SectionView, int | None]]:
        out, n = [], 0
        for s in self.sections:
            if self.thesis and s.numbered:
                n += 1
                out.append((s, n))
            else:
                out.append((s, None))
        return out

    def figure_list(self) -> list[str]:
        return [f"Figura {i}. {f.caption}" for i, f in enumerate((f for s in self.sections for f in s.figures), start=1)]

    def table_list(self) -> list[str]:
        return [f"Tabella {i}. {t.caption}" for i, t in enumerate((t for s in self.sections for t in s.tables), start=1)]


def split_notes(p: str) -> list[str | int]:
    """Divide un paragrafo in pezzi di testo e numeri di nota (int)."""
    from .citations import FN_RX

    out: list[str | int] = []
    pos = 0
    for m in FN_RX.finditer(p):
        if m.start() > pos:
            out.append(p[pos:m.start()])
        out.append(int(m.group(1)))
        pos = m.end()
    if pos < len(p):
        out.append(p[pos:])
    return out


def plain(p: str) -> str:
    return "".join(x if isinstance(x, str) else "" for x in split_notes(p))


def is_list(p: str) -> bool:
    lines = p.split("\n")
    return all(line.lstrip().startswith(("- ", "• ")) for line in lines)


BIB_NOTE = {
    "numeric": "Le fonti sono numerate nell'ordine di prima citazione.",
    "footnotes": "Fonti citate nelle note, in ordine alfabetico.",
    "author_date": "Fonti citate nel testo (autore anno), in ordine alfabetico.",
}


def paragraphs(body: str) -> list[str]:
    return [p.strip() for p in (body or "").replace("\r\n", "\n").split("\n\n") if p.strip()]


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_pdf(v: ReportView) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer
    from reportlab.platypus import Table as RLTable
    from reportlab.platypus import TableStyle
    from reportlab.platypus.tableofcontents import TableOfContents

    from .charts import font_bold_path, font_path

    if "NexusSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("NexusSans", font_path()))
        pdfmetrics.registerFont(TTFont("NexusSans-Bold", font_bold_path()))
        pdfmetrics.registerFontFamily("NexusSans", normal="NexusSans", bold="NexusSans-Bold", italic="NexusSans", boldItalic="NexusSans-Bold")
    base = ParagraphStyle("b", fontName="NexusSans", fontSize=10, leading=14.5, alignment=TA_LEFT, spaceAfter=6)
    h1 = ParagraphStyle("h1", parent=base, fontName="NexusSans-Bold", fontSize=20, leading=24, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base, fontName="NexusSans-Bold", fontSize=13, leading=17, spaceBefore=12, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=base, fontName="NexusSans-Bold", fontSize=10, leading=13, spaceBefore=6, spaceAfter=3)
    small = ParagraphStyle("s", parent=base, fontSize=8, leading=11, textColor=colors.HexColor("#555555"))
    warn = ParagraphStyle("w", parent=small, textColor=colors.HexColor("#9a5b00"))
    center = ParagraphStyle("c", parent=base, alignment=TA_CENTER)

    class Doc(SimpleDocTemplate):
        def afterFlowable(self, f):
            if isinstance(f, Paragraph) and getattr(f, "_toc", None):
                self.notify("TOCEntry", (0, f._toc, self.page))

    def head(text: str, toc: bool = True) -> Paragraph:
        p = Paragraph(_esc(text), h2)
        if toc and v.thesis:
            p._toc = text
        return p

    def para(p: str) -> str:
        return "".join(_esc(x) if isinstance(x, str) else f"<super>{x}</super>" for x in split_notes(p)).replace("\n", "<br/>")

    story: list = []
    if v.thesis:
        story += [Spacer(1, 5 * cm), Paragraph(_esc(v.title), ParagraphStyle("t", parent=h1, alignment=TA_CENTER, fontSize=24, leading=30))]
        if v.subtitle:
            story.append(Paragraph(_esc(v.subtitle), center))
        story.append(Spacer(1, 3 * cm))
        if v.author:
            story.append(Paragraph(f"di <b>{_esc(v.author)}</b>", center))
        if v.project:
            story.append(Paragraph(_esc(f"Progetto: {v.project}"), center))
        story += [Spacer(1, 4 * cm), Paragraph(_esc(f"{v.generated_at[:10]} · {v.status}"), ParagraphStyle("cs", parent=small, alignment=TA_CENTER))]
        for n in v.notices:
            story.append(Paragraph(_esc(n), ParagraphStyle("cw", parent=warn, alignment=TA_CENTER)))
        story.append(PageBreak())
    else:
        story.append(Paragraph(_esc(v.title), h1))
        if v.subtitle:
            story.append(Paragraph(_esc(v.subtitle), base))
        story.append(Paragraph(_esc(f"{v.author + ' · ' if v.author else ''}Generato da NEXUS il {v.generated_at} · Stato: {v.status}"), small))
        for n in v.notices:
            story.append(Paragraph(_esc(n), warn))
        story.append(Spacer(1, 0.4 * cm))

    numbered = v.numbered_sections()
    if v.thesis:
        abstract = [x for x in numbered if x[0].key == "abstract"]
        for s, _ in abstract:
            story.append(head(s.title, toc=False))
            story += [Paragraph(para(p), base) for p in s.paragraphs]
        if abstract:
            story.append(PageBreak())
        toc = TableOfContents()
        toc.levelStyles = [ParagraphStyle("toc", parent=base, leftIndent=0, firstLineIndent=0)]
        story += [Paragraph("Indice", h2), toc]
        figs, tabs = v.figure_list(), v.table_list()
        if figs:
            story += [Paragraph("Elenco delle figure", h3)] + [Paragraph(_esc(x), small) for x in figs]
        if tabs:
            story += [Paragraph("Elenco delle tabelle", h3)] + [Paragraph(_esc(x), small) for x in tabs]
        story.append(PageBreak())
        numbered = [x for x in numbered if x[0].key != "abstract"]

    fig_n = tab_n = 0
    for s, n in numbered:
        story.append(head(v.heading(s, n)))
        if not s.paragraphs and not s.figures and not s.tables:
            story.append(Paragraph("[Sezione non compilata]", warn))
        first_note, last_note = None, None
        for p in s.paragraphs:
            for x in split_notes(p):
                if isinstance(x, int):
                    first_note = first_note or x
                    last_note = x
            if is_list(p):
                story.append(ListFlowable([ListItem(Paragraph(para(line.lstrip()[2:]), base)) for line in p.split("\n")], bulletType="bullet", start="•"))
            else:
                story.append(Paragraph(para(p), base))
        for f in s.figures:
            fig_n += 1
            parts = []
            if f.png:
                parts.append(Image(io.BytesIO(f.png), width=16 * cm, height=7.55 * cm))
            parts.append(Paragraph(f"<b>Figura {fig_n}.</b> " + _esc(f.caption + (f" — {f.note}" if f.note else "")), small))
            story.append(KeepTogether(parts))
        for t in s.tables:
            tab_n += 1
            data = [[Paragraph(_esc(c), small) for c in t.columns]] + [[Paragraph(_esc(str(c)), small) for c in r] for r in t.rows]
            tbl = RLTable(data, repeatRows=1, hAlign="LEFT")
            tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                                     ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [Paragraph(f"<b>Tabella {tab_n}.</b> " + _esc(t.caption), small), tbl]
            if t.note:
                story.append(Paragraph(_esc(t.note), small))
            story.append(Spacer(1, 0.2 * cm))
        if first_note:
            # Nel PDF le note sono raccolte alla fine di ogni capitolo; nel DOCX e in LaTeX sono a piè di pagina.
            story.append(Paragraph("Note", h3))
            for k in range(first_note, last_note + 1):
                story.append(Paragraph(f"<super>{k}</super> " + _esc(v.footnotes[k - 1]), small))

    story.append(head("Bibliografia"))
    story.append(Paragraph(_esc(BIB_NOTE.get(v.style, "")), small))
    if not v.bibliography:
        story.append(Paragraph("Nessuna fonte citata.", warn))
    for b in v.bibliography:
        mark = "" if b.verified else f" [{b.status_label}]"
        story.append(Paragraph(_esc(f"{f'[{b.number}] ' if b.number else ''}{b.citation}{mark}"), base))
    if v.thesis:
        letter = iter("ABCDEFG")
        if v.chronology:
            story += [PageBreak(), head(f"Appendice {next(letter)}. Cronologia"),
                      Paragraph("Eventi dell'archivio collegati alle fonti del rapporto, ciascuno con la sua fonte.", small)]
            rows = [[Paragraph("<b>Data</b>", small), Paragraph("<b>Evento</b>", small), Paragraph("<b>Fonte</b>", small)]]
            rows += [[Paragraph(_esc(c.date), small), Paragraph(_esc(c.text), small), Paragraph(_esc(c.source), small)] for c in v.chronology]
            t = RLTable(rows, colWidths=[2.6 * cm, 8 * cm, 6 * cm], repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(t)
        if v.source_notes:
            story += [head(f"Appendice {next(letter)}. Nota sulle fonti"),
                      Paragraph("Stato di verifica di ogni fonte in bibliografia: «verificata» significa che l'autore ha controllato l'originale o che l'identificativo è stato confermato su un registro esterno.", small)]
            for b in v.source_notes:
                story.append(Paragraph(_esc(f"{b.citation} — {b.status_label}"), small))

    def on_page(canvas, doc):
        canvas.saveState()
        if not (v.thesis and doc.page == 1):
            canvas.setFont("NexusSans", 7)
            canvas.setFillColor(colors.HexColor("#777777"))
            canvas.drawString(2 * cm, 1.2 * cm, f"NEXUS · {v.title[:80]}")
            canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Pagina {doc.page}")
        if v.status != "Approvato":
            canvas.setFont("NexusSans-Bold", 54)
            canvas.setFillColor(colors.Color(0.8, 0.8, 0.8, alpha=0.25))
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(40)
            canvas.drawCentredString(0, 0, "BOZZA")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = Doc(buf, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm, bottomMargin=2 * cm, title=v.title, author=v.author or "NEXUS")
    doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _xml_text(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _docx_footnotes(d, notes: list[str]) -> None:
    """Aggiunge la parte footnotes.xml (python-docx non la crea da solo)."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.opc.packuri import PackURI
    from docx.opc.part import Part
    from docx.oxml import parse_xml

    body = [f'<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:separator/></w:r></w:p></w:footnote>',
            f'<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>']
    for i, n in enumerate(notes, start=1):
        body.append(f'<w:footnote w:id="{i}"><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                    f'<w:r><w:rPr><w:vertAlign w:val="superscript"/><w:sz w:val="18"/></w:rPr><w:footnoteRef/></w:r>'
                    f'<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve"> {_xml_text(n)}</w:t></w:r></w:p></w:footnote>')
    xml = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:footnotes xmlns:w="{_W}">{"".join(body)}</w:footnotes>'
    part = Part(PackURI("/word/footnotes.xml"), "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml", xml.encode("utf-8"), d.part.package)
    d.part.relate_to(part, RT.FOOTNOTES)
    settings = d.settings.element
    settings.append(parse_xml(f'<w:footnotePr xmlns:w="{_W}"><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'))


def _docx_para(d, text: str, style: str | None = None):
    from docx.oxml import parse_xml

    p = d.add_paragraph(style=style)
    for x in split_notes(text):
        if isinstance(x, int):
            p._p.append(parse_xml(f'<w:r xmlns:w="{_W}"><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteReference w:id="{x}"/></w:r>'))
        else:
            p.add_run(x)
    return p


def _docx_toc(d, entries: list[str]) -> None:
    """Campo TOC di Word: le voci scritte qui sono visibili subito; Word le aggiorna con i numeri di pagina all'apertura."""
    from docx.oxml import parse_xml

    def run(inner: str) -> str:
        return f'<w:r xmlns:w="{_W}">{inner}</w:r>'

    first = d.add_paragraph()
    first._p.append(parse_xml(run('<w:fldChar w:fldCharType="begin" w:dirty="true"/>')))
    first._p.append(parse_xml(run('<w:instrText xml:space="preserve"> TOC \\o "1-1" \\h \\z \\u </w:instrText>')))
    first._p.append(parse_xml(run('<w:fldChar w:fldCharType="separate"/>')))
    first.add_run(entries[0] if entries else "")
    last = first
    for e in entries[1:]:
        last = d.add_paragraph(e)
    last._p.append(parse_xml(run('<w:fldChar w:fldCharType="end"/>')))
    d.settings.element.append(parse_xml(f'<w:updateFields xmlns:w="{_W}" w:val="true"/>'))


def to_docx(v: ReportView) -> bytes:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.shared import Cm, Pt, RGBColor

    d = docx.Document()
    d.core_properties.title = v.title
    d.core_properties.author = v.author or "NEXUS"
    d.styles["Normal"].font.size = Pt(11)

    def small(text: str, color: RGBColor | None = None, align=None):
        p = d.add_paragraph()
        r = p.add_run(text)
        r.font.size = Pt(8)
        if color:
            r.font.color.rgb = color
        if align is not None:
            p.alignment = align
        return p

    def page_break():
        d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    numbered = v.numbered_sections()
    if v.thesis:
        for _ in range(6):
            d.add_paragraph()
        t = d.add_paragraph()
        t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = t.add_run(v.title)
        r.bold, r.font.size = True, Pt(26)
        if v.subtitle:
            st = d.add_paragraph(v.subtitle)
            st.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for _ in range(6):
            d.add_paragraph()
        if v.author:
            a = d.add_paragraph()
            a.alignment = WD_ALIGN_PARAGRAPH.CENTER
            a.add_run("di ")
            a.add_run(v.author).bold = True
        if v.project:
            pr = d.add_paragraph(f"Progetto: {v.project}")
            pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for _ in range(4):
            d.add_paragraph()
        small(f"{v.generated_at[:10]} · {v.status}", align=WD_ALIGN_PARAGRAPH.CENTER)
        for n in v.notices:
            small(n, RGBColor(0x9A, 0x5B, 0x00), WD_ALIGN_PARAGRAPH.CENTER)
        page_break()
        for s, _ in [x for x in numbered if x[0].key == "abstract"]:
            d.add_heading(s.title, level=1)
            for p in s.paragraphs:
                _docx_para(d, p)
            page_break()
        numbered = [x for x in numbered if x[0].key != "abstract"]
        d.add_heading("Indice", level=1)
        entries = [v.heading(s, n) for s, n in numbered] + ["Bibliografia"]
        letter = iter("ABCDEFG")
        if v.chronology:
            entries.append(f"Appendice {next(letter)}. Cronologia")
        if v.source_notes:
            entries.append(f"Appendice {next(letter)}. Nota sulle fonti")
        _docx_toc(d, entries)
        figs, tabs = v.figure_list(), v.table_list()
        if figs:
            d.add_heading("Elenco delle figure", level=2)
            for x in figs:
                d.add_paragraph(x)
        if tabs:
            d.add_heading("Elenco delle tabelle", level=2)
            for x in tabs:
                d.add_paragraph(x)
        page_break()
    else:
        d.add_heading(v.title, level=0)
        if v.subtitle:
            d.add_paragraph(v.subtitle)
        small(f"{v.author + ' · ' if v.author else ''}Generato da NEXUS il {v.generated_at} · Stato: {v.status}")
        for n in v.notices:
            small(n, RGBColor(0x9A, 0x5B, 0x00))

    fig_n = tab_n = 0
    for s, n in numbered:
        d.add_heading(v.heading(s, n), level=1)
        if not s.paragraphs and not s.figures and not s.tables:
            d.add_paragraph("[Sezione non compilata]")
        for p in s.paragraphs:
            if is_list(p):
                for line in p.split("\n"):
                    _docx_para(d, line.lstrip()[2:], "List Bullet")
            else:
                _docx_para(d, p)
        for f in s.figures:
            fig_n += 1
            if f.png:
                d.add_picture(io.BytesIO(f.png), width=Cm(16))
            cap = d.add_paragraph()
            cap.add_run(f"Figura {fig_n}. ").bold = True
            cap.add_run(f.caption + (f" — {f.note}" if f.note else ""))
            for r in cap.runs:
                r.font.size = Pt(8)
        for t in s.tables:
            tab_n += 1
            cap = d.add_paragraph()
            cap.add_run(f"Tabella {tab_n}. ").bold = True
            cap.add_run(t.caption)
            for r in cap.runs:
                r.font.size = Pt(8)
            tbl = d.add_table(rows=1, cols=len(t.columns))
            tbl.style = "Table Grid"
            for i, c in enumerate(t.columns):
                tbl.rows[0].cells[i].text = c
                for r in tbl.rows[0].cells[i].paragraphs[0].runs:
                    r.bold = True
            for row in t.rows:
                cells = tbl.add_row().cells
                for i, c in enumerate(row[: len(t.columns)]):
                    cells[i].text = str(c)
            for row in tbl.rows:
                for c in row.cells:
                    for r in c.paragraphs[0].runs:
                        r.font.size = Pt(9)
            if t.note:
                small(t.note)
    d.add_heading("Bibliografia", level=1)
    small(BIB_NOTE.get(v.style, ""))
    if not v.bibliography:
        d.add_paragraph("Nessuna fonte citata.")
    for b in v.bibliography:
        p = d.add_paragraph(f"{f'[{b.number}] ' if b.number else ''}{b.citation}" + ("" if b.verified else f" [{b.status_label}]"))
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.8)
    if v.thesis:
        letter = iter("ABCDEFG")
        if v.chronology:
            page_break()
            d.add_heading(f"Appendice {next(letter)}. Cronologia", level=1)
            small("Eventi dell'archivio collegati alle fonti del rapporto, ciascuno con la sua fonte.")
            tbl = d.add_table(rows=1, cols=3)
            tbl.style = "Table Grid"
            for i, h in enumerate(("Data", "Evento", "Fonte")):
                tbl.rows[0].cells[i].text = h
            for c in v.chronology:
                cells = tbl.add_row().cells
                cells[0].text, cells[1].text, cells[2].text = c.date, c.text, c.source
            for row in tbl.rows:
                for c in row.cells:
                    for r in c.paragraphs[0].runs:
                        r.font.size = Pt(9)
        if v.source_notes:
            d.add_heading(f"Appendice {next(letter)}. Nota sulle fonti", level=1)
            small("Stato di verifica di ogni fonte in bibliografia: «verificata» significa che l'autore ha controllato l'originale "
                  "o che l'identificativo è stato confermato su un registro esterno.")
            for b in v.source_notes:
                d.add_paragraph(f"{b.citation} — {b.status_label}", style="List Bullet")
    if v.footnotes:
        _docx_footnotes(d, v.footnotes)
    # numeri di pagina nel piè di pagina
    from docx.oxml import parse_xml

    fp = d.sections[0].footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for inner in ('<w:fldChar w:fldCharType="begin"/>', '<w:instrText xml:space="preserve"> PAGE </w:instrText>', '<w:fldChar w:fldCharType="end"/>'):
        fp._p.append(parse_xml(f'<w:r xmlns:w="{_W}"><w:rPr><w:sz w:val="16"/></w:rPr>{inner}</w:r>'))
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# --- LaTeX ---------------------------------------------------------------------------------------


def to_latex_zip(v: ReportView, bibtex: str) -> bytes:
    """Pacchetto ZIP: main.tex, references.bib e figure PNG. Compilabile con pdflatex (es. Overleaf)."""
    import zipfile

    from .bibtex import latex_escape as e

    def tex(p: str) -> str:
        return "".join(e(x) if isinstance(x, str) else rf"\footnote{{{e(v.footnotes[x - 1])}}}" for x in split_notes(p))

    cls = "report" if v.thesis else "article"
    sec = "chapter" if v.thesis else "section"
    lines = [
        rf"\documentclass[11pt,a4paper]{{{cls}}}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[italian]{babel}",
        r"\usepackage{lmodern}",
        r"\usepackage{graphicx}",
        r"\usepackage{booktabs}",
        r"\usepackage{longtable}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\usepackage[margin=2.5cm]{geometry}",
        "",
        rf"\title{{{e(v.title)}" + (rf"\\ \large {e(v.subtitle)}" if v.subtitle else "") + "}",
        rf"\author{{{e(v.author)}" + (rf"\\ \small Progetto: {e(v.project)}" if v.project else "") + "}",
        rf"\date{{{e(v.generated_at[:10])} --- {e(v.status)}}}",
        "",
        r"\begin{document}",
        r"\maketitle",
    ]
    for n in v.notices:
        lines.append(rf"\noindent\fbox{{\parbox{{\linewidth}}{{\small {e(n)}}}}}\par\medskip")
    numbered = v.numbered_sections()
    if v.thesis:
        for s, _ in [x for x in numbered if x[0].key == "abstract"]:
            lines += [r"\begin{abstract}", *[tex(" ".join(p.split("\n"))) for p in s.paragraphs], r"\end{abstract}"]
        numbered = [x for x in numbered if x[0].key != "abstract"]
        lines += [r"\tableofcontents"]
        if v.figure_list():
            lines.append(r"\listoffigures")
        if v.table_list():
            lines.append(r"\listoftables")
    files: dict[str, bytes] = {}
    fig_n = 0
    for s, n in numbered:
        lines += ["", rf"\{sec}{'' if (n or not v.thesis) else '*'}{{{e(s.title)}}}"]
        if not s.paragraphs and not s.figures and not s.tables:
            lines.append(r"\textit{[Sezione non compilata]}")
        for p in s.paragraphs:
            rows = p.split("\n")
            if is_list(p):
                lines.append(r"\begin{itemize}")
                lines += [rf"  \item {tex(r.lstrip()[2:])}" for r in rows]
                lines.append(r"\end{itemize}")
            else:
                lines += [tex(" ".join(rows)), ""]
        for f in s.figures:
            if f.png:
                fig_n += 1
                name = f"figures/figura{fig_n}.png"
                files[name] = f.png
                lines += [r"\begin{figure}[htbp]", r"\centering", rf"\includegraphics[width=\linewidth]{{{name}}}",
                          rf"\caption[{e(f.caption)}]{{{e(f.caption)}" + (rf" \\ \footnotesize {e(f.note)}" if f.note else "") + "}", r"\end{figure}"]
            else:
                lines.append(rf"\textit{{[Figura non disponibile: {e(f.caption)}]}}")
        for t in s.tables:
            cols = "l" * max(1, len(t.columns))
            lines += [r"\begin{table}[htbp]", r"\centering", r"\small", rf"\caption{{{e(t.caption)}}}", rf"\begin{{tabular}}{{{cols}}}", r"\toprule",
                      " & ".join(e(c) for c in t.columns) + r" \\", r"\midrule"]
            lines += [" & ".join(e(str(c)) for c in row) + r" \\" for row in t.rows]
            lines += [r"\bottomrule", r"\end{tabular}"]
            if t.note:
                lines.append(rf"\par\footnotesize {e(t.note)}")
            lines.append(r"\end{table}")
    if v.bibliography:
        lines += ["", rf"\begin{{thebibliography}}{{99}}"]
        if v.style != "numeric":
            lines = lines[:-1] + [r"\renewcommand{\refname}{Bibliografia}", r"\renewcommand{\bibname}{Bibliografia}", r"\begin{thebibliography}{99}"]
        for i, b in enumerate(v.bibliography, start=1):
            flag = "" if b.verified else rf" \textit{{[{e(b.status_label)}]}}"
            lines.append(rf"\bibitem{{ref{b.number or i}}} {e(b.citation)}{flag}")
        lines.append(r"\end{thebibliography}")
    if v.thesis and (v.chronology or v.source_notes):
        lines += ["", r"\appendix"]
        if v.chronology:
            lines += [rf"\{sec}{{Cronologia}}", r"\small", r"\begin{longtable}{p{2.3cm}p{7.5cm}p{5cm}}", r"\toprule", r"Data & Evento & Fonte \\", r"\midrule"]
            lines += [rf"{e(c.date)} & {e(c.text)} & {e(c.source)} \\" for c in v.chronology]
            lines += [r"\bottomrule", r"\end{longtable}", r"\normalsize"]
        if v.source_notes:
            lines += [rf"\{sec}{{Nota sulle fonti}}", r"\begin{itemize}"]
            lines += [rf"  \item {e(b.citation)} --- {e(b.status_label)}" for b in v.source_notes]
            lines.append(r"\end{itemize}")
    lines += [r"\end{document}", ""]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("main.tex", "\n".join(lines))
        z.writestr("references.bib", bibtex)
        z.writestr("LEGGIMI.txt", "Compila main.tex con pdflatex (ad esempio su Overleaf: Nuovo progetto > Carica progetto > questo ZIP).\n"
                   "Le citazioni seguono lo stile scelto nel rapporto (numeri, note a piè di pagina o autore-data). references.bib contiene\n"
                   "le stesse fonti in BibTeX per Zotero, JabRef o biblatex. Le fonti non verificate sono indicate.\n")
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()
