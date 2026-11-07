# NEXUS — Historical & Financial Intelligence Platform

Piattaforma che collega ricerca storica, dati economici, documenti e analisi
quantitativa in un archivio di conoscenza verificabile. Funziona in locale,
offline e a costo zero; può essere eseguita come servizio multi-utente.

**Stato: fasi 1–8 implementate e testate** (vedi [`docs/ROADMAP.md`](docs/ROADMAP.md)).

## Moduli
| | Modulo | Cosa fa |
|---|---|---|
| A | Historical Intelligence | Eventi con date (anche a.C.), cause, conseguenze, attori, fonti e attendibilità |
| B | Financial Intelligence | Serie da World Bank, Eurostat, OWID, FRED (con chiave) e CSV; rendimenti, volatilità, drawdown, ADF, correlazioni |
| C | Time Machine | Cronologia a una data con filtro anti-senno-di-poi |
| D | Knowledge Graph | Entità e relazioni con provenienza obbligatoria (fonte, passaggio o ipotesi) |
| E | Research War Room | Ricerca multi-agente supervisionata, locale o con provider AI dell'utente |
| F | Economic Laboratory | Monte Carlo, debito pubblico, sensitività, inflazione, regole di Taylor, regressioni, backtest senza look-ahead |
| G | Research Studio | Rapporti in 10 sezioni con citazioni verificabili, grafici, tabelle, export PDF/DOCX; Daily Briefing |
| H | NEXUS Business | Account, sessioni, condivisione progetti, piani e limiti, area amministratore |

Trasversali: archivio documenti (PDF, DOCX, CSV, XLSX, TXT, MD) con ricerca
testuale BM25 + semantica e risposte con citazioni; bibliografia con verifica DOI
su Crossref; registro attività; notifiche; ricerca globale; dashboard personalizzabile.

## Principi
- **Budget 0 €**: solo software open-source; ogni servizio esterno è facoltativo.
- **Nessun dato inventato**: ciò che manca viene dichiarato; i dati DEMO sono etichettati.
- **Fatti ≠ ipotesi**: ogni affermazione è tipizzata (fatto documentato, interpretazione,
  ipotesi, stima, dato mancante); l'AI non può promuovere un'ipotesi a fatto.
- **Supervisione**: eliminazioni, condivisioni e approvazioni richiedono conferma esplicita;
  ogni operazione è nel registro attività. NEXUS non esegue operazioni finanziarie.
- **Documenti = dati**: i contenuti importati non sono mai trattati come istruzioni.

## Requisiti
Python ≥ 3.11 (testato con 3.13), Node.js ≥ 20 (testato con 22).

**Windows:** installa Python da https://www.python.org/downloads spuntando «Add python.exe to PATH»,
Node.js LTS da https://nodejs.org e Git da https://git-scm.com, poi usa il terminale **Git Bash**
(va bene anche MSYS2/UCRT64). Gli script trovano da soli il Python ufficiale di Windows.

## Avvio rapido
```bash
cd nexus
scripts/setup.sh          # dipendenze, migrazioni, npm install
scripts/dev.sh            # backend 127.0.0.1:8000 · frontend http://127.0.0.1:5173
```
Documentazione API interattiva: http://127.0.0.1:8000/docs

```bash
scripts/py.sh scripts/seed_demo.py          # dati DEMO etichettati (progetti, eventi senza fonti)
scripts/py.sh scripts/backup_db.py          # backup consistente in nexus/backups/
scripts/py.sh scripts/generate_briefing.py  # Daily Briefing (programmabile con cron)
```

### Modalità multi-utente (SaaS)
```bash
NEXUS_AUTH_MODE=multi NEXUS_SECRET_KEY="…" scripts/dev.sh
```
Il primo account registrato diventa amministratore. In produzione: HTTPS davanti al
backend, `NEXUS_COOKIE_SECURE=true`, PostgreSQL consigliato.

### AI (facoltativa)
Da **Sistema → Credenziali** configura uno tra: Ollama (locale, gratuito),
un endpoint compatibile OpenAI, Anthropic API (a pagamento, modello predefinito
`claude-opus-5-5`). Poi selezionalo in **Sistema → Provider AI**. Senza provider,
la War Room lavora in modalità locale e dichiara gli agenti non eseguiti.

## Novità

- **Discovery Intelligence** (nuova sezione): connessioni tra eventi, serie ed entità, ipotesi con verifica, anomalie,
  catene causali e scenari, con evidenze e fonti. Architettura e limiti in [`docs/DISCOVERY.md`](docs/DISCOVERY.md).

- **Fonti BCE e ISTAT** (oltre a World Bank, FRED, Eurostat, OWID): in Financial Intelligence → Importa serie → Da fonte aperta, indica dataflow e chiave SDMX.
- **Avvisi sulle serie**: nella pagina di una serie, «Avvisi» (nuovo dato o soglia superata). Per controllarli in automatico pianifica
  `scripts/py.sh scripts/check_alerts.py` (cron su Linux/macOS, Utilità di pianificazione su Windows: istruzioni nello script).
- **Collaborazione**: nei progetti, icona commenti → commenti e cronologia delle modifiche (la condivisione richiede la modalità multi-utente).
- **LaTeX e BibTeX**: nello Studio, export «LaTeX» (ZIP per Overleaf con main.tex e references.bib); in Bibliografia, import/export BibTeX
  (Zotero, Mendeley, JabRef). Le fonti importate entrano come non verificate.
- **Lezioni guidate**: crisi del 1929, inflazione anni '70, crisi del 2008.
- **App installabile (PWA)**: dalla build di produzione servita in HTTPS o su localhost, il browser offre «Installa app».
  Su iPhone, Safari → Condividi → «Aggiungi a Home» funziona anche dalla rete locale.

## Test
```bash
scripts/test.sh                                                     # pytest + typecheck + vitest
NEXUS_URL=http://127.0.0.1:5173 node scripts/check_responsive.cjs   # E2E responsive (app avviata)
```

## Struttura
```
nexus/
├── backend/nexus/
│   ├── api/            router REST e schemi Pydantic (schemas_*.py per modulo)
│   ├── core/           configurazione, errori, logging, registro moduli, piani
│   ├── database/       engine, sessioni, migrazioni programmatiche
│   ├── models/         tabelle ORM
│   ├── services/       logica applicativa (un file per area)
│   ├── research/       estrazione, segmentazione, indici, citazioni, sicurezza contenuti
│   ├── history/        date storiche
│   ├── finance/        connettori e analisi
│   ├── agents/         provider AI, prompt, guardie, workflow multi-agente
│   ├── simulations/    modelli del laboratorio
│   ├── studio/         citazioni, grafici, export PDF/DOCX
│   ├── security/       identità, password, cifratura, rate limit
│   ├── billing/        interfaccia pagamenti (nessun pagamento attivo)
│   └── integrations/   registro fonti e verifica raggiungibilità
├── backend/migrations/ Alembic (0001–0008)
├── backend/tests/      pytest
├── frontend/src/       React + TypeScript (api, components, pages, state, test)
├── docs/               architettura, roadmap, API
└── scripts/            setup, avvio, test, seed, backup, briefing, test responsive
```

## Website

The public website lives in [`website/`](website/README.md).
