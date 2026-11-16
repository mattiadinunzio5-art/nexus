# NEXUS — Controllo generale (16 novembre 2026)

Controllo dopo i lavori del 15–16 novembre: Fasi 1–3, separazione Biblioteca, Confidence System, Causal Engine e
Scenario Simulator. Criterio: una funzionalità è «funzionante» solo se è stata **usata** (test automatici, flussi reali
su un server in esecuzione, verifica nel browser o online), non perché esiste nel codice.

## Moduli richiesti e loro corrispondenza nel codice

| Nome richiesto | Che cosa esiste in NEXUS |
|---|---|
| Intelligence Core | Sessioni della Discovery (`discovery/core.py`) e coda persistente della War Room (`services/jobs.py`, `agents/workflow.py`) |
| Intelligence Graph | Knowledge Graph (`services/graph.py`) |
| Deep Research | Ask the Archive (`services/research.py`), ricerche della War Room, tracciabilità dei rapporti (Research Studio) |
| Temporal Intelligence | Time Machine (`services/timemachine.py`) e tre date distinte su eventi e conoscenze |
| Causal Engine | Catene causali e di trasmissione (`discovery/causal.py`), Strategic Foresight, Economic Laboratory |
| Confidence System | `discovery/evidence.py` e valutazione delle fonti in Bibliografia |
| Knowledge Memory | **Non esiste un modulo con questo nome.** Il ruolo è svolto da: progetti e ambito di progetto, documenti indicizzati, note, conoscenze datate degli eventi, registro attività, ricerca globale |

## Test eseguiti

| Controllo | Esito |
|---|---|
| Server, suite completa su SQLite | **368/368** superati (369 con il test aggiunto oggi) |
| Server, suite completa su PostgreSQL 16 (come online) | **368/368** superati |
| App: controllo dei tipi (TypeScript) | nessun errore |
| App: test (Vitest) | **72/72** superati |
| App: build di produzione | riuscita (avviso: un file JavaScript supera 500 kB) |
| Sito pubblico: test e build | **15/15** superati, build riuscita |
| Flussi end-to-end su un server reale (`scripts/e2e_moduli.py`) | **43/43** controlli superati, nessun errore nel log del server |
| Browser sull'app con quei dati: 18 pagine dei moduli | tutte caricate con i dati attesi; 115 chiamate API riuscite, 0 fallite; nessun errore JavaScript |
| Database online: versione delle migrazioni | 0021, allineata al codice |
| Database online: errori PostgreSQL nelle ultime 24 ore | nessuno |
| Server online: `/api/health/deep` | database, ricerca e coda funzionanti |
| GitHub Actions su `main` | test verdi; i 7 fallimenti in elenco sono push intermedi su rami già corretti prima dell'unione |

Flussi end-to-end, per modulo:
- **Knowledge Memory, 6/6:** progetto, documento indicizzato, nota collegata, ricerca globale anche italiano → inglese, registro attività.
- **Deep Research, 5/5:**
  - risposta sostenuta a una domanda in italiano su un documento inglese;
  - nessuna risposta inventata quando le fonti mancano;
  - tracciabilità e controllo del rapporto.
- **Intelligence Core, 7/7:**
  - ricerca della War Room messa in coda, completata dal worker, approvata e trasformata in rapporto;
  - sessione di Discovery completata.
- **Confidence System, 6/6:**
  - valutazione per dimensioni;
  - identità ≠ contenuto;
  - connessione trovata dalla Discovery con le motivazioni separate;
  - due opere di Friedman contano come una sola conferma.
- **Temporal Intelligence, 6/6:** la Time Machine al 1935 mostra le conoscenze del 1929 e tiene separate quelle del 1963; al 1970 le mostra.
- **Intelligence Graph, 5/5:**
  - nodo per ogni evento;
  - relazioni documentate e ipotizzate;
  - duplicati e «documentata senza fonte» rifiutati;
  - percorso tra nodi.
- **Causal Engine, 8/8:**
  - catena con anello documentato e ipotizzato, la cui forza è quella dell'anello più debole;
  - trasmissione = correlazione;
  - scenari con dipendenze, note sui buchi e riproducibilità;
  - bootstrap con impronta dei dati.

## Sicurezza

