# NEXUS — Confidence System (valutazione delle fonti)

Codice: `backend/nexus/discovery/evidence.py`. Lo usano la Discovery (affidabilità delle connessioni, controllo
«Fonti indipendenti» nella verifica delle ipotesi), le schede degli eventi (avvisi sulle fonti) e la Bibliografia
(«Valutazione della fonte: perché», rotta `GET /api/sources/{id}/assessment`).

## Principio

Una fonte si valuta per **dimensioni distinte**, ognuna con la sua motivazione scritta, senza fonderle in un voto unico.
Le regole sono criteri di critica delle fonti già in uso nella ricerca storica ed economica: identità dell'opera,
tipo ed ente di pubblicazione, originalità, indipendenza delle conferme. NEXUS non introduce punteggi propri né pesi
statistici: dove non può sapere qualcosa lo dice.

## Le dimensioni di una fonte

| Dimensione | Come si valuta | Che cosa NON dice |
|---|---|---|
| **Identità e metadati** | `confirmed` se il registro esterno (Crossref, via DOI) conferma i metadati; `declared` se l'utente dichiara di averla controllata sull'originale; `incomplete`, `doubtful` (DOI inesistente o metadati discordanti), `unchecked` | Nulla sul contenuto: un DOI confermato prova che l'opera esiste ed è citata correttamente, non che sostenga l'affermazione |
| **Autorevolezza** | `high`: editore o ente istituzionale, letto da editore e rivista (mai dal titolo); `medium`: pubblicazione editoriale o accademica, oppure documento, archivio o dataset di altro ente; `low`: pagina web, tipo non indicato, raccolta compilativa | Non dipende più dalla verifica sul registro |
| **Originalità** | primaria o secondaria come indicato dall'utente in bibliografia; altrimenti dedotta dal tipo; `derived` se riprende un'altra fonte dichiarata; `tertiary` per le raccolte compilative (Wikidata/Wikipedia) | — |
| **Provenienza** | importazione automatica (es. «wikidata») e provenienza dichiarata nella scheda | — |
| **Data** | pubblicata prima dell'evento: documenta il contesto, non l'evento | — |

Una fonte è **qualificata** se ha identità accertata (`confirmed` o `declared`) e autorevolezza almeno media.
È un requisito sulla fonte, non sull'affermazione.

## Metadati ≠ affermazione

- La verifica su registro controlla l'**identità** dell'opera.
- Il controllo dell'utente «Ho verificato l'originale» è una **dichiarazione** dell'utente sulla fonte.
- Il **sostegno di un'affermazione** non è verificato da NEXUS. NEXUS segnala soltanto se il collegamento indica una
  pagina o un passaggio da leggere (ancoraggio). Ogni valutazione d'insieme termina con questa avvertenza.

Le etichette dell'interfaccia sono cambiate di conseguenza:
- «Verificata su registro» → «Metadati confermati»;
- «Verificata dall'utente» → «Controllata sull'originale».

## Indipendenza delle conferme

Due fonti contano come **una sola conferma** se:

1. sono la stessa opera (stesso DOI, ISBN, URL, oppure titolo e anno);
2. riprendono la stessa fonte primaria dichiarata in bibliografia (anche risalendo una catena di riprese);
3. hanno un autore in comune (stesso nome, normalizzato);
4. vengono dalla stessa raccolta compilativa (Wikidata/Wikipedia: ogni voce rimanda alla stessa base).

La regola è prudente: può unire fonti che sono indipendenti (per esempio due autori omonimi), mai il contrario.
Ogni unione è motivata nelle ragioni («Origine comune: «A» e «B»: autore in comune (…)»).

## Livello d'insieme (connessioni della Discovery)

- **alta**: almeno due gruppi indipendenti, ognuno con una fonte qualificata;
- **media**: un gruppo con una fonte qualificata, oppure almeno due gruppi indipendenti;
- **bassa**: altrimenti.

