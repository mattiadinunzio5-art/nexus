"""Kit di ricerca: progetti pronti su temi proposti da docenti (Piano Marshall, Fondo Sociale Europeo).

Non sono lezioni guidate: diventano progetti nell'account di chi li riceve (vedi services/research_kits.py
e scripts/create_research_projects.py). Ogni dato riporta la sua fonte e la licenza registrata
(core/licenses.py); le lacune sono dichiarate, non riempite.
"""

from __future__ import annotations

RESEARCH_KITS: list[dict] = [
    {
        "id": "piano-marshall",
        "title": "Il Piano Marshall (European Recovery Program, 1948–1952)",
        "level": "Intermedio",
        "duration": "circa 3 ore",
        "summary": "Gli aiuti americani alla ricostruzione europea: chi li ricevette, quanto, come furono finanziati e che ruolo ebbe l'OECE. Un esercizio di sintesi su fonti abbondanti, senza perdere la provenienza di ogni numero.",
        "goals": [
            "Ricostruire la cronologia dal discorso di Harvard alla fine del programma.",
            "Leggere la distribuzione degli aiuti per paese e capire perché le stime del totale variano (da 10,3 a 13,6 miliardi di dollari).",
            "Confrontare gli aiuti con l'andamento del PIL pro capite (Maddison), distinguendo correlazione e causalità.",
        ],
        "key_dates": [
            {"date": "1947-06-05", "event": "Discorso del Segretario di Stato George C. Marshall all'Università di Harvard", "source": "Congressional Research Service, «The Marshall Plan: Design, Accomplishments, and Significance» (R45079, C. Tarnoff, agg. 18/01/2018)"},
            {"date": "1947-07-12", "event": "Conferenza di Parigi: 16 paesi istituiscono il Comitato di cooperazione economica europea (CEEC)", "source": "Congressional Research Service, «The Marshall Plan: Design, Accomplishments, and Significance» (R45079, C. Tarnoff, agg. 18/01/2018)"},
            {"date": "1947-12-19", "event": "Il presidente Truman presenta al Congresso il programma di aiuti", "source": "Congressional Research Service, «The Marshall Plan: Design, Accomplishments, and Significance» (R45079, C. Tarnoff, agg. 18/01/2018)"},
            {"date": "1948-04-03", "event": "Entra in vigore l'Economic Cooperation Act (titolo I del Foreign Assistance Act of 1948, P.L. 80-472)", "source": "Congressional Research Service, «The Marshall Plan: Design, Accomplishments, and Significance» (R45079, C. Tarnoff, agg. 18/01/2018); Wikidata Q4576"},
            {"date": "1948-04-16", "event": "Nasce l'Organizzazione europea per la cooperazione economica (OECE)", "source": "Wikidata Q3057312"},
            {"date": "1950", "event": "Nasce l'Unione europea dei pagamenti (UEP)", "source": "Wikidata Q1377612 (solo l'anno)"},
            {"date": "1952-06-30", "event": "Scadenza prevista del programma; l'ECA era già confluita nella Mutual Security Agency nella seconda metà del 1951", "source": "Congressional Research Service, «The Marshall Plan: Design, Accomplishments, and Significance» (R45079, C. Tarnoff, agg. 18/01/2018)"},
            {"date": "1961-09-30", "event": "Scioglimento dell'OECE, sostituita dall'OCSE", "source": "Wikidata Q3057312"},
        ],
        "series": [
            {"label": "PIL pro capite — Italia (Maddison Project Database 2023, via OWID)", "category": "gdp", "params": {"connector": "owid", "slug": "gdp-per-capita-maddison-project-database", "entity": "Italy"}},
            {"label": "PIL pro capite — Francia (Maddison Project Database 2023, via OWID)", "category": "gdp", "params": {"connector": "owid", "slug": "gdp-per-capita-maddison-project-database", "entity": "France"}},
            {"label": "PIL pro capite — Regno Unito (Maddison Project Database 2023, via OWID)", "category": "gdp", "params": {"connector": "owid", "slug": "gdp-per-capita-maddison-project-database", "entity": "United Kingdom"}},
            {"label": "PIL pro capite — Germania (Maddison Project Database 2023, via OWID)", "category": "gdp", "params": {"connector": "owid", "slug": "gdp-per-capita-maddison-project-database", "entity": "Germany"}},
        ],
        "tables": [
            {
                "title": "Aiuti ERP per paese beneficiario, 3 aprile 1948 – 30 giugno 1952",
                "unit": "milioni di dollari correnti",
                "columns": ["Paese", "Aiuti (mln $)", "Quota sul totale (%)"],
                "rows": [["Austria", "677,8", "5,1"], ["Belgio/Lussemburgo", "559,3", "4,2"], ["Danimarca", "273,0", "2,0"], ["Francia", "2.713,6", "20,4"], ["Grecia", "706,7", "5,3"], ["Islanda", "29,3", "0,2"], ["Irlanda", "147,5", "1,1"], ["Italia", "1.508,8", "11,3"], ["Paesi Bassi", "1.083,5", "8,1"], ["Norvegia", "255,3", "1,9"], ["Portogallo", "51,2", "0,4"], ["Svezia", "107,3", "0,8"], ["Turchia", "225,1", "1,7"], ["Regno Unito", "3.189,8", "23,9"], ["Germania Ovest", "1.390,6", "10,4"], ["Regionale", "407,0", "3,1"], ["Totale", "13.325,8", "100,0"]],
                "source": "Congressional Research Service, «The Marshall Plan: Design, Accomplishments, and Significance» (R45079, C. Tarnoff, agg. 18/01/2018), Tabella 2 (fonte originale: USAID, Bureau for Program & Policy Coordination, 16 novembre 1971)",
                "source_url": "https://crsreports.congress.gov/product/pdf/R/R45079",
                "license_id": "us_gov",
                "notes": "La quota percentuale è calcolata da NEXUS sul totale di 13.325,8 milioni. Le stime del totale variano da 10,3 a 13,6 miliardi a seconda della durata considerata e dei programmi inclusi (CRS, nota 21: Wexler; Hartmann).",
            },
            {
                "title": "Fondi messi a disposizione dell'ECA per periodo",
                "unit": "milioni di dollari correnti",
                "columns": ["Voce", "3/4/1948–30/6/1949", "1/7/1949–30/6/1950", "1/7/1950–30/6/1951", "Totale"],
                "rows": [
                    ["Stanziamenti diretti", "5.074,0", "3.628,4", "2.200,0", "10.902,4"],
                    ["Prestiti (borrowing authority)", "972,3", "150,0", "62,5", "1.184,8"],
                    ["Garanzie sugli investimenti", "150,0", "50,0", "0,0", "200,0"],
                    ["Residui dagli aiuti provvisori", "14,5", "6,7", "0,0", "21,2"],
                    ["Trasferimenti da altre agenzie", "9,8", "225,1", "217,0", "451,9"],
                    ["Totale", "6.220,6", "4.060,2", "2.254,1", "12.534,9"],
                ],
                "source": "Congressional Research Service, «The Marshall Plan: Design, Accomplishments, and Significance» (R45079, C. Tarnoff, agg. 18/01/2018), Tabella 1 (da W. A. Brown Jr. e R. Opie, American Foreign Assistance, Brookings, 1953, p. 247)",
                "source_url": "https://crsreports.congress.gov/product/pdf/R/R45079",
                "license_id": "us_gov",
                "notes": "Il totale 1950–51 sottrae 225,4 milioni trasferiti ad altri programmi (Jugoslavia, Estremo Oriente, India), come indicato nella fonte.",
            },
        ],
        "gaps": [],
        "readings": [
            {"source_type": "document", "title": "The Marshall Plan: Design, Accomplishments, and Significance (R45079)", "authors": ["Tarnoff, Curt"], "year": 2018, "publisher": "Congressional Research Service"},
            {"source_type": "book", "title": "The Marshall Plan: America, Britain, and the Reconstruction of Western Europe, 1947-1952", "authors": ["Hogan, Michael J."], "year": 1987, "publisher": "Cambridge University Press"},
            {"source_type": "book", "title": "The Reconstruction of Western Europe, 1945-51", "authors": ["Milward, Alan S."], "year": 1984, "publisher": "University of California Press"},
            {"source_type": "book", "title": "The Marshall Plan and its Meaning", "authors": ["Price, Harry Bayard"], "year": 1955, "publisher": "Cornell University Press"},
            {"source_type": "book", "title": "American Foreign Assistance", "authors": ["Brown, William Adams Jr.", "Opie, Redvers"], "year": 1953, "publisher": "Brookings Institution"},
        ],
        "steps": [
            {"title": "Leggi le tabelle", "detail": "Le due tabelle sono nell'appunto-guida e, come file CSV, tra i documenti del progetto: chi ha ricevuto di più? Quanto pesano le stime diverse del totale?", "module": "/documents"},
            {"title": "Controlla la cronologia", "detail": "Le date chiave sono già eventi in Historical Intelligence, ciascuna collegata alla sua fonte: verificale e aggiungi quelle che mancano.", "module": "/history"},
            {"title": "Guarda il 1948 senza il senno di poi", "detail": "Apri la Time Machine al 1948: cosa si sapeva quando il programma partì?", "module": "/time-machine?year=1948"},
            {"title": "Aiuti e crescita", "detail": "Il PIL pro capite di Italia, Francia, Regno Unito e Germania (Maddison) è già importato: confrontalo tra il 1946 e il 1955. Ricorda: una crescita contemporanea agli aiuti non dimostra che ne sia la causa.", "module": "/financial/compare"},
            {"title": "Sintesi", "detail": "Nel Research Studio scrivi una sintesi di due pagine: fatti (date, cifre con fonte) separati dalle interpretazioni degli storici (es. Hogan, Milward).", "module": "/studio"},
        ],
    },
    {
        "id": "fse-1958-1989",
        "title": "Il Fondo Sociale Europeo dalle origini al 1989",
        "level": "Avanzato",
        "duration": "circa 4 ore, più ricerca d'archivio",
        "summary": "Un test su fonti scarse: cosa si trova davvero in rete sul Fondo Sociale Europeo tra il 1958 e il 1989, cosa manca e dove cercarlo. NEXUS mostra i buchi invece di riempirli.",
        "goals": [
            "Ricostruire la base giuridica del FSE e le sue riforme (1960, 1971, 1977, 1983).",
            "Raccogliere i pochi dati quantitativi disponibili, ognuno con la sua fonte.",
            "Individuare con precisione le lacune e gli archivi in cui colmarle.",
        ],
        "key_dates": [
            {"date": "1957-03-25", "event": "Firma dei Trattati di Roma: il Trattato CEE istituisce il Fondo Sociale Europeo (art. 123 e seguenti)", "source": "Wikidata Q167457; Oireachtas, Report No. 10 – Youth Employment, Appendix, 3/5/1978"},
            {"date": "1960-08-31", "event": "Pubblicazione nella Gazzetta Ufficiale (n. 56) del Regolamento n. 9 sul Fondo Sociale Europeo", "source": "Archive of European Integration (Univ. di Pittsburgh), bibliografia; citato nel Reg. (CEE) 2396/71"},
            {"date": "1971-02-01", "event": "Decisione del Consiglio 71/66/CEE sulla riforma del Fondo Sociale Europeo", "source": "Regolamento (CEE) n. 2396/71, EUR-Lex"},
            {"date": "1971-11-08", "event": "Regolamento (CEE) n. 2396/71 di attuazione della riforma", "source": "EUR-Lex, ELI reg/1971/2396"},
            {"date": "1972-05-01", "event": "Il Fondo riformato inizia a operare", "source": "Oireachtas, Report No. 10 – Youth Employment, Appendix, 3/5/1978"},
            {"date": "1977-12-20", "event": "Decisione 77/801/CEE: modifica della riforma, il Fondo si estende ai lavoratori autonomi", "source": "legislation.gov.uk, eudn 1977/801"},
            {"date": "1983-10-17", "event": "Decisione 83/516/CEE sui compiti del FSE: almeno il 75% degli stanziamenti ai giovani", "source": "Decisione 83/516/CEE (testo pubblicato)"},
            {"date": "1986-02-17", "event": "Firma dell'Atto unico europeo", "source": "Wikidata Q622649"},
        ],
        "series": [],
        "tables": [
            {
                "title": "Quota del Fondo Sociale sul bilancio della Comunità, 1973–1984",
                "as_series": {"name": "Quota del Fondo Sociale Europeo sul bilancio della Comunità", "unit": "% del bilancio", "category": "other"},
                "unit": "percentuale",
                "columns": ["Anno", "Quota (%)"],
                "rows": [["1973", "5,9"], ["1974", "6,5"], ["1975", "6,3"], ["1976", "5,8"], ["1977", "1,9"], ["1978", "4,3"], ["1979", "3,7"], ["1980", "2,3"], ["1981", "4,6"], ["1982", "5,8"], ["1983", "7,9"], ["1984", "7,2"]],
                "source": "Camera dei Comuni (Regno Unito), risposta scritta del 31 luglio 1984, HC Deb vol 65 c166W",
                "source_url": "https://api.parliament.uk/historic-hansard/written_answers/1984/jul/31/european-social-fund-1",
                "license_id": "uk_parliament",
                "notes": "Dati di spesa, non di impegno, tratti dai bilanci annuali. Il valore del 1977 riflette la revisione del Fondo di quell'anno. Per gli anni precedenti al 1973 la fonte dichiara che i dati si ottengono «solo a costo sproporzionato».",
            },
            {
                "title": "Gli altri numeri disponibili in rete",
                "unit": "",
                "columns": ["Dato", "Valore", "Fonte"],
                "rows": [
                    ["Risorse del FSE 1961–1972", "circa 420 milioni di unità di conto", "Ministero federale del Lavoro tedesco (BMAS), esf.de, «History of the ESF»"],
                    ["Assegnazioni al Regno Unito per il 1975", "45,9 milioni di sterline", "Camera dei Comuni, risposta scritta dell'11/5/1976"],
                    ["Assegnazioni al Regno Unito per il 1978", "34.846.028 sterline", "Camera dei Comuni, risposta scritta del 14/12/1978"],
                ],
                "source": "Fonti indicate riga per riga",
                "source_url": "https://www.esf.de/portal/EN/About-the-ESF/history-of-the-esf/content.html",
                "license_id": None,
                "notes": "Sono dati isolati, non serie complete: non permettono confronti tra paesi né tra anni.",
            },
        ],
        "gaps": [
            {"what": "Importi annui del Fondo per paese, 1958–1972, e numero di lavoratori aiutati", "where": "Archivi storici dell'Unione europea (Istituto universitario europeo, Firenze): fondi della Commissione, Direzione generale Affari sociali", "url": "https://archives.eui.eu"},
            {"what": "Relazioni annuali sulle attività del FSE dal 1972 (esercizio 1972 e seguenti)", "where": "Archive of European Integration, Università di Pittsburgh (documenti digitalizzati, da consultare a mano)", "url": "https://aei.pitt.edu"},
            {"what": "Testi giuridici completi (Regolamento n. 9/1960, Decisioni 71/66, 77/801, 83/516, riforma del 1988)", "where": "EUR-Lex, la banca dati ufficiale del diritto dell'UE", "url": "https://eur-lex.europa.eu"},
            {"what": "Dati dagli anni '90 in poi", "where": "Relazioni della Commissione; dati aperti dal periodo 2014–2020 nella Cohesion Open Data Platform", "url": "https://cohesiondata.ec.europa.eu"},
        ],
        "readings": [
            {"source_type": "book", "title": "The European Commission 1958-72: History and Memories", "authors": ["Dumoulin, Michel (a cura di)"], "year": 2007, "publisher": "Office for Official Publications of the European Communities"},
            {"source_type": "book", "title": "The European Commission 1973-86: History and Memories of an Institution", "authors": ["Bussière, Éric (a cura di)"], "year": 2014, "publisher": "Publications Office of the European Union"},
        ],
        "steps": [
            {"title": "Base giuridica", "detail": "Le date chiave (trattato, regolamento del 1960, riforme del 1971, 1977 e 1983) sono già eventi con la loro fonte: verificale sui testi originali in EUR-Lex.", "module": "/history"},
            {"title": "I dati che ci sono", "detail": "La quota del Fondo sul bilancio 1973–1984 è già una serie in Financial Intelligence, con la fonte della Camera dei Comuni; le altre cifre sono nell'appunto-guida.", "module": "/financial"},
            {"title": "I dati che mancano", "detail": "Per ogni lacuna elencata nell'appunto-guida annota cosa serve e in quale archivio cercarlo: è il risultato della ricerca, non un fallimento.", "module": "/documents"},
            {"title": "Ipotesi da verificare", "detail": "Usa Discovery per cercare collegamenti tra le riforme del Fondo e la disoccupazione, trattandoli sempre come ipotesi.", "module": "/discovery"},
            {"title": "Relazione", "detail": "Nel Research Studio scrivi cosa si sa, cosa non si sa e come lo si potrebbe sapere (archivi, documenti da digitalizzare).", "module": "/studio"},
        ],
    },
]

KITS_BY_ID = {k["id"]: k for k in RESEARCH_KITS}
