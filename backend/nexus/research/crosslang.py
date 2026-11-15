"""Ricerca bilingue italiano ↔ inglese senza AI e senza servizi esterni.

Una ricerca in italiano deve trovare anche documenti, fonti, eventi, entità e serie scritti in inglese
(e viceversa). Si usa un glossario del dominio (storia, economia, finanza, ambiente, istituzioni) con
le espressioni di più parole prima delle singole parole, e una riduzione dei plurali italiani.
Il glossario è esplicito: ogni corrispondenza è verificabile, nulla viene «indovinato».
"""

from __future__ import annotations

import re

from .text import STOPWORDS, strip_accents

# italiano → inglese. Le espressioni di più parole hanno la precedenza sulle singole parole.
IT_EN: dict[str, list[str]] = {
    # --- espressioni -------------------------------------------------------------------------
    "guerra fredda": ["cold war"], "prima guerra mondiale": ["world war i", "first world war"],
    "seconda guerra mondiale": ["world war ii", "second world war"], "guerra mondiale": ["world war"],
    "piano marshall": ["marshall plan"], "grande depressione": ["great depression"], "grande recessione": ["great recession"],
    "crisi finanziaria": ["financial crisis"], "crisi petrolifera": ["oil crisis"], "shock petrolifero": ["oil shock"],
    "crisi del debito": ["debt crisis"], "crisi bancaria": ["banking crisis"], "bolla immobiliare": ["housing bubble"],
    "banca centrale": ["central bank"], "banca centrale europea": ["european central bank", "ecb"],
    "fondo monetario internazionale": ["international monetary fund", "imf"], "banca mondiale": ["world bank"],
    "unione europea": ["european union"], "comunità economica europea": ["european economic community"],
    "nazioni unite": ["united nations"], "stati uniti": ["united states", "usa"], "regno unito": ["united kingdom", "uk"],
    "unione sovietica": ["soviet union", "ussr"], "muro di berlino": ["berlin wall"], "rivoluzione industriale": ["industrial revolution"],
    "rivoluzione francese": ["french revolution"], "rivoluzione russa": ["russian revolution"], "guerra civile": ["civil war"],
    "prodotto interno lordo": ["gross domestic product", "gdp"], "debito pubblico": ["public debt", "government debt"],
    "spesa pubblica": ["public spending", "government spending"], "politica monetaria": ["monetary policy"],
    "politica fiscale": ["fiscal policy"], "tasso di interesse": ["interest rate"], "tassi di interesse": ["interest rates"],
    "tasso di cambio": ["exchange rate"], "tassi di cambio": ["exchange rates"], "mercato del lavoro": ["labour market", "labor market"],
    "materie prime": ["commodities", "raw materials"], "energia rinnovabile": ["renewable energy"], "energie rinnovabili": ["renewable energy", "renewables"],
    "cambiamento climatico": ["climate change"], "cambiamenti climatici": ["climate change"], "riscaldamento globale": ["global warming"],
    "gas serra": ["greenhouse gas", "greenhouse gases"], "combustibili fossili": ["fossil fuels"], "economia circolare": ["circular economy"],
    "rifiuti plastici": ["plastic waste"], "rifiuti di plastica": ["plastic waste"], "inquinamento da plastica": ["plastic pollution"],
    "microplastiche": ["microplastics"], "monouso": ["single-use", "single use"], "riciclo della plastica": ["plastic recycling"],
    "gold standard": ["gold standard"], "sistema monetario": ["monetary system"], "bretton woods": ["bretton woods"],
    "borsa valori": ["stock exchange", "stock market"], "mercato azionario": ["stock market"], "crollo di wall street": ["wall street crash"],
    "potere d'acquisto": ["purchasing power"], "costo della vita": ["cost of living"], "salario minimo": ["minimum wage"],
    "stato sociale": ["welfare state"], "lotta di classe": ["class struggle"], "decolonizzazione": ["decolonization", "decolonisation"],
    "diritti umani": ["human rights"], "diritti civili": ["civil rights"], "libero scambio": ["free trade"],
    "bilancia commerciale": ["trade balance"], "bilancia dei pagamenti": ["balance of payments"], "investimenti esteri": ["foreign investment"],
    "paesi in via di sviluppo": ["developing countries"], "mercati emergenti": ["emerging markets"], "aspettativa di vita": ["life expectancy"],
    # --- parole -----------------------------------------------------------------------------
    "plastica": ["plastic"], "plastiche": ["plastics"], "polimero": ["polymer"], "polimeri": ["polymers"], "imballaggio": ["packaging"],
    "imballaggi": ["packaging"], "rifiuto": ["waste"], "rifiuti": ["waste", "garbage"], "riciclo": ["recycling"], "riciclaggio": ["recycling"],
    "inquinamento": ["pollution"], "ambiente": ["environment"], "ambientale": ["environmental"], "emissioni": ["emissions"],
    "clima": ["climate"], "oceano": ["ocean"], "oceani": ["oceans"], "mare": ["sea", "marine"], "marino": ["marine"], "discarica": ["landfill"],
    "incenerimento": ["incineration"], "petrolio": ["oil", "petroleum"], "petrolchimica": ["petrochemical"], "petrolchimico": ["petrochemical"],
    "gas": ["gas"], "carbone": ["coal"], "energia": ["energy"], "elettricità": ["electricity"], "acqua": ["water"], "suolo": ["soil"],
    "produzione": ["production", "output"], "consumo": ["consumption"], "consumi": ["consumption"], "industria": ["industry"],
    "industriale": ["industrial"], "manifattura": ["manufacturing"], "agricoltura": ["agriculture"], "agricolo": ["agricultural"],
    "economia": ["economy", "economics"], "economico": ["economic"], "economica": ["economic"], "finanza": ["finance"],
    "finanziario": ["financial"], "finanziaria": ["financial"], "mercato": ["market"], "mercati": ["markets"], "prezzo": ["price"],
    "prezzi": ["prices"], "inflazione": ["inflation"], "deflazione": ["deflation"], "disoccupazione": ["unemployment"],
    "occupazione": ["employment"], "lavoro": ["labour", "labor", "work"], "salario": ["wage"], "salari": ["wages"], "reddito": ["income"],
    "ricchezza": ["wealth"], "povertà": ["poverty"], "disuguaglianza": ["inequality"], "crescita": ["growth"], "recessione": ["recession"],
    "depressione": ["depression"], "crisi": ["crisis", "crises"], "crollo": ["crash", "collapse"], "bolla": ["bubble"], "debito": ["debt"],
    "deficit": ["deficit"], "tasse": ["taxes"], "tassa": ["tax"], "imposte": ["taxes"], "tasso": ["rate"], "tassi": ["rates"],
    "interesse": ["interest"], "banca": ["bank"], "banche": ["banks"], "bancario": ["banking"], "bancaria": ["banking"],
    "moneta": ["money", "currency"], "valuta": ["currency"], "valute": ["currencies"], "cambio": ["exchange"], "oro": ["gold"],
    "argento": ["silver"], "credito": ["credit"], "prestito": ["loan"], "prestiti": ["loans"], "risparmio": ["savings"],
    "investimento": ["investment"], "investimenti": ["investment", "investments"], "borsa": ["stock market", "stock exchange"],
    "azioni": ["shares", "stocks"], "obbligazioni": ["bonds"], "titoli": ["securities", "bonds"], "commercio": ["trade"],
    "esportazioni": ["exports"], "importazioni": ["imports"], "dazi": ["tariffs"], "dazio": ["tariff"], "impresa": ["company", "firm"],
    "imprese": ["companies", "firms"], "azienda": ["company"], "aziende": ["companies"], "popolazione": ["population"],
    "demografia": ["demography"], "migrazione": ["migration"], "emigrazione": ["emigration"], "immigrazione": ["immigration"],
    "salute": ["health"], "sanità": ["health"], "istruzione": ["education"], "città": ["city", "cities"], "trasporti": ["transport"],
    "guerra": ["war"], "guerre": ["wars"], "pace": ["peace"], "trattato": ["treaty"], "accordo": ["agreement"], "accordi": ["agreements"],
    "rivoluzione": ["revolution"], "riforma": ["reform"], "riforme": ["reforms"], "governo": ["government"], "stato": ["state"],
    "politica": ["policy", "politics"], "elezioni": ["elections"], "partito": ["party"], "impero": ["empire"], "colonia": ["colony"],
    "colonie": ["colonies"], "colonialismo": ["colonialism"], "indipendenza": ["independence"], "repubblica": ["republic"],
    "monarchia": ["monarchy"], "dittatura": ["dictatorship"], "fascismo": ["fascism"], "comunismo": ["communism"],
    "socialismo": ["socialism"], "capitalismo": ["capitalism"], "liberalismo": ["liberalism"], "globalizzazione": ["globalization", "globalisation"],
    "sciopero": ["strike"], "sindacato": ["union", "trade union"], "sindacati": ["unions"], "legge": ["law", "act"], "leggi": ["laws"],
    "regolamento": ["regulation"], "direttiva": ["directive"], "divieto": ["ban"], "tecnologia": ["technology"], "innovazione": ["innovation"],
    "scienza": ["science"], "storia": ["history"], "storico": ["historical"], "secolo": ["century"], "anni": ["years"],
    "decennio": ["decade"], "mondo": ["world"], "mondiale": ["world", "global"], "globale": ["global"], "europa": ["europe"],
    "europeo": ["european"], "europea": ["european"], "italia": ["italy"], "italiano": ["italian"], "italiana": ["italian"],
    "germania": ["germany"], "francia": ["france"], "spagna": ["spain"], "cina": ["china"], "giappone": ["japan"], "india": ["india"],
    "russia": ["russia"], "brasile": ["brazil"], "america": ["america"], "africa": ["africa"], "asia": ["asia"], "grecia": ["greece"],
    "inghilterra": ["england"], "olanda": ["netherlands"], "paesi bassi": ["netherlands"], "svizzera": ["switzerland"],
    "pil": ["gdp"], "bce": ["ecb"], "fmi": ["imf"], "onu": ["un", "united nations"], "ue": ["eu"], "usa": ["usa", "united states"],
}

