# Biblioteca NEXUS — dati aperti condivisi

La **Biblioteca NEXUS** raccoglie dati aperti importati da fonti pubbliche, con **fonte e licenza registrate per ogni
elemento**. Appartiene a un utente di sistema (`external_id = nexus-library`, non può accedere) ed è:

- **visibile a tutti gli utenti** accanto ai propri dati (eventi, Time Machine, grafo, serie, bibliografia, documenti,
  ricerca globale, «Ask the Archive»), con l'etichetta **LIBRARY**;
- **in sola lettura**: modificarla o eliminarla dall'app restituisce `403 read_only`. I filtri `origin=mine|library`
  nelle liste separano i due archivi.

I principi del progetto valgono anche qui: nessun dato inventato, fatti ≠ ipotesi, buchi lasciati come buchi.

## Importare

```bash
scripts/py.sh scripts/backup_db.py                          # prima di tutto, un backup
scripts/py.sh scripts/import_data.py series   --limit 20    # prova piccola
scripts/py.sh scripts/import_data.py all --profile online   # tutto, con i limiti per il database online
scripts/py.sh scripts/import_data.py all --profile full     # tutto, senza limiti (computer locale)
scripts/py.sh scripts/import_data.py events --resume        # riprende un import interrotto
scripts/py.sh scripts/import_data.py stats                  # conteggi e dimensione del database
scripts/py.sh scripts/import_data.py delete --origin wikidata --yes   # cancella un lotto (solo Biblioteca)
```

Il database è quello di `NEXUS_DATABASE_URL` nel file `.env`. Per riempire la versione online si lancia lo script dal
proprio computer con l'indirizzo del database Supabase (Project Settings → Database → Connection string, modalità
*Session pooler*), scritto **solo** nel file `.env` locale, mai in chat né nei commit.

### Senza usare il computer: GitHub Actions

Il workflow **«Import Biblioteca NEXUS»** (`.github/workflows/import-library.yml`) esegue lo stesso script su GitHub.
Una volta sola, in GitHub → Settings → Secrets and variables → Actions, si aggiungono i segreti copiati dalle variabili
di Render: `NEXUS_DATABASE_URL`, `NEXUS_SUPABASE_URL`, `NEXUS_SUPABASE_SERVICE_KEY`. Poi Actions → Import Biblioteca
NEXUS → *Run workflow*. Ogni esecuzione dura al massimo ~6 ore: se l'import non è finito, si rilancia e riparte da dove
era arrivato (gli elementi già presenti vengono saltati). I log degli errori sono scaricabili tra gli *artifact*.

Ogni area è **idempotente** (colonne `origin` + `external_id`, migrazione `0012`), **riprendibile** (`--resume`, stato
in `data/imports/*.state.json`), con **cache su disco** (`data/cache`), pause tra le richieste e **log degli errori**
(`data/imports/*.errors.log`). Gli elementi non riusciti non vengono segnati come fatti: `--resume` li riprova.

| Profilo | Serie | Eventi | Entità grafo | Fonti bibliografiche | Documenti |
|---|---|---|---|---|---|
| `online` (database da 500 MB) | 3.500 | 25.000 | 80.000 | 400 | 25 |
| `full` (locale) | senza limite | senza limite | senza limite | 2.000 | 80 |

## Fonti e licenze

