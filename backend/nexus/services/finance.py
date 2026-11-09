"""Gestione delle serie storiche e delle analisi."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..api.schemas_finance import CompareIn, Preset, SeriesDetailOut, SeriesImportIn, SeriesOut, SeriesUpdate
from ..core.config import Settings
from ..core.errors import ConfirmationRequiredError, ValidationFailedError
from ..database.base import utcnow
from ..finance import analytics, connectors
from ..models import ConnectorState, Observation, Series, User
from . import activity, credentials, quotas

PRESETS = [
    Preset(connector="world-bank", label="Inflazione, prezzi al consumo (% annua) — Italia", category="inflation", params={"indicator": "FP.CPI.TOTL.ZG", "country": "ITA"}),
    Preset(connector="world-bank", label="PIL (US$ correnti) — Italia", category="gdp", params={"indicator": "NY.GDP.MKTP.CD", "country": "ITA"}),
    Preset(connector="world-bank", label="Crescita del PIL (% annua) — Italia", category="gdp", params={"indicator": "NY.GDP.MKTP.KD.ZG", "country": "ITA"}),
    Preset(connector="world-bank", label="Disoccupazione (% forza lavoro, stima ILO) — Italia", category="unemployment", params={"indicator": "SL.UEM.TOTL.ZS", "country": "ITA"}),
    Preset(connector="eurostat", label="Debito pubblico (% PIL, definizione Maastricht) — Italia", category="public_debt", params={"dataset": "gov_10dd_edpt1", "filters": {"geo": "IT", "na_item": "GD", "sector": "S13", "unit": "PC_GDP", "freq": "A"}}),
    Preset(connector="eurostat", label="Tasso di disoccupazione 15-74 anni — Italia", category="unemployment", params={"dataset": "une_rt_a", "filters": {"geo": "IT", "age": "Y15-74", "sex": "T", "unit": "PC_ACT"}}),
    Preset(connector="world-bank", label="Saldo esterno beni e servizi (% PIL) — Italia", category="trade_balance", params={"indicator": "NE.RSB.GNFS.ZS", "country": "ITA"}),
    Preset(connector="eurostat", label="HICP, variazione media annua — Italia", category="inflation", params={"dataset": "prc_hicp_aind", "filters": {"geo": "IT", "coicop": "CP00", "unit": "RCH_A_AVG"}}),
    Preset(connector="ecb", label="Tasso BCE sulle operazioni di rifinanziamento principali — area euro", category="rates", params={"dataset": "FM", "key": "B.U2.EUR.4F.KR.MRR_FR.LEV"}),
    Preset(connector="ecb", label="Inflazione HICP area euro (% annua, BCE)", category="inflation", params={"dataset": "ICP", "key": "M.U2.N.000000.4.ANR"}),
    Preset(connector="owid", label="Inflazione dei prezzi al consumo — Italy (OWID)", category="inflation", params={"slug": "inflation-of-consumer-prices", "entity": "Italy"}),
    Preset(connector="fred", label="Tasso effettivo Fed Funds (FRED, richiede chiave)", category="rates", params={"series_id": "FEDFUNDS"}),
    Preset(connector="fred", label="Rendimento Treasury 10 anni (FRED, richiede chiave)", category="bonds", params={"series_id": "DGS10"}),
    Preset(connector="fred", label="CPI USA (FRED, richiede chiave)", category="inflation", params={"series_id": "CPIAUCSL"}),
]


def _fetcher(settings: Settings) -> connectors.HttpFetcher:
    return connectors.HttpFetcher(connectors.Cache(settings.cache_dir, settings.connector_cache_hours))


def _ext_id(data: SeriesImportIn) -> str:
    if data.connector == "world-bank":
        return f"{data.indicator}:{data.country}"
    if data.connector == "fred":
        return data.series_id or ""
    if data.connector == "owid":
        return f"{data.slug}:{data.entity}"
    if data.connector in ("ecb", "istat"):
        return f"{data.dataset}/{data.key}"
    return f"{data.dataset}?" + "&".join(f"{k}={v}" for k, v in sorted(data.filters.items()))


def _fetch(db: Session, user: User, settings: Settings, data: SeriesImportIn, force: bool) -> connectors.FetchResult:
    f = _fetcher(settings)
    try:
        if data.connector == "world-bank":
            return connectors.fetch_world_bank(f, data.indicator.strip(), data.country.strip(), force)
        if data.connector == "fred":
            key, _ = credentials.get_secret(db, user, settings, "fred")
            return connectors.fetch_fred(f, data.series_id.strip(), key, force)
        if data.connector == "owid":
            return connectors.fetch_owid(f, data.slug.strip(), data.entity.strip(), force)
        if data.connector == "ecb":
            return connectors.fetch_ecb(f, data.dataset.strip(), data.key.strip(), force)
        if data.connector == "istat":
            return connectors.fetch_istat(f, data.dataset.strip(), data.key.strip(), force)
        return connectors.fetch_eurostat(f, data.dataset.strip(), data.filters, force)
    except connectors.ConnectorError as exc:
        _record_state(db, data.connector, "unreachable" if "raggiungibile" in str(exc) else "degraded", str(exc))
        raise ValidationFailedError(str(exc)) from exc


def _record_state(db: Session, connector_id: str, status: str, error: str | None) -> None:
    st = db.get(ConnectorState, connector_id) or ConnectorState(connector_id=connector_id)
    st.last_checked_at, st.last_status, st.last_error = utcnow(), status, error
    st.last_http_status = None if error else 200
    db.add(st)
    db.commit()


def _apply(s: Series, res: connectors.FetchResult) -> None:
    s.unit, s.frequency, s.source_label, s.source_url = res.unit, res.frequency, res.source_label, res.source_url
    s.license_note, s.source_last_updated, s.description = res.license_note, res.source_last_updated, res.description
    s.retrieved_at, s.from_cache = res.retrieved_at, res.from_cache
    s.country = s.country or res.country
    s.observations = [Observation(date=d, value=v) for d, v in connectors.trim_coverage(sorted(res.observations))]
    _stats(s)


def _stats(s: Series) -> None:
    obs = s.observations
    valid = [o for o in obs if o.value is not None]
    s.observation_count = len(obs)
    s.missing_count = len(obs) - len(valid)
    s.start_date = valid[0].date if valid else None
    s.end_date = valid[-1].date if valid else None


def import_series(db: Session, user: User, settings: Settings, data: SeriesImportIn,
                  prefetched: connectors.FetchResult | None = None) -> Series:
    quotas.check(db, user, "series")
    ext = _ext_id(data)
    if db.scalar(select(Series).where(Series.owner_id == user.id, Series.connector == data.connector, Series.source_series_id == ext)):
        raise ValidationFailedError("Serie già importata: usa «Aggiorna» per riscaricarla.")
    res = prefetched or _fetch(db, user, settings, data, force=False)
    if not any(v is not None for _, v in res.observations):
        raise ValidationFailedError("La fonte non contiene valori per questa selezione.")
    s = Series(owner_id=user.id, name=res.name[:300], category=data.category, connector=data.connector, source_series_id=ext,
               params=data.model_dump(exclude={"category"}))
    _apply(s, res)
    db.add(s)
    db.flush()
    activity.record(db, user=user, actor="user", action="series.import", entity_type="series", entity_id=s.id,
                    summary=f"Importata la serie «{s.name}» da {data.connector} ({s.observation_count} osservazioni"
                    + (", dalla cache" if res.from_cache else "") + ")")
    db.commit()
    _record_state(db, data.connector, "reachable", None) if not res.from_cache else None
    db.refresh(s)
    return s


def import_csv(
    db: Session, user: User, *, name: str, text: str, unit: str, source_label: str, source_url: str, category: str,
    date_col: str | None, value_col: str | None, license_note: str = "", is_demo: bool = False,
) -> tuple[Series, list[str]]:
    quotas.check(db, user, "series")
    if not source_label.strip():
        raise ValidationFailedError("Indica la fonte dei dati: è obbligatoria per ogni serie.")
    try:
        obs, freq, warnings = connectors.parse_user_csv(text, date_col, value_col)
    except connectors.ConnectorError as exc:
        raise ValidationFailedError(str(exc)) from exc
    s = Series(owner_id=user.id, name=name, category=category, connector="upload", source_series_id="", source_label=source_label,
               source_url=source_url, license_note=license_note, unit=unit, frequency=freq, retrieved_at=utcnow(), is_demo=is_demo, params={})
    s.observations = [Observation(date=d, value=v) for d, v in obs]
    _stats(s)
    db.add(s)
    db.flush()
    activity.record(db, user=user, actor="user", action="series.upload", entity_type="series", entity_id=s.id,
                    summary=f"Caricata la serie «{name}» da CSV ({len(obs)} osservazioni)" + (" (DEMO)" if is_demo else ""))
    db.commit()
    db.refresh(s)
    return s, warnings


def refresh(db: Session, user: User, settings: Settings, series_id: int) -> Series:
    s = get_series(db, user, series_id, own=True)
    if s.connector == "upload":
        raise ValidationFailedError("Le serie caricate da CSV non hanno una fonte da cui aggiornarsi.")
    data = SeriesImportIn(category=s.category, **s.params)
    res = _fetch(db, user, settings, data, force=True)
    # Le vecchie osservazioni vanno eliminate prima di inserire le nuove (vincolo univoco serie+data).
    s.observations.clear()
    db.flush()
    _apply(s, res)
    db.flush()
    from . import alerts

    fired = alerts.evaluate(db, s)
    activity.record(db, user=user, actor="user", action="series.refresh", entity_type="series", entity_id=s.id,
                    summary=f"Aggiornata la serie «{s.name}»" + (" (fonte offline: usata la cache)" if res.from_cache else "")
                    + (f" — {fired} avvisi scattati" if fired else ""))
    db.commit()
    db.refresh(s)
    return s


def list_series(db: Session, user: User, category: str | None = None, q: str | None = None, limit: int = 300,
                offset: int = 0, origin: str | None = None) -> list[Series]:
    from ..core import library

    stmt = select(Series).where(Series.owner_id.in_(library.visible_owner_ids(db, user)))
    if origin == "mine":
        stmt = stmt.where(Series.owner_id == user.id)
    elif origin == "library":
        stmt = stmt.where(Series.owner_id != user.id)
    if category:
        stmt = stmt.where(Series.category == category)
    if q:
        like = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        stmt = stmt.where(or_(Series.name.ilike(like, escape="\\"), Series.country.ilike(like, escape="\\")))
    # Prima le serie dell'utente, poi quelle della Biblioteca.
    stmt = stmt.order_by((Series.owner_id != user.id), Series.name, Series.id)
    return list(db.scalars(stmt.offset(offset).limit(limit)))


def get_series(db: Session, user: User, series_id: int, own: bool = False) -> Series:
    from ..core import library

    return library.access(db, user, db.get(Series, series_id), own, "Serie non trovata.")


def to_out(db: Session, s: Series, detail: bool = False) -> SeriesOut | SeriesDetailOut:
    last = db.scalar(
        select(Observation).where(Observation.series_id == s.id, Observation.value.is_not(None)).order_by(Observation.date.desc()).limit(1)
    )
    from ..core import library

    base = SeriesOut.model_validate(s).model_dump()
    base["library"] = library.is_library(db, s.owner_id)
    base.update(last_value=last.value if last else None, last_date=last.date if last else None)
    if detail:
        base["observations"] = [{"date": o.date, "value": o.value} for o in s.observations]
        return SeriesDetailOut(**base)
    return SeriesOut(**base)


def update_series(db: Session, user: User, series_id: int, data: SeriesUpdate) -> Series:
    s = get_series(db, user, series_id, own=True)
    for k, v in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


def delete_series(db: Session, user: User, series_id: int, confirm: bool) -> None:
    s = get_series(db, user, series_id, own=True)
    if not confirm:
        raise ConfirmationRequiredError("Eliminare una serie richiede conferma (confirm=true).")
    db.delete(s)
    activity.record(db, user=user, actor="user", action="series.delete", entity_type="series", entity_id=series_id,
                    summary=f"Eliminata la serie «{s.name}»")
    db.commit()


LEVEL_CATEGORIES = {"stocks", "indices", "commodities", "precious_metals", "fx", "crypto", "gdp"}


def as_input(s: Series) -> analytics.SeriesInput:
    return analytics.SeriesInput(s.id, s.name, s.frequency, s.unit, [(o.date, o.value) for o in s.observations])


def analyze(db: Session, user: User, series_id: int, ma: list[int], return_kind: str, metrics: str | None) -> dict:
    s = get_series(db, user, series_id)
    # Rendimenti e drawdown hanno senso per livelli (prezzi, indici); per tassi e percentuali
    # si usano variazioni assolute. La scelta è dichiarata nel risultato e modificabile.
    level = metrics == "levels" if metrics else s.category in LEVEL_CATEGORIES
    try:
        res = analytics.analyze(as_input(s), ma, return_kind, level_metrics=level)
    except analytics.AnalysisError as exc:
        raise ValidationFailedError(str(exc)) from exc
    res["metrics_basis"] = "levels" if level else "rates"
    res["source"] = {"label": s.source_label, "url": s.source_url, "unit": s.unit, "frequency": s.frequency,
                     "last_updated": s.source_last_updated, "retrieved_at": s.retrieved_at.isoformat() if s.retrieved_at else None}
    return res


def compare(db: Session, user: User, data: CompareIn) -> dict:
    series = [get_series(db, user, i) for i in data.series_ids]
    try:
        res = analytics.compare([as_input(s) for s in series], data.target_frequency, data.method, data.mode)
    except analytics.AnalysisError as exc:
        raise ValidationFailedError(str(exc)) from exc
    res["series"] = [{"id": s.id, "name": s.name, "unit": s.unit, "frequency": s.frequency, "source": s.source_label} for s in series]
    return res
