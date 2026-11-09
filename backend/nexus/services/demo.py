"""Demo pubblica senza account: «La Grande Depressione 1929–1933».

Un unico utente dimostrativo, in sola lettura, condiviso da tutti i visitatori.
Chi preme «Prova la demo» riceve un token firmato (``demo.<scadenza>.<firma>``)
valido poche ore; il backend lo riconosce senza passare da Supabase.

Contenuti: eventi storici documentati con fonti bibliografiche reali e serie
storiche ufficiali (FRED / NBER Macrohistory Database) scaricate il giorno
indicato in ``demo_series.json``. Nulla è inventato: dove una fonte non è stata
controllata sul registro resta «non verificata», come per qualunque utente.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..database.base import utcnow
from ..models import Observation, Project, Series, User

LANGS = ("it", "en")
DEMO_EMAIL = "demo@nexus-demo.invalid"
DEMO_EXTERNAL_ID = "nexus-public-demo"
DEMO_PROJECT_TITLE = "[DEMO] La Grande Depressione 1929–1933"
DEMO_PROJECT_TITLE_EN = "[DEMO] The Great Depression 1929–1933"
TOKEN_PREFIX = "demo."
TOKEN_HOURS = 8
# Richieste di sola elaborazione consentite anche in demo (non salvano nulla).
DEMO_ALLOWED_WRITES = {"/api/finance/compare", "/api/auth/logout"}
READ_ONLY_MESSAGE = "Questa è la demo in sola lettura: crea un account gratuito per salvare e modificare i tuoi progetti."
READ_ONLY_MESSAGE_EN = "This is the read-only demo: create a free account to save and edit your own projects."


def _ids(lang: str) -> tuple[str, str]:
    """(external_id, email) dell'utente demo per lingua; l'italiano mantiene gli identificativi originali."""
    if lang == "en":
        return DEMO_EXTERNAL_ID + "-en", "demo-en@nexus-demo.invalid"
    return DEMO_EXTERNAL_ID, DEMO_EMAIL

_lock = threading.Lock()


# --- Token ---------------------------------------------------------------------------------


def _key(settings: Settings) -> bytes:
    from ..security.secrets import _key as secret_key

    return hashlib.sha256(b"nexus-demo|" + secret_key(settings)).digest()


def _sign(settings: Settings, payload: str) -> str:
    sig = hmac.new(_key(settings), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def make_token(settings: Settings, now: float | None = None, lang: str = "it") -> tuple[str, datetime]:
    lang = lang if lang in LANGS else "it"
    exp = int((now or time.time()) + TOKEN_HOURS * 3600)
    payload = f"{lang}.{exp}"
    return f"{TOKEN_PREFIX}{payload}.{_sign(settings, payload)}", datetime.fromtimestamp(exp, UTC)


def is_demo_token(token: str | None) -> bool:
    return bool(token) and token.startswith(TOKEN_PREFIX)


def check_token(settings: Settings, token: str) -> str:
    """Verifica firma e scadenza; restituisce la lingua della demo."""
    from .auth import AuthError

    try:
        lang, exp_s, sig = token[len(TOKEN_PREFIX):].split(".", 2)
        exp = int(exp_s)
    except ValueError as exc:
        raise AuthError("Sessione demo non valida: riapri la demo.") from exc
    if lang not in LANGS or not hmac.compare_digest(sig, _sign(settings, f"{lang}.{exp_s}")):
        raise AuthError("Sessione demo non valida: riapri la demo.")
    if exp < time.time():
        raise AuthError("La sessione demo è scaduta: riapri la demo.")
    return lang


def is_demo_user(user: User) -> bool:
    return bool(user.external_id) and user.external_id.startswith(DEMO_EXTERNAL_ID)


def demo_user(db: Session, lang: str = "it") -> User | None:
    return db.scalar(select(User).where(User.external_id == _ids(lang)[0]))


# --- Contenuti -----------------------------------------------------------------------------

S_GALBRAITH, S_FRIEDMAN, S_KINDLEBERGER, S_EICHENGREEN, S_BERNANKE, S_TONIOLO = range(6)

SOURCES = [
    dict(source_type="book", title="The Great Crash, 1929", authors=["John Kenneth Galbraith"], year=1955, publisher="Houghton Mifflin"),
    dict(source_type="book", title="A Monetary History of the United States, 1867–1960", authors=["Milton Friedman", "Anna J. Schwartz"],
         year=1963, publisher="Princeton University Press"),
    dict(source_type="book", title="The World in Depression, 1929–1939", authors=["Charles P. Kindleberger"], year=1973,
         publisher="University of California Press"),
    dict(source_type="book", title="Golden Fetters: The Gold Standard and the Great Depression, 1919–1939", authors=["Barry Eichengreen"],
         year=1992, publisher="Oxford University Press"),
    dict(source_type="article", title="Nonmonetary Effects of the Financial Crisis in the Propagation of the Great Depression",
         authors=["Ben S. Bernanke"], year=1983, container="American Economic Review, 73(3)", pages="257–276"),
    dict(source_type="book", title="L'economia dell'Italia fascista", authors=["Gianni Toniolo"], year=1980, publisher="Laterza"),
]
# Fonti i cui dati bibliografici sono stati confrontati con un catalogo pubblico (Open Library).
CATALOGUE_CHECKED = {S_GALBRAITH, S_FRIEDMAN, S_KINDLEBERGER, S_EICHENGREEN, S_TONIOLO}

EVENTS = [
    dict(key="crash", title="Crollo di Wall Street", start_year=1929, start_month=10, start_day=24, end_year=1929, end_month=10, end_day=29,
         region="Nord America", countries=["Stati Uniti"], categories=["financial_crisis"],
         description="Tra il «giovedì nero» (24 ottobre) e il «martedì nero» (29 ottobre) la Borsa di New York subisce le cadute più gravi "
                     "della sua storia fino ad allora, dopo il massimo del Dow Jones del 3 settembre 1929.",
         causes="Forte rialzo speculativo del 1928–29, ampio ricorso agli acquisti a margine (broker loans), politica monetaria più restrittiva dal 1928.",
         consequences="Distruzione di ricchezza e di fiducia; il crollo precede, ma da solo non spiega, la profondità della depressione successiva.",
         institutions=["New York Stock Exchange"], sources=[S_GALBRAITH, S_KINDLEBERGER]),
    dict(key="tariff", title="Tariffa Smoot-Hawley", start_year=1930, start_month=6, start_day=17, region="Nord America", countries=["Stati Uniti"],
         categories=["economic"], description="Il presidente Hoover firma il Tariff Act del 1930, che innalza i dazi su migliaia di prodotti importati.",
         consequences="Ritorsioni commerciali di altri paesi e contrazione del commercio internazionale negli anni successivi.",
         people=["Herbert Hoover", "Reed Smoot", "Willis C. Hawley"], sources=[S_KINDLEBERGER]),
    dict(key="banks1930", title="Prima ondata di panici bancari negli Stati Uniti", start_year=1930, start_month=11, end_year=1930, end_month=12,
         region="Nord America", countries=["Stati Uniti"], categories=["banking", "financial_crisis"],
         description="Ondata di fallimenti bancari nell'autunno 1930; l'11 dicembre chiude la Bank of United States di New York.",
         consequences="Secondo Friedman e Schwartz è l'inizio della contrazione monetaria che trasforma la recessione in Grande Depressione.",
         institutions=["Bank of United States", "Federal Reserve"], sources=[S_FRIEDMAN]),
    dict(key="creditanstalt", title="Crisi della Creditanstalt", start_year=1931, start_month=5, start_day=11, region="Europa", countries=["Austria"],
         categories=["banking", "financial_crisis"], description="La principale banca austriaca rende note perdite gravissime: è l'inizio della crisi finanziaria europea del 1931.",
         consequences="Il panico si estende alla Germania e mette sotto pressione la sterlina.", institutions=["Creditanstalt"],
         sources=[S_KINDLEBERGER, S_EICHENGREEN]),
    dict(key="moratorium", title="Moratoria Hoover", start_year=1931, start_month=6, start_day=20, region="Internazionale",
         countries=["Stati Uniti", "Germania"], categories=["monetary", "war_geopolitics"],
         description="Proposta di sospendere per un anno i pagamenti dei debiti di guerra e delle riparazioni tra governi.",
         people=["Herbert Hoover"], sources=[S_KINDLEBERGER]),
    dict(key="sterling", title="Il Regno Unito abbandona il gold standard", start_year=1931, start_month=9, start_day=21, region="Europa",
         countries=["Regno Unito"], categories=["monetary"], description="Dopo settimane di deflussi di riserve, il Regno Unito sospende la convertibilità della sterlina in oro.",
         consequences="Molti paesi seguono la sterlina; chi esce prima dall'oro tende a riprendersi prima (Eichengreen).",
         institutions=["Bank of England"], sources=[S_EICHENGREEN]),
    dict(key="fedrate", title="La Federal Reserve alza il tasso di sconto", start_year=1931, start_month=10, region="Nord America",
         countries=["Stati Uniti"], categories=["monetary"],
         description="Per difendere la parità aurea del dollaro dopo l'uscita della sterlina, la Federal Reserve Bank di New York alza il tasso di sconto "
                     "dall'1,5% al 3,5% in due passaggi (ottobre 1931).",
         consequences="Stretta monetaria in piena depressione, con nuove ondate di fallimenti bancari.",
         institutions=["Federal Reserve Bank of New York"], sources=[S_FRIEDMAN, S_EICHENGREEN]),
    dict(key="rfc", title="Nasce la Reconstruction Finance Corporation", start_year=1932, start_month=1, start_day=22, region="Nord America",
         countries=["Stati Uniti"], categories=["banking"], description="Agenzia federale creata per concedere prestiti a banche, ferrovie e altre imprese in difficoltà.",
         institutions=["Reconstruction Finance Corporation"], sources=[S_FRIEDMAN]),
    dict(key="bottom", title="Minimo del Dow Jones", start_year=1932, start_month=7, start_day=8, region="Nord America", countries=["Stati Uniti"],
         categories=["financial_crisis"], description="Il Dow Jones Industrial Average chiude a 41,22 punti, circa l'89% sotto il massimo del settembre 1929.",
         sources=[S_GALBRAITH]),
    dict(key="iri", title="Nasce l'IRI", start_year=1933, start_month=1, start_day=23, region="Europa", countries=["Italia"], categories=["banking", "industrial"],
         description="Il governo istituisce l'Istituto per la Ricostruzione Industriale, che rileva le partecipazioni industriali delle grandi banche miste in crisi.",
         consequences="Lo Stato diventa il principale azionista dell'industria e della banca italiana.",
         institutions=["IRI", "Banca Commerciale Italiana", "Credito Italiano", "Banco di Roma"], people=["Alberto Beneduce"], sources=[S_TONIOLO]),
    dict(key="holiday", title="Bank holiday ed Emergency Banking Act", start_year=1933, start_month=3, start_day=6, end_year=1933, end_month=3, end_day=9,
         region="Nord America", countries=["Stati Uniti"], categories=["banking"],
         description="Due giorni dopo l'insediamento, Roosevelt chiude tutte le banche del paese; il 9 marzo il Congresso approva l'Emergency Banking Act "
                     "e le banche solide riaprono nei giorni seguenti.",
         people=["Franklin D. Roosevelt"], sources=[S_FRIEDMAN]),
    dict(key="glass", title="Banking Act del 1933 (Glass-Steagall)", start_year=1933, start_month=6, start_day=16, region="Nord America",
         countries=["Stati Uniti"], categories=["banking"],
         description="Separa l'attività bancaria commerciale da quella d'investimento e istituisce l'assicurazione federale dei depositi (FDIC).",
         people=["Carter Glass", "Henry B. Steagall"], institutions=["FDIC"], sources=[S_FRIEDMAN]),
    dict(key="goldact", title="Gold Reserve Act", start_year=1934, start_month=1, start_day=30, region="Nord America", countries=["Stati Uniti"],
         categories=["monetary"], description="L'oro monetario passa al Tesoro; il giorno dopo il prezzo dell'oro viene fissato a 35 dollari l'oncia "
                                              "(svalutazione del dollaro rispetto ai 20,67 dollari precedenti).",
         people=["Franklin D. Roosevelt"], sources=[S_FRIEDMAN, S_EICHENGREEN]),
    dict(key="bank1936", title="Legge bancaria italiana", start_year=1936, start_month=3, start_day=12, region="Europa", countries=["Italia"],
         categories=["banking"], description="Riforma del sistema creditizio: separazione tra credito a breve e a lungo termine, vigilanza affidata a un Ispettorato "
                     "presieduto dal Governatore; la Banca d'Italia diventa istituto di diritto pubblico.",
         institutions=["Banca d'Italia"], sources=[S_TONIOLO]),
]

# (evento origine, evento destinazione, relazione, fonte, nota)
LINKS = [
    ("crash", "banks1930", "preceded", S_FRIEDMAN, "Il crollo di borsa precede la prima ondata di panici bancari."),
    ("creditanstalt", "sterling", "influenced", S_KINDLEBERGER, "La crisi bancaria austro-tedesca si trasmette alla sterlina."),
    ("sterling", "fedrate", "caused", S_FRIEDMAN, "La Fed alza i tassi per difendere il dollaro dopo l'uscita della sterlina dall'oro."),
    ("holiday", "glass", "preceded", S_FRIEDMAN, "Dalla chiusura delle banche alla riforma del sistema bancario."),
    ("iri", "bank1936", "preceded", S_TONIOLO, "Il salvataggio delle banche miste porta alla riforma bancaria del 1936."),
]

# (evento, anno da cui è nota, tipo, fonte, contenuto) — per la Time Machine «senza senno di poi».
KNOWLEDGE = [
    ("crash", 1929, "contemporary", None, "Nei giorni del crollo molti commentatori lo considerano una correzione di un mercato sopravvalutato."),
    ("crash", 1955, "historiography", S_GALBRAITH, "Galbraith ricostruisce la speculazione del 1928–29 e la fragilità finanziaria che la accompagnava."),
    ("banks1930", 1963, "historiography", S_FRIEDMAN, "Friedman e Schwartz attribuiscono la gravità della depressione alla contrazione dell'offerta di moneta."),
    ("banks1930", 1983, "historiography", S_BERNANKE, "Bernanke aggiunge il canale del credito: i fallimenti bancari distruggono informazione e capacità di prestito."),
    ("sterling", 1992, "historiography", S_EICHENGREEN, "Eichengreen: il gold standard trasmette la crisi; i paesi che lo abbandonano prima si riprendono prima."),
    ("creditanstalt", 1973, "historiography", S_KINDLEBERGER, "Kindleberger: la crisi si aggrava perché nessun paese assume il ruolo di prestatore di ultima istanza internazionale."),
]

SERIES = [
    dict(id="M1109BUSM293NNBR", name="Dow Jones Industrial Average (media mensile)", category="indices", unit="Dollari per azione",
         label="NBER Macrohistory Database, via FRED (Federal Reserve Bank of St. Louis)",
         description="Indice mensile basato sui prezzi di chiusura giornalieri della Borsa di New York; 30 titoli da ottobre 1928. "
                     "Valori mensili: i minimi giornalieri (es. 41,22 l'8 luglio 1932) sono più bassi."),
    dict(id="INDPRO", name="Produzione industriale, Stati Uniti", category="other", unit="Indice 2017=100 (dest.)",
         label="Board of Governors of the Federal Reserve System, via FRED", description="Indice della produzione industriale, destagionalizzato."),
    dict(id="CPIAUCNS", name="Indice dei prezzi al consumo, Stati Uniti", category="inflation", unit="Indice 1982-84=100",
         label="U.S. Bureau of Labor Statistics, via FRED", description="CPI per tutti i consumatori urbani, non destagionalizzato: mostra la deflazione 1930–33."),
    dict(id="M13009USM156NNBR", name="Tasso di sconto, Federal Reserve Bank of New York", category="rates", unit="Percentuale",
         label="NBER Macrohistory Database, via FRED", description="Media ponderata per giorni dei tassi di sconto in vigore nel mese."),
    dict(id="M0892AUSM156SNBR", name="Tasso di disoccupazione, Stati Uniti (stime NICB)", category="unemployment", unit="Percentuale (dest.)",
         label="National Industrial Conference Board, NBER Macrohistory Database, via FRED",
         description="Stime contemporanee del National Industrial Conference Board, destagionalizzate (1929–1942). Non sono direttamente "
                     "confrontabili con le serie BLS moderne: per il 1929 risultano più basse di altre ricostruzioni (es. Lebergott, circa 3% annuo)."),
]


# --- English version (public demo in English: ?demo=en) --------------------------------------------

REGIONS_EN = {"Nord America": "North America", "Europa": "Europe", "Internazionale": "International"}
COUNTRIES_EN = {"Stati Uniti": "United States", "Austria": "Austria", "Germania": "Germany", "Regno Unito": "United Kingdom", "Italia": "Italy"}

EVENTS_EN = {
    "crash": dict(title="Wall Street Crash",
                  description="Between “Black Thursday” (24 October) and “Black Tuesday” (29 October) the New York Stock Exchange suffers the worst falls "
                              "in its history up to then, after the Dow Jones peak of 3 September 1929.",
                  causes="A strong speculative boom in 1928–29, heavy use of margin buying (broker loans), tighter monetary policy from 1928.",
                  consequences="Destruction of wealth and confidence; the crash precedes, but does not by itself explain, the depth of the depression that followed."),
    "tariff": dict(title="Smoot-Hawley Tariff", description="President Hoover signs the Tariff Act of 1930, raising duties on thousands of imported goods.",
                   consequences="Trade retaliation by other countries and a contraction of international trade in the following years."),
    "banks1930": dict(title="First wave of US banking panics", description="A wave of bank failures in autumn 1930; on 11 December the Bank of United States in New York closes.",
                      consequences="According to Friedman and Schwartz, the start of the monetary contraction that turned the recession into the Great Depression."),
    "creditanstalt": dict(title="Creditanstalt crisis", description="Austria's largest bank discloses massive losses: the start of the European financial crisis of 1931.",
                          consequences="Panic spreads to Germany and puts sterling under pressure."),
    "moratorium": dict(title="Hoover Moratorium", description="Proposal to suspend for one year all intergovernmental payments of war debts and reparations."),
    "sterling": dict(title="Britain leaves the gold standard", description="After weeks of reserve outflows, Britain suspends the convertibility of sterling into gold.",
                     consequences="Many countries follow sterling; those that leave gold earlier tend to recover earlier (Eichengreen)."),
    "fedrate": dict(title="The Federal Reserve raises the discount rate",
                    description="To defend the dollar's gold parity after sterling's exit, the Federal Reserve Bank of New York raises its discount rate "
                                "from 1.5% to 3.5% in two steps (October 1931).",
                    consequences="Monetary tightening in the middle of the depression, followed by new waves of bank failures."),
    "rfc": dict(title="Reconstruction Finance Corporation founded", description="Federal agency created to lend to banks, railroads and other businesses in distress."),
    "bottom": dict(title="Dow Jones hits bottom", description="The Dow Jones Industrial Average closes at 41.22, about 89% below its September 1929 peak."),
    "iri": dict(title="Italy creates IRI", description="The government sets up the Istituto per la Ricostruzione Industriale, which takes over the industrial holdings of the troubled universal banks.",
                consequences="The Italian state becomes the main shareholder of the country's industry and banking."),
    "holiday": dict(title="Bank holiday and Emergency Banking Act",
                    description="Two days after his inauguration, Roosevelt closes every bank in the country; on 9 March Congress passes the Emergency Banking Act "
                                "and sound banks reopen in the following days."),
    "glass": dict(title="Banking Act of 1933 (Glass-Steagall)", description="Separates commercial from investment banking and creates federal deposit insurance (FDIC)."),
    "goldact": dict(title="Gold Reserve Act", description="Monetary gold is transferred to the Treasury; the next day the gold price is set at $35 an ounce "
                                                          "(a devaluation of the dollar from the previous $20.67)."),
    "bank1936": dict(title="Italian Banking Law", description="Reform of the credit system: separation of short-term and long-term lending, supervision entrusted to an "
                                                               "Inspectorate chaired by the Governor; the Bank of Italy becomes a public-law institution."),
}

LINK_NOTES_EN = [
    "The stock market crash precedes the first wave of banking panics.",
    "The Austro-German banking crisis spreads to sterling.",
    "The Fed raises rates to defend the dollar after sterling leaves gold.",
    "From the bank closures to the reform of the banking system.",
    "The rescue of the universal banks leads to the banking reform of 1936.",
]

KNOWLEDGE_EN = [
    "In the days of the crash many commentators saw it as a correction of an overvalued market.",
    "Galbraith reconstructs the speculation of 1928–29 and the financial fragility that came with it.",
    "Friedman and Schwartz attribute the severity of the depression to the contraction of the money supply.",
    "Bernanke adds the credit channel: bank failures destroy information and lending capacity.",
    "Eichengreen: the gold standard transmits the crisis; countries that leave it earlier recover earlier.",
    "Kindleberger: the crisis deepens because no country acts as international lender of last resort.",
]

SERIES_EN = {
    "M1109BUSM293NNBR": dict(name="Dow Jones Industrial Average (monthly average)", unit="Dollars per share",
                             description="Monthly index based on daily closing prices of the New York Stock Exchange; 30 stocks from October 1928. "
                                         "Monthly values: daily lows (e.g. 41.22 on 8 July 1932) are lower."),
    "INDPRO": dict(name="Industrial production, United States", unit="Index 2017=100 (s.a.)", description="Industrial production index, seasonally adjusted."),
    "CPIAUCNS": dict(name="Consumer price index, United States", unit="Index 1982-84=100",
                     description="CPI for all urban consumers, not seasonally adjusted: shows the 1930–33 deflation."),
    "M13009USM156NNBR": dict(name="Discount rate, Federal Reserve Bank of New York", unit="Percent",
                             description="Average of the discount rates in force during the month, weighted by days."),
    "M0892AUSM156SNBR": dict(name="Unemployment rate, United States (NICB estimates)", unit="Percent (s.a.)",
                             description="Contemporary estimates by the National Industrial Conference Board, seasonally adjusted (1929–1942). Not directly "
                                         "comparable with modern BLS series: for 1929 they are lower than other reconstructions (e.g. Lebergott, about 3% annual)."),
}

TEXTS = {
    "it": dict(project=DEMO_PROJECT_TITLE,
               project_desc="Progetto dimostrativo: come la crisi di Wall Street del 1929 diventa una depressione mondiale. Eventi con fonti "
                            "bibliografiche, serie storiche ufficiali (FRED/NBER) e la Time Machine per leggere i fatti con ciò che si sapeva allora.",
               checked="Dati bibliografici confrontati con il catalogo Open Library (8 novembre 2026).",
               reliability="Fatto documentato nella letteratura indicata tra le fonti.", country="Stati Uniti", name="Visitatore demo"),
    "en": dict(project=DEMO_PROJECT_TITLE_EN,
               project_desc="Sample project: how the 1929 Wall Street crash became a worldwide depression. Events with bibliographic sources, "
                            "official historical series (FRED/NBER) and the Time Machine to read the facts with what was known at the time.",
               checked="Bibliographic data checked against the Open Library catalogue (8 November 2026).",
               reliability="Fact documented in the literature listed among the sources.", country="United States", name="Demo visitor"),
}


def _event(data: dict, lang: str) -> dict:
    d = dict(data)
    if lang == "en":
        d.update(EVENTS_EN[d["key"]])
        d["region"] = REGIONS_EN.get(d.get("region", ""), d.get("region", ""))
        d["countries"] = [COUNTRIES_EN.get(c, c) for c in d.get("countries", [])]
    return d


def _load_series() -> dict:
    return json.loads((Path(__file__).with_name("demo_series.json")).read_text())


def _seed(db: Session, settings: Settings, user: User, lang: str = "it") -> None:
    from ..api.schemas import ProjectCreate
    from ..api.schemas_history import EventIn, EventLinkIn, KnowledgeIn
    from ..api.schemas_research import SourceIn
    from ..finance.connectors import FRED_LICENSE
    from . import finance, history, projects, sources

    tx = TEXTS[lang]
    projects.create_project(db, user, ProjectCreate(title=tx["project"], description=tx["project_desc"]), is_demo=True)

    src_ids = []
    for i, data in enumerate(SOURCES):
        s = sources.create_source(db, user, SourceIn(**data), is_demo=True)
        if i in CATALOGUE_CHECKED:
            sources.verify_source(db, user, s.id, "user", tx["checked"])
        src_ids.append(s.id)

    events = {}
    for data in EVENTS:
        d = _event(data, lang)
        key, srcs = d.pop("key"), d.pop("sources")
        e = history.create_event(db, user, EventIn(**d, reliability="established", reliability_note=tx["reliability"]), is_demo=True)
        for si in srcs:
            history.link_source(db, user, e.id, src_ids[si], "", "")
        events[key] = e.id

    for i, (src, tgt, rel, si, note) in enumerate(LINKS):
        note = LINK_NOTES_EN[i] if lang == "en" else note
        history.link_events(db, user, events[src], EventLinkIn(target_event_id=events[tgt], relation_type=rel, provenance="sourced",
                                                              source_id=src_ids[si], evidence_note=note, confidence="high"))
    for i, (key, year, kind, si, content) in enumerate(KNOWLEDGE):
        content = KNOWLEDGE_EN[i] if lang == "en" else content
        history.add_knowledge(db, user, events[key], KnowledgeIn(content=content, known_since_year=year, kind=kind,
                                                                source_id=src_ids[si] if si is not None else None))

    bundle = _load_series()
    retrieved = datetime.fromisoformat(bundle["retrieved"]).replace(tzinfo=UTC)
    for meta in SERIES:
        m = {**meta, **SERIES_EN[meta["id"]]} if lang == "en" else meta
        s = Series(owner_id=user.id, name=m["name"], category=m["category"], country=tx["country"], connector="fred",
                   source_series_id=m["id"], source_label=f"{m['label']} — {'series' if lang == 'en' else 'serie'} {m['id']}",
                   source_url=f"https://fred.stlouisfed.org/series/{m['id']}", license_note=FRED_LICENSE, unit=m["unit"],
                   frequency="M", description=m["description"], retrieved_at=retrieved, is_demo=True,
                   params={"series_id": m["id"]})
        s.observations = [Observation(date=d, value=v) for d, v in bundle["series"][m["id"]]]
        finance._stats(s)
        db.add(s)
    db.commit()


def _run_discovery(database, settings: Settings, user_id: int) -> None:
    from . import discovery

    with database.session_factory() as db:
        user = db.get(User, user_id)
        try:
            s = discovery.create_session(db, user, settings, "autonomous", "")
        except Exception:  # noqa: BLE001 — la demo funziona anche senza risultati di discovery
            return
        sid = s.id
    discovery.run_in_background(database, settings, sid)


def ensure_demo(database, settings: Settings, lang: str = "it") -> int:
    """Crea (una sola volta per lingua) l'utente demo con i suoi contenuti; restituisce l'id dell'utente."""
    lang = lang if lang in LANGS else "it"
    external_id, email = _ids(lang)
    with _lock:
        with database.session_factory() as db:
            user = demo_user(db, lang)
            if user is None:
                user = User(email=email, display_name=TEXTS[lang]["name"], external_id=external_id, role="user",
                            plan="free", is_local=False, is_active=True)
                db.add(user)
                db.commit()
                db.refresh(user)
            uid = user.id
            seeded = db.scalar(select(Project.id).where(Project.owner_id == uid, Project.title == TEXTS[lang]["project"]))
            if seeded is None:
                _seed(db, settings, user, lang)
            user.last_login_at = utcnow()
            db.commit()
        if seeded is None:
            _run_discovery(database, settings, uid)
    return uid
