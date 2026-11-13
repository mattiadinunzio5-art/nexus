"""NEXUS Copyright & Data Policy: registro delle licenze delle fonti.

Le licenze valgono per fonte, non per singolo elemento: ogni elemento della Biblioteca
(serie, documento, evento/fonte) punta a una scheda di questo registro tramite ``license_id``.
Sul singolo elemento restano fonte originale, URL, data di acquisizione e note specifiche.

Ogni scheda riporta i nove campi della policy: fonte originale, URL, data di verifica,
licenza esatta, attribuzione obbligatoria, uso commerciale, redistribuzione, limiti
territoriali, modifiche effettuate da NEXUS. I testi sono stati controllati sulle pagine
ufficiali indicate in ``terms_url`` alla data ``verified_on``. Non costituiscono parere legale.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .locale import current_lang

POLICY_VERSION = "1.0"
POLICY_DATE = "2026-11-11"

# Valori ammessi per uso commerciale / redistribuzione.
YES, CONDITIONAL, NO = "yes", "conditional", "no"
# Stato della verifica della scheda.
VERIFIED, PER_ITEM = "verified", "per_item"


@dataclass(frozen=True)
class T:
    it: str
    en: str

    def get(self) -> str:
        return self.en if current_lang.get() == "en" else self.it


@dataclass(frozen=True)
class LicenseEntry:
    id: str
    name: str
    publisher: str
    homepage: str
    applies_to: T
    license: str
    license_url: str
    attribution: T
    commercial: str
    commercial_note: T
    redistribution: str
    redistribution_note: T
    territorial: T
    modifications: T
    terms_url: str
    verified_on: str
    status: str
    notes: T

    def as_dict(self) -> dict:
        out = {}
        for k, v in self.__dict__.items():
            out[k] = v.get() if isinstance(v, T) else v
        return out


NONE_TERRITORIAL = T("Nessuna limitazione territoriale indicata dalla fonte.", "No territorial restriction stated by the source.")

LICENSES: dict[str, LicenseEntry] = {e.id: e for e in [
    LicenseEntry(
        id="wikidata", name="Wikidata", publisher="Wikimedia Foundation", homepage="https://www.wikidata.org",
        applies_to=T("Biblioteca: eventi storici (date, paesi, cause, conseguenze), entità e relazioni del Knowledge Graph.",
                     "Library: historical events (dates, countries, causes, consequences), Knowledge Graph entities and relations."),
        license="Creative Commons CC0 1.0 Universal (Public Domain Dedication)",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        attribution=T("Non obbligatoria. NEXUS cita comunque ogni elemento: «Wikidata, <identificativo Q>», con link.",
                      "Not required. NEXUS still cites every item: “Wikidata, <Q identifier>”, with a link."),
        commercial=YES, commercial_note=T("Consentito senza condizioni.", "Allowed without conditions."),
        redistribution=YES, redistribution_note=T("Consentita senza condizioni.", "Allowed without conditions."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Selezione delle proprietà (date, paesi, luogo, «ha causa» P828, «ha effetto» P1542). Date riportate con la "
                        "precisione dichiarata da Wikidata; prima del 1583 solo l'anno (conversione di calendario). Iniziale del titolo "
                        "in maiuscolo. Nessun valore inventato o stimato.",
                        "Selection of properties (dates, countries, location, “has cause” P828, “has effect” P1542). Dates kept at the "
                        "precision stated by Wikidata; before 1583 only the year (calendar conversion). Title capitalised. No value "
                        "invented or estimated."),
        terms_url="https://www.wikidata.org/wiki/Wikidata:Licensing", verified_on=POLICY_DATE, status=VERIFIED,
        notes=T("Vale per i dati strutturati. Le descrizioni testuali degli eventi provengono da Wikipedia: vedi la scheda dedicata.",
                "Applies to structured data. Event text descriptions come from Wikipedia: see its own entry."),
    ),
    LicenseEntry(
        id="wikipedia", name="Wikipedia (English)", publisher="Wikimedia Foundation", homepage="https://en.wikipedia.org",
        applies_to=T("Biblioteca: brevi descrizioni degli eventi storici (estratto introduttivo della voce).",
                     "Library: short descriptions of historical events (introductory extract of the article)."),
        license="Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)",
        license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        attribution=T("Obbligatoria: titolo della voce, link alla voce e licenza CC BY-SA 4.0. NEXUS la riporta nella fonte di ogni evento.",
                      "Required: article title, link to the article and the CC BY-SA 4.0 licence. NEXUS shows it in each event's source."),
        commercial=YES, commercial_note=T("Consentito, con attribuzione e condivisione allo stesso modo.",
                                          "Allowed, with attribution and share-alike."),
        redistribution=CONDITIONAL,
        redistribution_note=T("Consentita con attribuzione; le versioni modificate degli estratti vanno rilasciate con la stessa licenza "
                              "CC BY-SA 4.0. La licenza non si estende ai dati e ai testi propri di NEXUS.",
                              "Allowed with attribution; modified versions of the extracts must be released under the same CC BY-SA 4.0 "
                              "licence. It does not extend to NEXUS's own data and texts."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Solo l'estratto introduttivo in testo semplice, come fornito dall'API di Wikipedia; tolte le parentesi vuote "
                        "lasciate dalla pronuncia rimossa. Testo non riscritto.",
                        "Introductory plain-text extract only, as returned by the Wikipedia API; empty brackets left by the removed "
                        "pronunciation are dropped. Text not rewritten."),
        terms_url="https://en.wikipedia.org/wiki/Wikipedia:Reusing_Wikipedia_content", verified_on=POLICY_DATE, status=VERIFIED,
        notes=T("", ""),
    ),
    LicenseEntry(
        id="world_bank_wdi", name="World Development Indicators", publisher="World Bank", homepage="https://data.worldbank.org",
        applies_to=T("Biblioteca: serie annuali per paese (PIL, inflazione, debito, disoccupazione, commercio, tassi, cambi, popolazione, IDE).",
                     "Library: annual country series (GDP, inflation, debt, unemployment, trade, rates, exchange rates, population, FDI)."),
        license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution=T("Obbligatoria: «World Bank, World Development Indicators», codice dell'indicatore e data di accesso; NEXUS indica "
                      "anche le fonti primarie dichiarate dalla Banca Mondiale (FMI, OCSE, ILO, ONU, istituti nazionali).",
                      "Required: “World Bank, World Development Indicators”, indicator code and access date; NEXUS also lists the "
                      "primary sources declared by the World Bank (IMF, OECD, ILO, UN, national offices)."),
        commercial=YES, commercial_note=T("Consentito con attribuzione (licenza del dataset nel World Bank Data Catalog).",
                                          "Allowed with attribution (dataset licence in the World Bank Data Catalog)."),
        redistribution=YES, redistribution_note=T("Consentita con attribuzione.", "Allowed with attribution."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Nessuna modifica dei valori. Gli anni mancanti restano vuoti (nessuna interpolazione).",
                        "Values unchanged. Missing years stay empty (no interpolation)."),
        terms_url="https://datacatalog.worldbank.org/search/dataset/0037712", verified_on=POLICY_DATE, status=VERIFIED,
        notes=T("Le condizioni generali del sito della Banca Mondiale (uso non commerciale) valgono solo per i materiali senza licenza "
                "specifica; il dataset WDI ha licenza CC BY 4.0.",
                "The World Bank website's general terms (non-commercial use) apply only to materials without a specific licence; "
                "the WDI dataset is licensed CC BY 4.0."),
    ),
    LicenseEntry(
        id="owid", name="Our World in Data", publisher="Global Change Data Lab", homepage="https://ourworldindata.org",
        applies_to=T("Biblioteca: popolazione e speranza di vita per paese (dati «with major processing by Our World in Data»).",
                     "Library: population and life expectancy by country (data “with major processing by Our World in Data”)."),
        license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution=T("Obbligatoria: Our World in Data e i fornitori originali indicati (es. HYDE, Gapminder, UN WPP, HMD).",
                      "Required: Our World in Data and the original providers listed (e.g. HYDE, Gapminder, UN WPP, HMD)."),
        commercial=YES, commercial_note=T("La licenza CC BY consente l'uso commerciale con attribuzione.",
                                          "The CC BY licence allows commercial use with attribution."),
        redistribution=YES, redistribution_note=T("Consentita con attribuzione a OWID e alle fonti originali.",
                                                  "Allowed with attribution to OWID and the original sources."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Nessuna modifica dei valori; esclusi gli aggregati regionali calcolati da OWID.",
                        "Values unchanged; regional aggregates computed by OWID are excluded."),
        terms_url="https://ourworldindata.org/faqs#can-i-use-or-reproduce-your-data", verified_on=POLICY_DATE, status=VERIFIED,
        notes=T("OWID avverte che i dati di terze parti restano soggetti alle licenze delle fonti originali: per un riuso esterno "
                "conviene verificarle.",
                "OWID notes that third-party data remain subject to the original sources' licences: check them before external reuse."),
    ),
    LicenseEntry(
        id="maddison", name="Maddison Project Database 2023", publisher="Groningen Growth and Development Centre (University of Groningen)",
        homepage="https://www.rug.nl/ggdc/historicaldevelopment/maddison/",
        applies_to=T("Biblioteca: PIL pro capite di lungo periodo per paese (tramite Our World in Data, «minor processing»).",
                     "Library: long-run GDP per capita by country (via Our World in Data, “minor processing”)."),
        license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution=T("Obbligatoria: Bolt, J. e van Zanden, J.L. (2024), «Maddison style estimates of the evolution of the world economy: "
                      "A new 2023 update», Journal of Economic Surveys, DOI 10.1111/joes.12618; più Our World in Data. Per grafici o "
                      "analisi su meno di 12 paesi vanno citati anche gli studi originali indicati nel database.",
                      "Required: Bolt, J. and van Zanden, J.L. (2024), “Maddison style estimates of the evolution of the world economy: "
                      "A new 2023 update”, Journal of Economic Surveys, DOI 10.1111/joes.12618; plus Our World in Data. For charts or "
                      "analyses of fewer than 12 countries, the original studies listed in the database must also be cited."),
        commercial=YES, commercial_note=T("Consentito con attribuzione.", "Allowed with attribution."),
        redistribution=YES, redistribution_note=T("Consentita con attribuzione.", "Allowed with attribution."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Nessuna modifica dei valori; gli anni senza stima restano vuoti.", "Values unchanged; years without an estimate stay empty."),
        terms_url="https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023",
        verified_on=POLICY_DATE, status=VERIFIED, notes=T("", ""),
    ),
    LicenseEntry(
        id="eurostat", name="Eurostat", publisher="European Commission — Eurostat", homepage="https://ec.europa.eu/eurostat",
        applies_to=T("Biblioteca: debito pubblico, disoccupazione e inflazione HICP dei 27 paesi UE.",
                     "Library: public debt, unemployment and HICP inflation for the 27 EU countries."),
        license="Creative Commons Attribution 4.0 International (CC BY 4.0) — Decisione della Commissione 2011/833/UE",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        attribution=T("Obbligatoria: «Fonte: Eurostat, dataset <codice>, <data di accesso>», indicando le eventuali modifiche.",
                      "Required: “Source: Eurostat, dataset <code>, <access date>”, stating any changes."),
        commercial=CONDITIONAL,
        commercial_note=T("Consentito per i dati dei paesi UE/EFTA/candidati (tutte le serie in Biblioteca sono UE-27). I dati di altri "
                          "paesi o di terze parti sono riutilizzabili solo per fini non commerciali.",
                          "Allowed for EU/EFTA/candidate-country data (all Library series are EU-27). Data on other countries or from "
                          "third parties may be reused for non-commercial purposes only."),
        redistribution=YES, redistribution_note=T("Consentita con attribuzione e indicazione delle modifiche.",
                                                  "Allowed with attribution and a statement of changes."),
        territorial=T("Le restrizioni riguardano i dati su paesi extra UE/EFTA/candidati e alcuni dati del commercio estero (Svizzera, "
                      "Liechtenstein, Austria a 8 cifre NC): non presenti in Biblioteca.",
                      "Restrictions concern data on non-EU/EFTA/candidate countries and some foreign-trade data (Switzerland, "
                      "Liechtenstein, Austria at 8-digit CN): not in the Library."),
        modifications=T("Nessuna modifica dei valori; selezione di unità e dimensioni indicate nella fonte di ogni serie.",
                        "Values unchanged; unit and dimension selection stated in each series' source."),
        terms_url="https://ec.europa.eu/eurostat/help/copyright-notice", verified_on=POLICY_DATE, status=VERIFIED, notes=T("", ""),
    ),
    LicenseEntry(
        id="ecb", name="ECB Data Portal", publisher="Banca Centrale Europea", homepage="https://data.ecb.europa.eu",
        applies_to=T("Biblioteca: tassi di cambio di riferimento dell'euro (USD, GBP, JPY, CHF, CNY), mensili.",
                     "Library: euro reference exchange rates (USD, GBP, JPY, CHF, CNY), monthly."),
        license="Condizioni d'uso del sito BCE: riutilizzo libero con citazione della fonte",
        license_url="https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html",
        attribution=T("Obbligatoria: la BCE va citata come fonte e i dati riportati fedelmente.",
                      "Required: the ECB must be cited as the source and the data reproduced accurately."),
        commercial=CONDITIONAL,
        commercial_note=T("Consentito; se i dati entrano in prodotti a pagamento, va indicato agli acquirenti che sono ottenibili "
                          "gratuitamente dal sito della BCE.",
                          "Allowed; if the data are included in paid products, buyers must be told they can be obtained free of "
                          "charge from the ECB website."),
        redistribution=YES, redistribution_note=T("Consentita con citazione della fonte.", "Allowed with source citation."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Nessuna modifica dei valori. Eventuali trasformazioni calcolate in NEXUS (es. tassi di crescita) sono "
                        "dichiarate come tali.",
                        "Values unchanged. Any transformation computed in NEXUS (e.g. growth rates) is stated as such."),
        terms_url="https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html", verified_on=POLICY_DATE,
        status=VERIFIED, notes=T("", ""),
    ),
    LicenseEntry(
        id="gutenberg", name="Project Gutenberg", publisher="Project Gutenberg Literary Archive Foundation",
        homepage="https://www.gutenberg.org",
        applies_to=T("Biblioteca: 10 classici dell'economia (Smith, Ricardo, Mill, Malthus, Bagehot, Mackay, George, Veblen, Keynes).",
                     "Library: 10 economics classics (Smith, Ricardo, Mill, Malthus, Bagehot, Mackay, George, Veblen, Keynes)."),
        license="Pubblico dominio (opere) + Project Gutenberg License (file e marchio)",
        license_url="https://www.gutenberg.org/policy/license.html",
        attribution=T("Non richiesta per le opere; NEXUS indica autore, titolo e link all'ebook. La licenza Project Gutenberg resta "
                      "inclusa nel testo.",
                      "Not required for the works; NEXUS lists author, title and a link to the ebook. The Project Gutenberg licence "
                      "remains included in the text."),
        commercial=CONDITIONAL,
        commercial_note=T("Le opere sono libere; il marchio Project Gutenberg no. NEXUS offre questi testi gratuitamente. Per "
                          "distribuirli a pagamento bisogna togliere licenza e riferimenti a Project Gutenberg, oppure versare le "
                          "royalty previste.",
                          "The works are free; the Project Gutenberg trademark is not. NEXUS offers these texts free of charge. To "
                          "distribute them for a fee, the licence and Project Gutenberg references must be removed, or the stated "
                          "royalties paid."),
        redistribution=CONDITIONAL,
        redistribution_note=T("Gratuita con la licenza Project Gutenberg inclusa, oppure senza alcun riferimento al marchio.",
                              "Free of charge with the Project Gutenberg licence included, or without any reference to the trademark."),
        territorial=T("Pubblico dominio negli USA. In Italia e nell'UE un'opera è libera 70 anni dopo la morte dell'autore: tutti gli "
                      "autori presenti sono morti prima del 1956 (il più recente, Keynes, nel 1946), quindi le opere sono libere anche nell'UE.",
                      "Public domain in the US. In Italy and the EU a work is free 70 years after the author's death: all authors "
                      "included died before 1956 (the latest, Keynes, in 1946), so the works are also free in the EU."),
        modifications=T("Testo integrale invariato; suddiviso in segmenti solo per la ricerca interna.",
                        "Full text unchanged; split into segments only for internal search."),
        terms_url="https://www.gutenberg.org/policy/license.html", verified_on=POLICY_DATE, status=VERIFIED, notes=T("", ""),
    ),
    LicenseEntry(
        id="us_gov", name="Congressional Research Service (Congresso degli Stati Uniti)", publisher="Library of Congress — Congressional Research Service",
        homepage="https://crsreports.congress.gov",
        applies_to=T("Lezione guidata sul Piano Marshall: tabelle degli aiuti per paese e dei fondi dell'ECA (rapporto R45079).",
                     "Marshall Plan guided lesson: tables of aid by country and ECA funds (report R45079)."),
        license="Pubblico dominio negli Stati Uniti (opera del governo federale, 17 U.S.C. § 105)",
        license_url="https://www.copyright.gov/title17/92chap1.html#105",
        attribution=T("Non obbligatoria per legge; NEXUS cita sempre il rapporto (autore, numero, data) e la fonte originale dei dati che riporta.",
                      "Not legally required; NEXUS always cites the report (author, number, date) and the original source of the data it reports."),
        commercial=YES, commercial_note=T("Consentito: le opere del governo federale USA non sono protette da copyright.",
                                          "Allowed: US federal government works are not protected by copyright."),
        redistribution=YES, redistribution_note=T("Consentita.", "Allowed."),
        territorial=T("Il pubblico dominio è stabilito dalla legge statunitense; fuori dagli USA lo status può dipendere dalla legge locale.",
                      "Public-domain status is set by US law; outside the US it may depend on local law."),
        modifications=T("Cifre riportate come nella fonte; la quota percentuale per paese è calcolata da NEXUS ed è indicata come tale.",
                        "Figures reported as in the source; the percentage share per country is computed by NEXUS and labelled as such."),
        terms_url="https://crsreports.congress.gov/product/pdf/R/R45079", verified_on="2026-11-13", status=VERIFIED,
        notes=T("Le tabelle del rapporto riprendono dati USAID (1971) e Brown e Opie (1953), citati nella lezione.",
                "The report's tables reproduce USAID (1971) and Brown and Opie (1953) data, cited in the lesson."),
    ),
    LicenseEntry(
        id="uk_parliament", name="Hansard (Camera dei Comuni del Regno Unito)", publisher="UK Parliament",
        homepage="https://api.parliament.uk/historic-hansard/",
        applies_to=T("Lezione guidata sul Fondo Sociale Europeo: quota del Fondo sul bilancio comunitario 1973–1984 e assegnazioni al Regno Unito.",
                     "European Social Fund guided lesson: the Fund's share of the Community budget 1973–1984 and allocations to the United Kingdom."),
        license="Open Parliament Licence v3.0",
        license_url="https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/",
        attribution=T("Obbligatoria: «Contains Parliamentary information licensed under the Open Parliament Licence v3.0», con il riferimento alla seduta.",
                      "Required: “Contains Parliamentary information licensed under the Open Parliament Licence v3.0”, with the sitting reference."),
        commercial=YES, commercial_note=T("Consentito con attribuzione.", "Allowed with attribution."),
        redistribution=YES, redistribution_note=T("Consentita con attribuzione.", "Allowed with attribution."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Cifre riportate come nella risposta scritta; tabelle tradotte in italiano.", "Figures reported as in the written answer; tables translated into Italian."),
        terms_url="https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/", verified_on="2026-11-13", status=VERIFIED,
        notes=T("", ""),
    ),
    LicenseEntry(
        id="fred_nber", name="NBER Macrohistory Database (via FRED)", publisher="National Bureau of Economic Research",
        homepage="https://fred.stlouisfed.org",
        applies_to=T("Demo pubblica (1929–1933): Dow Jones, tasso di sconto della Fed di New York, disoccupazione USA.",
                     "Public demo (1929–1933): Dow Jones, New York Fed discount rate, US unemployment."),
        license="Copyrighted: Citation Required (classificazione FRED)",
        license_url="https://fred.stlouisfed.org/legal/",
        attribution=T("Obbligatoria: «National Bureau of Economic Research, <titolo> [<codice>], retrieved from FRED, Federal Reserve "
                      "Bank of St. Louis», con link e data. Va conservato l'avviso di copyright.",
                      "Required: “National Bureau of Economic Research, <title> [<code>], retrieved from FRED, Federal Reserve Bank "
                      "of St. Louis”, with link and date. The copyright notice must be kept."),
        commercial=CONDITIONAL,
        commercial_note=T("Consentito con attribuzione per uso didattico e per report o pubblicazioni; non serve autorizzazione "
                          "preventiva per questa categoria.",
                          "Allowed with attribution for teaching and in reports or publications; no prior approval needed for this category."),
        redistribution=CONDITIONAL, redistribution_note=T("Con citazione e avviso di copyright.", "With citation and copyright notice."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Nessuna modifica dei valori.", "Values unchanged."),
        terms_url="https://fred.stlouisfed.org/legal/", verified_on=POLICY_DATE, status=VERIFIED,
        notes=T("Non fa parte della Biblioteca: è usata solo nella demo pubblica.", "Not part of the Library: used only in the public demo."),
    ),
    LicenseEntry(
        id="fred", name="FRED", publisher="Federal Reserve Bank of St. Louis", homepage="https://fred.stlouisfed.org",
        applies_to=T("Serie importate dagli utenti con la propria chiave FRED; demo pubblica: produzione industriale e prezzi al consumo USA.",
                     "Series imported by users with their own FRED key; public demo: US industrial production and consumer prices."),
        license="Variabile per serie: «Public Domain: Citation Requested», «Copyrighted: Citation Required» o «Copyrighted: Pre-approval Required»",
        license_url="https://fred.stlouisfed.org/legal/",
        attribution=T("Citare la fonte originale e «via FRED» (es. «Fonte: BLS via FRED»), con link alla serie.",
                      "Cite the original source and “via FRED” (e.g. “Source: BLS via FRED”), with a link to the series."),
        commercial=CONDITIONAL,
        commercial_note=T("Dipende dalla serie: quelle «Pre-approval Required» solo per uso didattico o personale salvo permesso del titolare.",
                          "Depends on the series: “Pre-approval Required” series only for educational or personal use unless the "
                          "rights holder grants permission."),
        redistribution=CONDITIONAL, redistribution_note=T("Dipende dalla serie; controllare le note della serie su FRED.",
                                                          "Depends on the series; check the series notes on FRED."),
        territorial=NONE_TERRITORIAL,
        modifications=T("Nessuna modifica dei valori.", "Values unchanged."),
        terms_url="https://fred.stlouisfed.org/legal/", verified_on=POLICY_DATE, status=PER_ITEM,
        notes=T("Le serie della demo INDPRO e CPIAUCNS sono «Public Domain: Citation Requested».",
                "The demo series INDPRO and CPIAUCNS are “Public Domain: Citation Requested”."),
    ),
]}

LIBRARY_LICENSES = ("wikidata", "wikipedia", "world_bank_wdi", "owid", "maddison", "eurostat", "ecb", "gutenberg")


def _host(url: str) -> str:
    try:
        return (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return ""


def for_series(source_url: str, source_series_id: str = "") -> str | None:
    """Scheda di licenza di una serie, dedotta dall'URL della fonte. None se la fonte non è nel registro."""
    h = _host(source_url)
    if h.endswith("worldbank.org"):
        return "world_bank_wdi"
    if h.endswith("ourworldindata.org"):
        return "maddison" if "maddison" in (source_url or "").lower() else "owid"
    if h == "ec.europa.eu" and "/eurostat" in (source_url or ""):
        return "eurostat"
    if h.endswith("ecb.europa.eu"):
        return "ecb"
    if h.endswith("stlouisfed.org"):
        sid = (source_series_id or source_url.rsplit("/", 1)[-1]).upper()
        return "fred_nber" if sid.endswith("NBR") else "fred"
    return None


def for_document(origin: str, origin_url: str = "") -> str | None:
    if origin == "gutenberg" or _host(origin_url).endswith("gutenberg.org"):
        return "gutenberg"
    return None


def for_source(url: str) -> str | None:
    h = _host(url)
    if h.endswith("wikidata.org"):
        return "wikidata"
    if h.endswith("wikipedia.org"):
        return "wikipedia"
    return None


def for_source_record(url: str, notes: str = "") -> list[str]:
    """Schede di una fonte: Wikidata per i dati strutturati, più Wikipedia se la descrizione ne riporta un estratto."""
    out = [lid] if (lid := for_source(url)) else []
    if lid == "wikidata" and "wikipedia" in (notes or "").lower():
        out.append("wikipedia")
    return out


def get(license_id: str | None) -> LicenseEntry | None:
    return LICENSES.get(license_id or "")


def registry() -> list[dict]:
    return [e.as_dict() for e in LICENSES.values()]
