"""Schemi API — Research Studio e Daily Briefing (Fase 7)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from .schemas import CleanStr, ORMModel, UTCDateTime


YearOpt = Annotated[int, Field(ge=-5000, le=2200)] | None
CitationStyle = Literal["numeric", "footnotes", "author_date"]
Template = Literal["standard", "thesis"]


class SeriesEmbed(BaseModel):
    type: Literal["series"]
    series_id: int
    caption: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    start_year: YearOpt = None
    end_year: YearOpt = None


class CompareEmbed(BaseModel):
    """Più serie nello stesso grafico, su un periodo scelto, eventualmente ribasate a 100."""

    type: Literal["compare"]
    series_ids: list[int] = Field(min_length=1, max_length=8)
    caption: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    start_year: YearOpt = None
    end_year: YearOpt = None
    rebase: bool = False


class SimulationEmbed(BaseModel):
    type: Literal["simulation"]
    simulation_id: int
    caption: Annotated[CleanStr, StringConstraints(max_length=300)] = ""


class TableEmbed(BaseModel):
    type: Literal["table"]
    caption: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    source_note: Annotated[CleanStr, StringConstraints(max_length=600)] = ""
    document_id: int | None = None
    columns: list[Annotated[str, StringConstraints(max_length=100)]] = Field(min_length=1, max_length=12)
    rows: list[list[Annotated[str, StringConstraints(max_length=300)]]] = Field(max_length=200)

    @field_validator("rows")
    @classmethod
    def _width(cls, rows, info):
        n = len(info.data.get("columns", []))
        if any(len(r) != n for r in rows):
            raise ValueError("Ogni riga della tabella deve avere lo stesso numero di colonne dell'intestazione")
        return rows


Embed = Annotated[SeriesEmbed | CompareEmbed | SimulationEmbed | TableEmbed, Field(discriminator="type")]


class ReportCreate(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    subtitle: Annotated[CleanStr, StringConstraints(max_length=300)] = ""
    author: Annotated[CleanStr, StringConstraints(max_length=200)] = ""
    project_id: int | None = None
    citation_style: CitationStyle = "numeric"
    template: Template = "standard"


class ReportUpdate(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)] | None = None
    subtitle: Annotated[CleanStr, StringConstraints(max_length=300)] | None = None
    author: Annotated[CleanStr, StringConstraints(max_length=200)] | None = None
    project_id: int | None = None
    source_ids: list[int] | None = Field(default=None, max_length=500)
    citation_style: CitationStyle | None = None
    template: Template | None = None


class SectionIn(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)] | None = None
    body: Annotated[str, StringConstraints(max_length=200_000)] | None = None
    embeds: list[Embed] | None = Field(default=None, max_length=20)


class ChapterIn(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    after_key: str = "analysis"


class SectionOut(ORMModel):
    id: int
    ordinal: int
    key: str
    title: str
    body: str
    embeds: list


class ReportOut(ORMModel):
    id: int
    title: str
    subtitle: str
    author: str
    status: Literal["draft", "approved"]
    project_id: int | None
    source_ids: list[int]
    origin: str
    contains_ai_text: bool
    citation_style: str = "numeric"
    template: str = "standard"
    created_at: UTCDateTime
    updated_at: UTCDateTime
    sections: list[SectionOut]


class ReportSummary(ORMModel):
    id: int
    title: str
    status: str
    project_id: int | None
    origin: str
    updated_at: UTCDateTime


class CheckItem(BaseModel):
    key: str
    label: str
    ok: bool
    blocking: bool
    detail: str = ""


class QuoteIn(BaseModel):
    """Citazione testuale da Ask the Archive da aggiungere a una sezione."""

    text: Annotated[str, StringConstraints(min_length=3, max_length=4000)]
    document_id: int
    locator: Annotated[CleanStr, StringConstraints(max_length=40)] = ""
    comment: Annotated[str, StringConstraints(max_length=2000)] = ""


class DocTable(BaseModel):
    caption: str
    columns: list[str]
    rows: list[list[str]]
    source_note: str
    truncated: bool


class ReportCheck(BaseModel):
    ready: bool
    checklist: list[CheckItem] = []
    empty_sections: list[str]
    invalid_citations: list[int]
    unverified_sources: list[dict]
    cited_sources: int
    bibliography_size: int
    embed_problems: list[str]
    warnings: list[str]


class NoteIn(BaseModel):
    title: Annotated[CleanStr, StringConstraints(min_length=1, max_length=300)]
    body: Annotated[str, StringConstraints(max_length=100_000)] = ""
    project_id: int | None = None
    source_id: int | None = None
    document_id: int | None = None


class NoteOut(ORMModel):
    id: int
    title: str
    body: str
    project_id: int | None
    source_id: int | None
    document_id: int | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class BriefingIn(BaseModel):
    refresh_sources: bool = False


class BriefingOut(ORMModel):
    id: int
    trigger: str
    content: dict
    created_at: UTCDateTime
