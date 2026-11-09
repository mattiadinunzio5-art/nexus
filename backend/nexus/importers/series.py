"""Serie economiche nella Biblioteca: World Bank (tutti i paesi), OWID (Maddison, popolazione, speranza di vita),
Eurostat (UE), BCE. Passano dal servizio finance.import_series: stesse validazioni, fonte e licenza dei connettori.
I buchi restano buchi: nessuna interpolazione.
"""

from __future__ import annotations

import csv
import io
import json

from sqlalchemy import select

from ..api.schemas_finance import SeriesImportIn
from ..core.errors import NexusError
from ..finance import connectors
from ..models import Series
from ..services import finance
from .common import Run

# Indicatore World Bank -> categoria NEXUS
WB_INDICATORS = {
    "NY.GDP.MKTP.CD": "gdp", "NY.GDP.PCAP.CD": "gdp", "NY.GDP.MKTP.KD.ZG": "gdp", "FP.CPI.TOTL.ZG": "inflation",
    "GC.DOD.TOTL.GD.ZS": "public_debt", "SL.UEM.TOTL.ZS": "unemployment", "NE.RSB.GNFS.ZS": "trade_balance",
    "BN.CAB.XOKA.GD.ZS": "trade_balance", "NE.EXP.GNFS.ZS": "trade_balance", "NE.IMP.GNFS.ZS": "trade_balance",
    "FR.INR.LEND": "rates", "FR.INR.RINR": "rates", "PA.NUS.FCRF": "fx", "SP.POP.TOTL": "other", "BX.KLT.DINV.WD.GD.ZS": "other",
}
# Prima i paesi del G20, l'Italia, la Spagna e l'UE; poi tutti gli altri.
WB_FIRST = ["ITA", "ESP", "USA", "GBR", "DEU", "FRA", "JPN", "CHN", "IND", "BRA", "CAN", "AUS", "KOR", "MEX", "RUS", "SAU", "TUR",
            "ARG", "ZAF", "IDN", "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "GRC", "HUN", "IRL", "LVA", "LTU",
            "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "SWE"]

OWID_SLUGS = {"gdp-per-capita-maddison-project-database": "gdp", "population": "other", "life-expectancy": "other"}
MADDISON_LICENSE = ("Maddison Project Database, version 2023 by Jutta Bolt and Jan Luiten van Zanden — Creative Commons "
                    "Attribution 4.0 International (CC BY 4.0). https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023 "
                    "— tramite Our World in Data (CC BY).")

EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE"]
EUROSTAT = [
    ("gov_10dd_edpt1", {"na_item": "GD", "sector": "S13", "unit": "PC_GDP", "freq": "A"}, "public_debt"),
    ("une_rt_a", {"age": "Y15-74", "unit": "PC_ACT", "sex": "T", "freq": "A"}, "unemployment"),
    ("prc_hicp_aind", {"unit": "RCH_A_AVG", "coicop": "CP00", "freq": "A"}, "inflation"),
]
ECB = [
    ("EXR", "M.USD.EUR.SP00.A", "fx"), ("EXR", "M.GBP.EUR.SP00.A", "fx"), ("EXR", "M.JPY.EUR.SP00.A", "fx"),
    ("EXR", "M.CHF.EUR.SP00.A", "fx"), ("EXR", "M.CNY.EUR.SP00.A", "fx"),
]


def _fetcher(run: Run) -> connectors.HttpFetcher:
    # Cache lunga: le esecuzioni ripetute non riscaricano i dati.
    return connectors.HttpFetcher(connectors.Cache(run.settings.cache_dir, 24 * 30))


def _import(run: Run, origin: str, ext: str, data: SeriesImportIn, license_note: str | None = None, fatal_network: bool = False) -> None:
    key = f"{origin}:{ext}"
    if run.is_done(key) or not run.budget_left():
        return
    exists = run.db.scalar(select(Series.id).where(Series.owner_id == run.lib.id, Series.origin == origin, Series.external_id == ext))
    if exists:
        run.report.add("series", "skipped")
        run.mark(key)
        return
    run.tick()
    try:
        s = finance.import_series(run.db, run.lib, run.settings, data)
        s.origin, s.external_id = origin, ext
        if license_note:
            s.license_note = license_note
        run.db.commit()
        run.report.add("series", "created")
        run.report.add("observations", "created", s.observation_count)
    except NexusError as exc:
        msg = str(exc)
        if "non contiene valori" in msg or "Nessun dato" in msg or "non selezionano" in msg or "già importata" in msg:
            run.report.add("series", "skipped")  # la fonte non ha dati per questa combinazione: si dichiara, non si inventa
            run.db.rollback()
        else:
            run.error("series", key, msg)  # non segnata come fatta: --resume la riprova
            if fatal_network and "raggiungibile" in msg:
                raise
            run.sleep()
            return
    except Exception as exc:  # noqa: BLE001
        run.error("series", key, repr(exc))
        run.sleep()
        return
    run.mark(key)
    run.sleep()


def world_bank(run: Run) -> None:
    f = _fetcher(run)
    txt, _, _ = f.get("https://api.worldbank.org/v2/country", {"format": "json", "per_page": 400})
    rows = json.loads(txt)[1]
    countries = [r["id"] for r in rows if r.get("region", {}).get("id") not in (None, "NA", "")]
    ordered = [c for c in WB_FIRST if c in countries] + sorted(c for c in countries if c not in WB_FIRST)
    for iso in ordered:
        for ind, cat in WB_INDICATORS.items():
            if not run.budget_left():
                return
            _import(run, "world-bank", f"{ind}:{iso}", SeriesImportIn(connector="world-bank", indicator=ind, country=iso, category=cat))


def owid(run: Run) -> None:
    f = _fetcher(run)
    q = {"v": "1", "csvType": "full", "useColumnShortNames": "true"}
    for slug, cat in OWID_SLUGS.items():
        txt, _, _ = f.get(f"https://ourworldindata.org/grapher/{slug}.csv", q)
        reader = csv.DictReader(io.StringIO(txt))
        entities = sorted({r["Entity"] for r in reader if len(r.get("Code") or "") == 3})  # solo paesi (codice ISO a 3 lettere)
        lic = MADDISON_LICENSE if "maddison" in slug else None
        for ent in entities:
            if not run.budget_left():
                return
            _import(run, "owid", f"{slug}:{ent}", SeriesImportIn(connector="owid", slug=slug, entity=ent, category=cat), lic)


def eurostat(run: Run) -> None:
    for ds, filters, cat in EUROSTAT:
        for geo in EU27:
            if not run.budget_left():
                return
            fl = {**filters, "geo": geo}
            _import(run, "eurostat", f"{ds}:{geo}", SeriesImportIn(connector="eurostat", dataset=ds, filters=fl, category=cat))


def ecb(run: Run) -> None:
    for flow, key, cat in ECB:
        try:
            _import(run, "ecb", f"{flow}/{key}", SeriesImportIn(connector="ecb", dataset=flow, key=key, category=cat), fatal_network=True)
        except NexusError as exc:
            run.report.note(f"BCE non raggiungibile da questa rete: saltata ({exc}).")
            return


SOURCES = {"world-bank": world_bank, "owid": owid, "eurostat": eurostat, "ecb": ecb}
# Quota del limite complessivo assegnata a ciascuna fonte (le piccole non hanno bisogno di limite).
SHARE = {"world-bank": 0.72, "owid": 0.25, "eurostat": None, "ecb": None}


def run_series(run: Run, only: list[str] | None = None) -> None:
    total = run.limit
    for name, fn in SOURCES.items():
        if only and name not in only:
            continue
        run._processed = 0
        share = SHARE[name]
        run.limit = None if total is None else (max(1, int(total * share)) if share and not only else total)
        try:
            fn(run)
        except NexusError as exc:
            run.report.note(f"{name}: interrotto ({exc}).")
        except Exception as exc:  # noqa: BLE001
            run.report.note(f"{name}: interrotto per errore imprevisto ({exc!r}); vedi {run.log_path.name}.")
            run.error("series", name, repr(exc))
    run.limit = total
    run.report.note("FRED non importato: richiede una chiave API personale (non usata per la Biblioteca condivisa).")
    run.report.note("ISTAT non incluso nell'import automatico della Biblioteca: si aggiunge dalla pagina Financial Intelligence.")