| Controllo | Esito |
|---|---|
| Accesso senza login alle rotte protette, online (lettura e scrittura) | 401 |
| Richieste da un'origine estranea (CORS) | rifiutate |
| Intestazioni di sicurezza (CSP, HSTS, X-Frame-Options, nosniff, Referrer-Policy) | presenti su app e server |
| Isolamento tra utenti e sola lettura della Biblioteca | coperti dai test (`test_isolation`, `test_discovery_library`) |
| Segreti nel codice (chiavi API, token, chiavi private) | nessuno trovato |
| Dipendenze Python (`pip-audit`) | nessuna vulnerabilità nota |
| Dipendenze dell'app e del sito (`npm audit`) | 2 moderate in React Router 6 (link e redirect costruiti con input dell'utente). In NEXUS ogni link costruito da dati è un percorso interno generato dal server con ID numerici: non sfruttabile. La correzione richiede React Router 7 |
| Supabase: 39 tabelle con RLS attivo e nessuna policy | avviso informativo: l'API pubblica di Supabase non vede quelle tabelle; il server accede direttamente. È lo stato sicuro |
| Supabase: protezione dalle password compromesse | **disattivata** (impostazione manuale, vedi «Problemi aperti») |

## Problemi trovati e risolti

1. **Ricerca italiano → inglese incompleta su un termine centrale.**
   - Problema: «fallimenti bancari» non trovava i documenti su «bank failures», e Ask the Archive rispondeva «non sostenuta». Mancavano nel glossario «fallimento/i», «bancari/e» e alcune espressioni («fallimenti bancari», «corsa agli sportelli», «panico bancario», «insolvenza»).
   - Correzione: voci aggiunte, esplicite e verificabili come le altre.
   - Test: aggiunto; fallisce senza la correzione.
2. **Il server online si addormentava.**
   - Problema: il workflow GitHub «Sveglia backend» (ogni 10 minuti) è stato eseguito solo 2 volte in circa 8 ore, perché GitHub salta spesso i workflow pianificati frequenti. Sul piano gratuito di Render il server si spegne dopo 15 minuti, e il primo utente aspetta fino a un minuto.
   - Correzione: un job pianificato nel database (Supabase `pg_cron` + `pg_net`) chiama `/api/health` ogni 10 minuti. Il workflow GitHub resta come riserva.
   - Per rimuovere il job: `select cron.unschedule('nexus-wake-backend');`.
3. **Controllo end-to-end ripetibile.** I flussi usati per questo controllo sono in `scripts/e2e_moduli.py`.

## Problemi aperti

| Priorità | Problema | Che cosa serve |
|---|---|---|
| **Alta** | L'**AI condivisa con tutti gli utenti è attiva e usa la chiave OpenAI (ChatGPT) dell'amministratore**, che è a pagamento: 4 utenti attivi × 10 richieste al giorno | Sostituire la chiave con Groq (gratuito) in Impostazioni, oppure disattivare «Attiva per tutti». Decisione dell'amministratore |
| Media | Protezione dalle password compromesse disattivata in Supabase | Attivarla a mano (`docs/SICUREZZA.md`) |
| Media | Le 342 connessioni della Discovery sulla Biblioteca hanno l'affidabilità calcolata con le regole precedenti al Confidence System | Rieseguire la Discovery sulla Biblioteca (sostituisce i risultati attuali). L'ultima esecuzione completa ha richiesto più di un workflow GitHub da 6 ore |
| Bassa | React Router 6: 2 vulnerabilità moderate non sfruttabili in NEXUS | Passaggio a React Router 7, da pianificare |
| Bassa | ESLint non è configurato nel progetto | Configurarlo, se si vuole un controllo dello stile del codice |
| Bassa | Il file JavaScript principale dell'app supera 500 kB | Divisione del codice per pagina, se il caricamento iniziale diventa lento |
| Bassa | Glossario italiano ↔ inglese: copre il dominio, ma ogni termine mancante va aggiunto a mano | Arricchirlo quando i test con gli studenti trovano altri termini |
| Bassa | Strategic Foresight segnala le dipendenze tra variabili ma non le simula | Bootstrap sincrono (vedi `docs/CAUSAL_SCENARIOS.md`) |
| Bassa | La demo pubblica è in sola lettura, quindi le analisi nuove (catene, scenari, Laboratorio) non sono provabili online senza account | Una prova manuale con un account reale dopo ogni pubblicazione |

## Prossime priorità

1. Spostare l'AI condivisa su Groq (o disattivarla) e attivare la protezione delle password in Supabase.
2. Rieseguire la Discovery sulla Biblioteca con le nuove regole del Confidence System.
3. Prova d'uso con uno studente sull'app online, con il proprio account, su catene causali, scenari e Laboratorio.
4. Pianificare React Router 7 e la configurazione di ESLint.
