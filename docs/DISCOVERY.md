# NEXUS Discovery Intelligence — architettura

Livello di analisi avanzata costruito **sopra** i moduli esistenti: non duplica database,
motore di ricerca, grafo o modelli di simulazione, li interroga.

## Fase 1 — Analisi dell'esistente (riutilizzato)

| Esistente | Dove | Uso in Discovery |
|---|---|---|
| FastAPI + SQLAlchemy 2 + Alembic (SQLite/PostgreSQL) | `backend/nexus` | Stesso database, nuova migrazione `0010` |
| Knowledge Graph (NetworkX, provenienza obbligatoria) | `services/graph.py` | Componente G: esteso con nuovi tipi, deduplicazione, nodi serie/ipotesi |
| Archivio eventi con attori, paesi, categorie, fonti, affidabilità | `models/history.py` | Connessioni tra eventi, incongruenze cronologiche |
| Serie con provenienza + analisi (anomalie robuste, ADF) | `finance/analytics.py` | Anomalie, associazioni statistiche, scenari |
| Ricerca ibrida nei documenti (BM25 + semantica) | `services/research.py` | Verifica delle ipotesi: passaggi che citano entrambi gli elementi |
| Bootstrap Monte Carlo | `simulations/models.py` (stesso principio) | Scenari del Foresight sulle variazioni |
| Client AI facoltativo, guard JSON, limiti | `agents/llm.py`, `agents/guard.py`, `services/ai.py` | Sintesi facoltativa, con limite di chiamate |
| Esecuzione in background (War Room) | `services/warroom.py` | Sessioni di discovery con pausa/ripresa |
| Notifiche, registro attività, piani | `services/notifications.py`, `activity.py`, `core/plans.py` | Esito sessioni, tracciabilità |

## Fase 2 — Componenti

```
            ┌──────────────────── A. Intelligence Core (core.py) ─────────────────────┐
 domanda ──▶│ comprende → scompone in passi → esegue con limiti → deduplica → sintetizza │──▶ sessione
 autonoma   └──┬───────────┬──────────────┬───────────────┬──────────────┬──────────────┘
               ▼           ▼              ▼               ▼              ▼
     B. Discovery    C. Hypothesis   D. Anomaly     E. Causal       F. Foresight
     connections.py  hypotheses.py   anomalies.py   causal.py       foresight.py
               └───────────┴──── evidence.py (valutazione fonti, indipendenza) ──┘
                                        │
                         G. Knowledge Graph (kg.py → services/graph.py)
```

- **evidence.py** — classificazione (fatto documentato, interpretazione, ipotesi, previsione, non verificato) e
  valutazione delle fonti: autorevolezza, originalità (primaria/secondaria), data, pertinenza, **indipendenza**
  (fonti raggruppate per opera e per fonte primaria dichiarata: dieci articoli che riprendono la stessa fonte
  contano come una conferma), contraddizioni.
- **connections.py** — quattro rilevatori deterministici, ognuno con tipo di relazione esplicito:
  attori condivisi tra eventi, riferimento testuale (le cause di B citano A), percorsi nel grafo (vicini comuni),
  coincidenza evento–cambiamento nei dati, associazione statistica tra serie (variazioni, ritardi, p-value).
  Nessuno produce una relazione causale: la causalità resta un'ipotesi da verificare.
- **hypotheses.py** — da una connessione a un'ipotesi completa (motivazione, evidenze a favore e contro, dati
  mancanti, metodo di verifica, confidenza), stati `da verificare → in verifica → confermata/respinta/inconcludente`.
  La decisione finale è sempre dell'utente.
- **anomalies.py** — variazioni anomale (z robusto), deviazioni dal trend, discrepanze tra fonti sullo stesso
  indicatore, incongruenze cronologiche. Sotto le soglie minime di dati non segnala nulla e lo dice.
- **causal.py** — catene nel grafo con ogni anello classificato (causale documentata / causale ipotizzata /
  associazione), cause alternative e cause comuni; catene di trasmissione tra serie con correlazioni ritardate.
- **foresight.py** — tre scenari (ottimistico, centrale, avverso) dal bootstrap a blocchi delle variazioni storiche:
  le bande sono i percentili 10/50/90 del modello, dichiarati come tali; nessun'altra probabilità.
- **core.py** — sessioni guidate (domanda) o autonome, eseguite a passi con limiti di tempo, passi e chiamate AI;
  pausa, ripresa, arresto; deduplicazione tramite impronte; piste di approfondimento.

## Dati

Nuove tabelle: `discovery_sessions`, `discovery_connections`, `discovery_hypotheses`, `discovery_anomalies`,
`discovery_analyses` (catene causali e scenari salvati). Estensioni: `entities.series_id`,
`sources.primary_source_id`, nuovi tipi di entità e relazione.

## Limiti dichiarati

- Le connessioni sono candidate da verificare, non scoperte.
- La sintesi AI è facoltativa; senza provider si usa la sintesi locale (marcata come tale).
- La qualità dipende dall'archivio dell'utente: con pochi eventi, serie o fonti i risultati sono pochi, e la
  sessione lo segnala.

## Stato dell'implementazione (novembre 2026)

| Componente | Stato | Note |
|---|---|---|
| A. Intelligence Core | Implementato | Sessioni guidate e autonome in background; pausa/ripresa/arresto tra i passi; limiti di tempo, chiamate AI e risultati; recupero delle sessioni interrotte da un riavvio |
| B. Discovery Engine | Implementato | 5 rilevatori; attori troppo comuni ignorati; misure dello stesso fenomeno escluse; finestre temporali reali per serie irregolari |
| C. Hypothesis Generator | Implementato | Ipotesi da regole (non da AI); verifica automatica con 4 controlli; esito deciso dall'utente con motivazione obbligatoria |
| D. Anomaly Detection | Implementato in parte | Variazioni anomale, deviazioni dal trend, discrepanze tra fonti, incongruenze cronologiche. Non implementato: «eventi con caratteristiche ricorrenti» come anomalia dedicata |
| E. Causal Intelligence | Implementato | Catene nel grafo con classificazione per anello, cause alternative e comuni; catene di trasmissione tra serie |
| F. Strategic Foresight | Implementato | Bootstrap univariato: le variabili non sono modellate congiuntamente |
| G. Knowledge Graph | Esteso | Nuovi tipi (organizzazione, sistema economico, fenomeno, concetto, ipotesi) e relazioni; deduplicazione per nome/alias; nodi per serie e ipotesi |
| Valutazione fonti | Implementato in parte | Autorevolezza, originalità, data, indipendenza, contraddizioni. La pertinenza non è un punteggio separato: è data dall'ambito della ricerca |

Servizi esterni: nessuno obbligatorio. Un provider AI (Ollama, compatibile OpenAI o Anthropic) migliora
l'interpretazione della domanda e la sintesi. Non esiste un'API di ricerca web: le evidenze vengono solo
dall'archivio dell'utente (documenti, bibliografia, eventi, serie, grafo).
