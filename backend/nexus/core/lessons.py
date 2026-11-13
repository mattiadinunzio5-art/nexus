"""Lezioni guidate: percorsi di ricerca pronti per studenti e docenti.

Contengono solo istruzioni, codici reali di serie pubbliche e date
ampiamente documentate. I dati vengono scaricati dalle fonti quando lo
studente li importa; le letture consigliate entrano in bibliografia come
«non verificate», da controllare sull'originale.
"""

from __future__ import annotations

LESSONS: list[dict] = [
    {
        "id": "crisi-1929",
        "title": "La crisi del 1929 e la Grande Depressione",
        "level": "Introduttivo",
        "duration": "circa 3 ore",
        "summary": "Dal crollo di Wall Street alla depressione degli anni Trenta: produzione industriale, prezzi e scelte di politica economica.",
        "goals": [
            "Collocare in ordine gli eventi principali tra il 1929 e il 1933.",
            "Leggere la caduta della produzione industriale e dei prezzi negli Stati Uniti.",
            "Distinguere i fatti documentati dalle interpretazioni degli storici.",
        ],
        "key_dates": [
            {"date": "1929-10-24", "event": "«Giovedì nero» alla Borsa di New York"},
            {"date": "1929-10-29", "event": "«Martedì nero»: nuovo crollo di Wall Street"},
            {"date": "1930-06-17", "event": "Firma dello Smoot-Hawley Tariff Act"},
            {"date": "1933-03-06", "event": "Inizio della «bank holiday» nazionale negli Stati Uniti"},
            {"date": "1933-06-16", "event": "Firma del Banking Act (Glass-Steagall)"},
        ],
        "series": [
            {"label": "Produzione industriale USA (FRED INDPRO, dal 1919)", "category": "other", "params": {"connector": "fred", "series_id": "INDPRO"}},
            {"label": "Indice dei prezzi al consumo USA, non destagionalizzato (FRED CPIAUCNS, dal 1913)", "category": "inflation", "params": {"connector": "fred", "series_id": "CPIAUCNS"}},
        ],
        "readings": [
            {"source_type": "book", "title": "A Monetary History of the United States, 1867–1960", "authors": ["Friedman, Milton", "Schwartz, Anna Jacobson"], "year": 1963, "publisher": "Princeton University Press"},
            {"source_type": "book", "title": "The World in Depression, 1929–1939", "authors": ["Kindleberger, Charles P."], "year": 1973, "publisher": "University of California Press"},
            {"source_type": "book", "title": "The Great Crash, 1929", "authors": ["Galbraith, John Kenneth"], "year": 1955, "publisher": "Houghton Mifflin"},
        ],
        "steps": [
            {"title": "Importa i dati", "detail": "Importa le due serie FRED proposte (serve la chiave FRED gratuita in Sistema → Credenziali).", "module": "/financial"},
            {"title": "Costruisci la cronologia", "detail": "In Historical Intelligence aggiungi le date chiave come eventi, citando per ognuno una fonte della bibliografia.", "module": "/history"},
            {"title": "Guarda senza il senno di poi", "detail": "Apri la Time Machine al 1930: cosa si sapeva allora? Annota cosa non era ancora noto.", "module": "/time-machine?year=1930&country=Stati+Uniti&category=economic"},
            {"title": "Confronta le serie", "detail": "Confronta produzione e prezzi tra 1929 e 1933 e descrivi l'andamento con le tue parole, citando la serie.", "module": "/financial"},
            {"title": "Fatti e interpretazioni", "detail": "Nel rapporto separa i fatti (date, dati) dalle interpretazioni (es. il ruolo della politica monetaria secondo Friedman e Schwartz).", "module": "/studio"},
        ],
    },
    {
        "id": "inflazione-anni-70",
        "title": "L'inflazione degli anni Settanta",
        "level": "Intermedio",
        "duration": "circa 4 ore",
        "summary": "Fine di Bretton Woods, shock petroliferi e la svolta della Federal Reserve: inflazione, tassi e disoccupazione negli Stati Uniti.",
        "goals": [
            "Collegare shock petroliferi, inflazione e tassi d'interesse.",
            "Leggere insieme inflazione e disoccupazione nello stesso periodo.",
            "Valutare la svolta di politica monetaria del 1979 con i dati.",
        ],
        "key_dates": [
            {"date": "1971-08-15", "event": "Nixon sospende la convertibilità del dollaro in oro"},
            {"date": "1973-10-17", "event": "Inizio dell'embargo petrolifero dei paesi arabi OPEC"},
            {"date": "1979-08-06", "event": "Paul Volcker diventa presidente della Federal Reserve"},
            {"date": "1979-10-06", "event": "La Fed annuncia il nuovo approccio di politica monetaria"},
        ],
        "series": [
            {"label": "Prezzi al consumo USA (FRED CPIAUCSL)", "category": "inflation", "params": {"connector": "fred", "series_id": "CPIAUCSL"}},
            {"label": "Tasso effettivo Fed Funds (FRED FEDFUNDS)", "category": "rates", "params": {"connector": "fred", "series_id": "FEDFUNDS"}},
            {"label": "Tasso di disoccupazione USA (FRED UNRATE)", "category": "unemployment", "params": {"connector": "fred", "series_id": "UNRATE"}},
            {"label": "Prezzo spot del petrolio WTI (FRED WTISPLC)", "category": "commodities", "params": {"connector": "fred", "series_id": "WTISPLC"}},
        ],
        "readings": [
            {"source_type": "book", "title": "A History of the Federal Reserve, Volume 2", "authors": ["Meltzer, Allan H."], "year": 2009, "publisher": "University of Chicago Press"},
        ],
        "steps": [
            {"title": "Importa i dati", "detail": "Importa le quattro serie FRED proposte.", "module": "/financial"},
            {"title": "Calcola l'inflazione annua", "detail": "Nell'analisi della serie CPI usa la variazione su 12 mesi e individua i picchi del decennio.", "module": "/financial"},
            {"title": "Metti in fila gli shock", "detail": "Aggiungi le date chiave alla cronologia con le fonti e collega gli eventi alle serie nel Knowledge Graph.", "module": "/graph"},
            {"title": "Scenario", "detail": "Nell'Economic Laboratory prova uno shock sui tassi e confronta il risultato con quanto accaduto davvero (è un modello, non una previsione).", "module": "/lab"},
            {"title": "Scrivi le conclusioni", "detail": "Nel rapporto indica i limiti: correlazione non è causalità.", "module": "/studio"},
        ],
    },
    {
        "id": "crisi-2008",
        "title": "La crisi finanziaria del 2008",
        "level": "Intermedio",
        "duration": "circa 4 ore",
        "summary": "Dalla bolla immobiliare al fallimento di Lehman Brothers: prezzi delle case, tassi e lavoro negli Stati Uniti, con uno sguardo all'area euro.",
        "goals": [
            "Ricostruire la sequenza degli eventi dal 2007 al 2009.",
            "Leggere prezzi delle case, tassi e disoccupazione nello stesso grafico.",
            "Confrontare la risposta della Fed e della BCE.",
        ],
        "key_dates": [
            {"date": "2008-03-16", "event": "Salvataggio di Bear Stearns con l'acquisizione da parte di JPMorgan"},
            {"date": "2008-09-15", "event": "Lehman Brothers presenta istanza di fallimento"},
            {"date": "2008-10-03", "event": "Firma dell'Emergency Economic Stabilization Act (TARP)"},
        ],
        "series": [
            {"label": "Indice dei prezzi delle case S&P CoreLogic Case-Shiller USA (FRED CSUSHPINSA)", "category": "other", "params": {"connector": "fred", "series_id": "CSUSHPINSA"}},
            {"label": "Tasso effettivo Fed Funds (FRED FEDFUNDS)", "category": "rates", "params": {"connector": "fred", "series_id": "FEDFUNDS"}},
            {"label": "Tasso di disoccupazione USA (FRED UNRATE)", "category": "unemployment", "params": {"connector": "fred", "series_id": "UNRATE"}},
            {"label": "Tasso BCE sulle operazioni di rifinanziamento principali", "category": "rates", "params": {"connector": "ecb", "dataset": "FM", "key": "B.U2.EUR.4F.KR.MRR_FR.LEV"}},
        ],
        "readings": [
            {"source_type": "document", "title": "The Financial Crisis Inquiry Report", "authors": ["Financial Crisis Inquiry Commission"], "year": 2011, "publisher": "U.S. Government Printing Office"},
        ],
        "steps": [
            {"title": "Importa i dati", "detail": "Importa le serie proposte: tre da FRED (con chiave) e una dalla BCE (senza chiave).", "module": "/financial"},
            {"title": "Costruisci la cronologia", "detail": "Aggiungi le date chiave come eventi con la loro fonte.", "module": "/history"},
            {"title": "Time Machine", "detail": "Apri la Time Machine a luglio 2008: quali dati erano disponibili prima di Lehman?", "module": "/time-machine"},
            {"title": "War Room", "detail": "Poni una domanda alla Research War Room usando solo i documenti del progetto e verifica ogni citazione.", "module": "/war-room"},
            {"title": "Rapporto", "detail": "Scrivi il rapporto ed esportalo in PDF o LaTeX.", "module": "/studio"},
        ],
    },
]

LESSONS_BY_ID = {x["id"]: x for x in LESSONS}
