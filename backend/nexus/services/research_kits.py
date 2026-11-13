"""Crea un progetto da un kit di ricerca (core/research_kits.py) nell'account di un utente.

Il progetto contiene: un appunto-guida (obiettivi, passi, tabelle con fonte e licenza, lacune), le date
chiave come eventi collegati alla loro fonte, la bibliografia («non verificata»), le serie indicate e le
tabelle come file CSV tra i documenti. Idempotente: se il progetto esiste già non duplica nulla.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.schemas import ProjectCreate
from ..api.schemas_finance import SeriesImportIn
from ..api.schemas_history import EventIn
from ..api.schemas_research import SourceIn
from ..core import licenses
from ..core.config import Settings
from ..core.errors import NotFoundError
from ..core.research_kits import KITS_BY_ID
from ..models import Note, Project, Series, Source, User
from . import activity, documents, finance, history, projects, sources

log = logging.getLogger("nexus.research_kits")


def project_title(kit: dict) -> str:
    return f"Ricerca — {kit['title']}"[:200]


def _table_md(t: dict) -> list[str]:
    out = [f"### {t['title']}", ""]
    if t.get("unit"):
        out += [f"Unità: {t['unit']}", ""]
    out += ["| " + " | ".join(t["columns"]) + " |", "|" + "---|" * len(t["columns"])]
    out += ["| " + " | ".join(r) + " |" for r in t["rows"]]
    lic = licenses.get(t.get("license_id"))
    out += ["", f"Fonte: {t['source']}" + (f" — {t['source_url']}" if t.get("source_url") else "")]
    if lic:
        out.append(f"Licenza: {lic.license}. Attribuzione: {lic.attribution.get()}")
    if t.get("notes"):
        out.append(f"Note: {t['notes']}")
    return out + [""]


def guide_markdown(kit: dict) -> str:
    out = [kit["summary"], "", "## Obiettivi", *[f"- {g}" for g in kit["goals"]], "", "## Passi"]
    out += [f"{i}. **{s['title']}** — {s['detail']}" for i, s in enumerate(kit["steps"], start=1)]
    out += ["", "## Date chiave (già inserite come eventi, con la fonte)"]
    out += [f"- {d['date']}: {d['event']} — fonte: {d.get('source', 'da indicare')}" for d in kit["key_dates"]]
    if kit.get("tables"):
        out += ["", "## Dati", ""]
        for t in kit["tables"]:
            out += _table_md(t)
    if kit.get("gaps"):
        out += ["## Cosa manca e dove cercarlo", "",
                "Questi dati non sono disponibili in rete in forma aperta: NEXUS non li stima né li inventa.", ""]
        out += [f"- **{g['what']}** — {g['where']}" + (f" ({g['url']})" if g.get("url") else "") for g in kit["gaps"]]
    out += ["", "Le letture consigliate sono in bibliografia come «non verificate»: controllale sull'originale prima di citarle."]
    return "\n".join(out)


def _csv(t: dict) -> bytes:
    def q(v: str) -> str:
        return f'"{v.replace(chr(34), chr(34) * 2)}"' if any(c in v for c in '";\n') else v
    lines = [";".join(q(c) for c in t["columns"]), *(";".join(q(v) for v in r) for r in t["rows"])]
    lines += ["", f"Fonte;{q(t['source'])}", f"URL;{t.get('source_url', '')}"]
    return ("﻿" + "\n".join(lines) + "\n").encode("utf-8")


def _date(d: str) -> dict:
    parts = [int(x) for x in d.split("-")]
    return {"start_year": parts[0], "start_month": parts[1] if len(parts) > 1 else None, "start_day": parts[2] if len(parts) > 2 else None}


def _num(v: str) -> float:
    return float(v.replace(".", "").replace(",", "."))


def create(db: Session, user: User, settings: Settings, kit_id: str, *, fetch_series: bool = True) -> dict:
    kit = KITS_BY_ID.get(kit_id)
    if kit is None:
        raise NotFoundError("Kit di ricerca non trovato.")
    title = project_title(kit)
    if db.scalar(select(Project.id).where(Project.owner_id == user.id, Project.title == title)):
        return {"project_id": None, "skipped": True}
    report: dict = {"events": 0, "sources": 0, "series": 0, "documents": 0, "warnings": []}
    p = projects.create_project(db, user, ProjectCreate(title=title, description=kit["summary"][:2000]))
    db.add(Note(owner_id=user.id, project_id=p.id, title=f"Guida: {kit['title']}"[:300], body=guide_markdown(kit)))

    existing = {s.title.lower(): s for s in db.scalars(select(Source).where(Source.owner_id == user.id))}

    def source_for(text: str, **kw) -> Source:
        key = text[:500].lower()
        if key not in existing:
            existing[key] = sources.create_source(db, user, SourceIn(title=text[:500], **kw))
            report["sources"] += 1
        return existing[key]

    for d in kit["key_dates"]:
        e = history.create_event(db, user, EventIn(title=d["event"][:300], categories=["economic"], **_date(d["date"]),
                                                   reliability="probable" if d.get("source") else "unverified",
                                                   reliability_note=f"Kit di ricerca NEXUS «{kit['title']}»."))
        report["events"] += 1
        if d.get("source"):
            s = source_for(d["source"], source_type="document", notes="Fonte indicata dal kit di ricerca NEXUS; verificare sull'originale.")
            history.link_source(db, user, e.id, s.id, "", "")
    for r in kit["readings"]:
        source_for(r["title"], source_type=r.get("source_type", "book"), authors=r.get("authors", []), year=r.get("year"),
                   publisher=r.get("publisher", ""), notes=f"Lettura consigliata dal kit «{kit['title']}». Da verificare sull'originale.")

    for t in kit.get("tables", []):
        lic = licenses.get(t.get("license_id"))
        try:
            documents.import_bytes(db, user, settings, filename=f"{t['title'][:80]}.csv", data=_csv(t), title=t["title"][:300],
                                   category="dataset", project_id=p.id, origin="upload", origin_url=t.get("source_url", ""),
                                   license_note=(lic.license if lic else "Fonti indicate riga per riga"))
            report["documents"] += 1
        except Exception as exc:  # noqa: BLE001 — lo storage può mancare in locale: l'appunto contiene comunque la tabella
            report["warnings"].append(f"Tabella «{t['title']}» non salvata come documento: {exc}")
        spec = t.get("as_series")
        if spec and not db.scalar(select(Series.id).where(Series.owner_id == user.id, Series.name == spec["name"])):
            text = "date,value\n" + "\n".join(f"{r[0]}-01-01,{_num(r[1])}" for r in t["rows"])
            finance.import_csv(db, user, name=spec["name"], text=text, unit=spec["unit"], source_label=t["source"][:500],
                               source_url=t.get("source_url", ""), category=spec["category"], date_col="date", value_col="value",
                               license_note=(lic.license if lic else ""))
            report["series"] += 1

    if fetch_series:
        for s in kit.get("series", []):
            try:
                finance.import_series(db, user, settings, SeriesImportIn(category=s["category"], **s["params"]))
                report["series"] += 1
            except Exception as exc:  # noqa: BLE001 — serie già presente o fonte non raggiungibile: si segnala e si prosegue
                db.rollback()
                report["warnings"].append(f"Serie «{s['label']}»: {exc}")

    activity.record(db, user=user, actor="system", action="research_kit.create", entity_type="project", entity_id=p.id,
                    summary=f"Creato il progetto di ricerca «{kit['title']}»")
    db.commit()
    log.info("Kit %s → progetto %s: %s", kit_id, p.id, report)
    return {"project_id": p.id, "skipped": False, **report}