Correttivi, tutti dichiarati nelle ragioni:
- le fonti con identità dubbia sono escluse;
- senza pagina o passaggio indicati il livello non supera «media»;
- ogni contraddizione abbassa di un livello;
- gli eventi con affidabilità dichiarata bassa o contestata e i collegamenti intermedi ipotizzati abbassano il livello (regole già esistenti).

Le ragioni hanno un prefisso per dimensione: Indipendenza, Origine comune, Escluse, Qualità, Metadati, Ancoraggio,
Contraddizioni, Contenuto.

Nella verifica delle ipotesi, il controllo «Fonti indipendenti» è «a favore» solo con almeno due gruppi
indipendenti che contengono una fonte qualificata; il dettaglio ricorda che è un controllo sulle fonti, non sul
contenuto, ed elenca le origini comuni trovate.

## Problemi corretti (16 novembre 2026)

| Prima | Ora |
|---|---|
| Un DOI confermato da Crossref rendeva la fonte di autorevolezza «alta» (anche un blog) | La conferma riguarda solo l'identità; l'autorevolezza dipende da tipo ed editore |
| Parole come «bank» o «institute» nel **titolo** davano autorevolezza «alta» | L'ente si legge solo da editore e rivista |
| Documenti d'archivio senza ente riconosciuto finivano tra le «pagine web» | Autorevolezza media, con motivazione corretta |
| La classificazione primaria/secondaria indicata dall'utente era ignorata | Prevale su quella dedotta dal tipo |
| Ogni voce Wikidata contava come conferma indipendente | Una sola conferma per raccolta compilativa |
| Due opere dello stesso autore erano due conferme indipendenti | Una sola conferma |
| Fonti con DOI inesistente o discordante contavano nei gruppi | Escluse, con motivazione |
| «Verificata» indicava sia il controllo dei metadati sia quello dell'originale | Etichette distinte e avvertenza esplicita sul contenuto |
| Livello «alta» possibile senza alcuna pagina indicata | Al massimo «media» senza ancoraggio |

Confronto sugli stessi casi, prima e dopo:

| Caso | Prima | Ora |
|---|---|---|
| Due voci Wikidata diverse (livello) | media | bassa |
| Due libri dello stesso autore, controllati, editore universitario (livello) | alta | media |
| Articolo di editore ignoto con «Central Bank» nel titolo (autorevolezza) | alta | media |
| Blog con DOI confermato (autorevolezza) | alta | bassa |
| Due articoli di autori diversi con DOI confermato (livello) | alta | alta |

Le connessioni già salvate (comprese quelle della Discovery sulla Biblioteca) mantengono il livello calcolato con le
regole precedenti finché la discovery non viene eseguita di nuovo.

## Limiti dichiarati

- L'elenco degli enti istituzionali è un'espressione regolare su editore e rivista: può non riconoscere un ente o
  riconoscerne uno per una parola generica (es. «institute»).
- L'autore in comune si riconosce dal nome scritto nello stesso modo (dopo normalizzazione di maiuscole, accenti e
  punteggiatura): «Rossi, M.» e «Mario Rossi» restano distinti.
- NEXUS non legge le fonti per controllare il sostegno delle affermazioni e non valuta la revisione paritaria.

## Test

- `backend/tests/test_confidence.py`, 8 test:
  - identità ≠ autorevolezza ≠ contenuto;
  - autorevolezza letta dall'editore e non dal titolo;
  - classificazione dell'utente prioritaria;
  - le quattro regole di indipendenza;
  - livelli e motivazioni, compresi ancoraggio e contraddizioni;
  - ancoraggio delle connessioni tra eventi;
  - controllo «Fonti indipendenti» delle ipotesi;
  - rotta di valutazione.
- `backend/tests/test_discovery.py` e `test_history.py`: testi delle motivazioni aggiornati.
- `frontend/src/test/bibliography.test.tsx`: la valutazione si carica solo all'apertura e mostra le motivazioni.
- `frontend/src/test/i18n.test.tsx`: traduzioni inglesi delle motivazioni.
- Risultati: server 357 test superati; app 71 test superati, controllo dei tipi e build senza errori.