# inglese → italiano, ricavato dal glossario.
EN_IT: dict[str, list[str]] = {}
for _it, _ens in IT_EN.items():
    for _en in _ens:
        EN_IT.setdefault(_en, [])
        if _it not in EN_IT[_en]:
            EN_IT[_en].append(_it)

_NORM_IT = {strip_accents(k): v for k, v in IT_EN.items()}
_NORM_EN = {strip_accents(k): v for k, v in EN_IT.items()}
_MAX_PHRASE = max(len(k.split()) for k in list(IT_EN) + list(EN_IT))
_WORD = re.compile(r"[\wÀ-ÿ'’-]+", re.UNICODE)


def _singulars(w: str) -> list[str]:
    """Forme di partenza di un plurale (italiano e inglese): «plastiche» → «plastica», «crises» → «crisis»."""
    out = []
    for suf, rep in (("che", "ca"), ("ghe", "ga"), ("chi", "co"), ("ghi", "go"), ("zioni", "zione"), ("ioni", "ione"),
                     ("e", "a"), ("i", "o"), ("i", "e"), ("ies", "y"), ("es", "is"), ("es", ""), ("s", "")):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            out.append(w[: -len(suf)] + rep)
    return out


def _lookup(phrase: str) -> list[str]:
    p = strip_accents(phrase.lower())
    for table in (_NORM_IT, _NORM_EN):
        if p in table:
            return table[p]
    if " " not in p:
        for s in _singulars(p):
            for table in (_NORM_IT, _NORM_EN):
                if s in table:
                    return table[s]
    return []