| Area | Fonte | Licenza / termini | Note |
|---|---|---|---|
| Serie | World Bank WDI (15 indicatori, tutti i paesi) | CC BY 4.0 per la maggior parte dei dataset ([termini](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets)) | prima G20, Italia, Spagna e UE |
| Serie | Our World in Data: Maddison Project 2023 (PIL pro capite di lungo periodo), popolazione, speranza di vita | OWID CC BY; Maddison Project Database 2023 CC BY 4.0 ([pagina](https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023)) | solo paesi (codice ISO a 3 lettere); un download per dataset; anni prima di Cristo esclusi (fuori dal calendario delle serie) |
| Serie | Eurostat (debito pubblico, disoccupazione, inflazione HICP; UE27) | riuso consentito con attribuzione ([avviso](https://ec.europa.eu/eurostat/help/copyright-notice)) | |
| Serie | BCE (tassi di cambio mensili) | [condizioni BCE](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html) | saltata se non raggiungibile |
| Eventi, grafo | Wikidata | CC0 1.0 | classi verificate per etichetta all'avvio |
| Descrizioni | Wikipedia in inglese (estratto di 2 frasi) | CC BY-SA 4.0, con attribuzione nella fonte | |
| Bibliografia | Crossref, Open Library | metadati aperti | DOI verificati con la verifica esistente |
| Documenti | Project Gutenberg (mirror `gutenberg.pglaf.org`) | pubblico dominio negli USA + licenza Project Gutenberg | 10 classici, titolo controllato nel file |

**Non importati**: FRED (richiede una chiave personale), ISTAT (aggiungibile dalla pagina Financial Intelligence),
Bank of England «A millennium of macroeconomic data» (cartella Excel complessa: da valutare a parte), IMF/OECD/BIS
(connettori non attivi).

## Regole per gli eventi (Wikidata)

- Classi: guerre, guerre civili, battaglie, assedi, trattati, rivoluzioni, colpi di stato, ribellioni, crisi finanziarie,
  bancarie e di borsa, crisi economiche, recessioni, iperinflazioni, crisi valutarie e del debito, default sovrani,
  corse agli sportelli, riforme monetarie, carestie; più le **fondazioni** di banche centrali, borse, stati storici e imperi.
- **Copertura equilibrata**: a turno l'elemento più citato di ogni secolo, finché si raggiunge il limite.
- **Date**: l'endpoint SPARQL usa anni astronomici (0 = 1 a.C.) e date gregoriane: si convertono gli anni e, prima del
  1583, si conserva **solo l'anno** per non riportare giorni convertiti di calendario. La precisione è nella nota.
- **Affidabilità**: `unverified`; `probable` solo con almeno due riferimenti distinti nella voce; **mai** `established`.
- **Cause/conseguenze**: solo dalle proprietà P828 «ha causa» e P1542 «ha effetto», dichiarandolo nel testo.
- **Time Machine**: nessuna «informazione datata» generata (Wikidata e Wikipedia non sono fonti coeve). Con la
  Biblioteca la Time Machine mostra per default una finestra di 25 anni prima della data scelta.

## Knowledge Graph

Entità da Wikidata: economisti e banchieri, stati sovrani e storici, imperi, banche centrali e banche, borse, compagnie
commerciali e privilegiate, organizzazioni internazionali, teorie e scuole economiche, sistemi economici. Più un'entità
«indicatore» per ogni serie della Biblioteca (collegata con `series_id`, usata da Discovery).

Relazioni **solo** da proprietà Wikidata tra elementi importati, con `provenance = sourced`, confidenza `medium` e nota
con proprietà e voci (es. `Q123 P828 (has cause) → Q456`): P828, P1542, P361, P155/P156, P710, P607, P1365/P1366,
P112, P8324, P859, P737, P793. Nessuna ipotesi AI.

Per ragioni di scala le entità e le relazioni della Biblioteca sono scritte in blocco (con validazione `EntityIn`,
deduplica per QID e una voce di registro attività per lotto): il controllo di duplicati per nome di `create_entity`
scorre tutte le entità a ogni inserimento e non è praticabile su decine di migliaia di elementi. Eventi e fonti passano
invece dai servizi (`create_event`, `create_source`, `link_source`).

## Discovery

`import_data.py discovery` esegue sulla Biblioteca solo i rilevatori **deterministici** (connessioni evento-dato,
anomalie). I risultati appartengono alla Biblioteca e si consultano nelle pagine Discovery con il selettore
**«Il mio archivio | Biblioteca NEXUS»** (API: `?origin=library` su connessioni, ipotesi, anomalie e sessioni; la
panoramica li conta in `library`). Sono in **sola lettura**: accettare, scartare, verificare o decidere restituisce
`403 read_only`. Le liste predefinite restano quelle dell'archivio personale.

Su archivi grandi (oltre 1.500 eventi o 2.000 nodi del grafo) i rilevatori non confrontano più «tutti con tutti», che
sulla Biblioteca significava centinaia di milioni di coppie e un workflow fermato dopo 6 ore. Si confrontano solo le
coppie che possono dare un risultato, trovate con indici: attori condivisi, termini rari del titolo citati nel testo,
vicini comuni nel grafo, eventi dello stesso paese, serie dello stesso indicatore. I test verificano che i risultati
siano identici al confronto completo. Due limiti, solo per gli archivi grandi:

- un attore presente in più di 200 eventi è trattato come «comune» (come già accade a quelli presenti in metà degli
  eventi) e non genera connessioni;
- un nodo del grafo con più di 300 collegamenti non genera coppie candidate, ma conta nel punteggio delle coppie trovate.

La sessione Discovery della Biblioteca ha un limite di 3 ore (invece di 120 secondi) e conserva fino a 300 risultati per tipo (invece di 60).

## Prestazioni

Con la Biblioteca le liste sono paginate (`limit`/`offset`), il grafo si esplora con visite in ampiezza via SQL
(massimo 4.000 relazioni per vista) invece di caricare l'intero grafo in memoria, e la Time Machine usa una finestra
temporale. Dimensioni e tempi misurati sono riportati nel report di consegna.