def translations(query: str) -> list[str]:
    """Le espressioni equivalenti nell'altra lingua per i termini riconosciuti della ricerca (senza l'originale)."""
    words = [w.lower().replace("’", "'") for w in _WORD.findall(query)]
    out: list[str] = []
    i = 0
    while i < len(words):
        for n in range(min(_MAX_PHRASE, len(words) - i), 0, -1):
            chunk = " ".join(words[i:i + n])
            if n == 1 and strip_accents(chunk) in STOPWORDS:
                found = []
            else:
                found = _lookup(chunk)
            if found:
                out += [f for f in found if strip_accents(f) != strip_accents(chunk)]
                i += n
                break
        else:
            i += 1
    return list(dict.fromkeys(out))


def _translate_whole(words: list[str]) -> list[str]:
    """La ricerca tradotta per intero: ogni espressione riconosciuta sostituita, le altre parole di contenuto lasciate."""
    out, i = [], 0
    while i < len(words):
        for n in range(min(_MAX_PHRASE, len(words) - i), 0, -1):
            chunk = " ".join(words[i:i + n])
            found = [] if (n == 1 and strip_accents(chunk) in STOPWORDS) else _lookup(chunk)
            if found:
                out.append(found[0])
                i += n
                break
        else:
            if strip_accents(words[i]) not in STOPWORDS:
                out.append(words[i])
            i += 1
    return out


def variants(query: str) -> list[str]:
    """La ricerca originale e, se il glossario la riconosce, la stessa ricerca nell'altra lingua."""
    q = query.strip()
    if not q:
        return []
    words = [w.lower().replace("’", "'") for w in _WORD.findall(q)]
    whole = " ".join(_translate_whole(words))
    return [q] + ([whole] if whole and strip_accents(whole) != strip_accents(" ".join(words)) else [])


def content_words(v: str) -> list[str]:
    """Le parole che una variante deve contenere (stopword escluse); le parole brevi restano se sono l'unico termine."""
    ws = [w for w in _WORD.findall(v.lower()) if strip_accents(w) not in STOPWORDS]
    return ws or [v.strip()]


def match_any(columns, query: str):
    """Condizione SQL: per almeno una variante (originale o tradotta), ogni sua parola compare in una delle colonne."""
    from sqlalchemy import and_, or_

    def esc(w: str) -> str:
        return "%" + w.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"

    alts = []
    for v in variants(query):
        alts.append(and_(*[or_(*[c.ilike(esc(w), escape="\\") for c in columns]) for w in content_words(v)]))
    return or_(*alts) if alts else None


def text_matcher(query: str):
    """Controllo in Python a inizio parola per tutte le varianti (come `match_any`, ma su testi già letti)."""
    rxs = [[re.compile(r"(?<![\w])" + re.escape(w), re.IGNORECASE) for w in content_words(v)] for v in variants(query)]

    def ok(*texts: str | None) -> bool:
        blob = " ".join(t or "" for t in texts)
        return any(all(rx.search(blob) for rx in group) for group in rxs)

    return ok


def expand_terms(toks: list[str]) -> list[str]:
    """Per la ricerca a parole (BM25/full-text): i termini originali più i loro equivalenti, già normalizzati."""
    from .text import terms

    extra = []
    for t in translations(" ".join(toks)):
        extra += terms(t)
    return list(dict.fromkeys(toks + extra))
