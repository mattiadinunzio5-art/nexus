# NEXUS — Causal Engine e Scenario Simulator: analisi, correzioni, limiti

Verifica del 16 novembre 2026. Moduli esaminati:
- **Causal Engine:** `discovery/causal.py` (catene nel grafo, catene di trasmissione), `discovery/connections.py`
  (associazioni tra serie, eventi e dati), `discovery/anomalies.py`, `discovery/hypotheses.py` (livello dell'evidenza);
- **Scenario Simulator:** `discovery/foresight.py` (Strategic Foresight), `simulations/models.py`, `simulations/engine.py`,
  `simulations/sectors.py`, `services/lab.py` (Economic Laboratory);
- **Dati:** `finance/analytics.py` (preparazione delle serie).

## 1. Correlazione, causalità documentata, ipotesi: com'è distinta

| Livello | Dove nasce | Come appare |
|---|---|---|
| **Correlazione statistica** | associazioni tra serie, catene di trasmissione, regressione del laboratorio | sempre «correlazione» o «associazione»; la regressione dichiara «associazione statistica, non causalità» |
| **Associazione temporale** | evento seguito da una variazione insolita dei dati | «la coincidenza temporale merita una verifica» |
| **Relazione causale documentata** | relazione del grafo di tipo causale con fonte collegata | «documentata»; da oggi solo se la fonte non ha identità dubbia |
| **Ipotesi dell'utente** | relazione inserita come ipotesi | «ipotizzata (ipotesi dell'utente)» |
| **Ipotesi generata dall'AI** | relazioni proposte dalla War Room o dalla Discovery | «ipotizzata (ipotesi generata dall'AI, da verificare)» |

Regole già presenti e verificate:
- un'ipotesi della Discovery diventa «causalità documentata» solo se è confermata dall'utente e se nel grafo c'è una
  relazione causale con fonte;
- la sola statistica non permette mai di confermare un'ipotesi;
- la forza di una catena è quella dell'anello più debole.

## 2. Problemi trovati e correzioni

| # | Problema | Correzione |
|---|---|---|
| 1 | **Dati mancanti.** In una serie regolare con periodi mancanti, la variazione tra le osservazioni ai due lati del buco (es. 1989→1995) era trattata come variazione di un periodo: correlazioni, scenari, bootstrap, regressione in differenze e rilevamento delle anomalie la vedevano come un salto | `analytics.changes`: variazioni solo tra periodi consecutivi; quelle a cavallo di un buco sono escluse e contate. Le serie irregolari per costruzione (es. date dei cambiamenti di un tasso: spaziatura mediana > 1,5 volte la frequenza) restano come prima, ma lo si dichiara. La regressione lavora su un calendario regolare, così differenze e ritardi non scavalcano i buchi |
| 2 | **Scenari su serie che crescono di ordini di grandezza** (PIL dal 1950, prezzi): lo Strategic Foresight ricampionava variazioni assolute, così le variazioni piccole dei primi decenni pesavano quanto le recenti | Variazioni percentuali (log) quando la serie è positiva e spazia su più di un ordine di grandezza (×20), come già nel resto della Discovery; il risultato indica il tipo di variazioni usato |
| 3 | **Dipendenze tra variabili.** Gli scenari ottimistico e avverso combinano gli estremi di variabili simulate separatamente, anche quando in passato non si muovevano insieme in quel senso | Per ogni coppia di variabili si riporta la correlazione storica delle variazioni nello stesso periodo. Se è significativa (p ≤ 0,05) e di segno opposto a quello che gli scenari estremi assumono, la coppia è segnalata come «poco coerente con gli scenari estremi». **Il modello non usa queste dipendenze**: è una descrizione del passato |
| 4 | **Origine delle relazioni causali.** Nelle catene, le ipotesi dell'AI e quelle dell'utente avevano la stessa etichetta | Ogni anello indica l'origine (fonte, utente, AI); le note contano gli anelli proposti dall'AI e ricordano che «documentata» non significa «verificata nel contenuto» |
| 5 | **Fonti dubbie.** Una relazione «con fonte» contava come documentata anche se la fonte aveva identità dubbia (DOI inesistente o metadati discordanti) | Scende a «ipotizzata», con nota. Nelle catene di trasmissione il passaggio resta una correlazione |
| 6 | **Test multipli nelle catene di trasmissione.** Il p-value era corretto per i ritardi provati, non per il numero di passaggi | Correzione di Bonferroni anche per il numero di passaggi (`p_adj_chain`), usata per dire «significativa» |
| 7 | **Riproducibilità.** Il seme era salvato, ma non c'era modo di sapere se i dati erano gli stessi | Ogni simulazione e ogni scenario registrano seme, generatore (PCG64 di numpy), versione di numpy e un'impronta (SHA-256 abbreviato) di date e valori di ogni serie usata. Stessi parametri, seme e impronta danno lo stesso risultato |
| 8 | **Debito pubblico con incertezza.** L'ipotesi che gli shock siano indipendenti da un anno all'altro non era dichiarata, e le estrazioni di crescita sotto −99% venivano corrette in silenzio | Ipotesi dichiarata; il numero di estrazioni corrette compare tra gli avvisi |

Non sono stati introdotti modelli nuovi. Le tecniche usate (variazioni tra periodi consecutivi, variazioni
logaritmiche, correlazione di Pearson sulle variazioni, correzione di Bonferroni) erano già nel codice o sono standard.

## 3. Assunzioni dei modelli (dichiarate nei risultati)

- **Strategic Foresight:**
  - bootstrap a blocchi di 3 periodi delle variazioni storiche, 2000 traiettorie, seme 7;
  - ogni variabile è simulata da sola;
  - non produce shock più grandi di quelli già osservati e ignora i cambi strutturali;
  - bande ai percentili 10/50/90, senza probabilità attribuite agli scenari.
- **Catene di trasmissione:**
  - correlazione delle variazioni alla frequenza comune più bassa, ritardi da −4 a +4;
  - un anticipo temporale non dimostra un effetto.
- **Monte Carlo (moto browniano geometrico):** rendimenti normali indipendenti, drift e volatilità costanti.
- **Bootstrap del laboratorio:** blocchi di rendimenti storici; non genera eventi più estremi di quelli osservati.
- **Debito pubblico:**
  - modello contabile, senza retroazioni (tassi → crescita, debito → spread);
  - con incertezza: shock normali correlati tra tasso e crescita, indipendenti nel tempo.
- **Regressione:**
  - OLS con errori standard HAC (Newey-West);
  - avviso di non stazionarietà in livelli (test ADF);
  - «associazione statistica, non causalità».
- **Proiezioni a scenari:**
  - crescita composta costante, scelta dall'utente o pari alla media storica;
  - banda log-normale con shock indipendenti.
- **Modelli settoriali:**
  - regole da manuale (produzione con vincolo di capacità, legge di Okun, elasticità del commercio, consumi);
  - i parametri vengono dall'utente, NEXUS non propone valori.

## 4. Limiti che restano

- Lo Strategic Foresight **non modella le dipendenze** tra variabili: le segnala soltanto. Un bootstrap sincrono
  (stessi blocchi temporali per tutte le variabili) le preserverebbe, ma richiede frequenze e periodi comuni ed è
  rimandato.
- Il rilevamento dei buchi si basa sulla spaziatura delle date. Una serie dichiarata con una frequenza sbagliata, o
  con buchi in più della metà dei periodi, viene trattata come irregolare.
- Nelle anomalie «evento → dati» le finestre di più periodi consecutivi sono calcolate sulle variazioni valide e
  possono ancora comprendere un buco all'interno della finestra (la variazione che lo scavalca, però, è esclusa).
- Il backtest calcola i rendimenti tra osservazioni successive: per serie di prezzi giornalieri è la convenzione
  corretta, ma un lungo periodo senza quotazioni diventa un unico rendimento.
- La legge di Okun nel modello dell'occupazione limita la disoccupazione tra 1% e 60%: il limite inferiore è segnalato
  nel risultato, quello superiore no.
- La riproducibilità vale a parità di versione di numpy. Il generatore PCG64 è stabile tra versioni, ma i metodi di
  estrazione possono cambiare; per questo la versione è registrata.
- Correlazione e test sono descrittivi: nessun metodo del Causal Engine stima effetti causali (non ci sono variabili
  strumentali, esperimenti o identificazione), e i risultati lo dicono.

## 5. Test

- `backend/tests/test_causal_scenarios.py`, 11 test:
  - buchi esclusi nelle variazioni, serie irregolari dichiarate;
  - un buco non è un'anomalia;
  - variazioni escluse riportate nelle correlazioni;
  - proiezioni percentuali per le serie in crescita;
  - coppie poco coerenti negli scenari estremi;
  - riproducibilità e impronta dei dati;
  - origine degli anelli e fonti dubbie nelle catene;
  - Bonferroni sui passaggi;
  - bootstrap e regressione del laboratorio con buchi;
  - avvisi del modello del debito.
- Frontend:
  - `reproducibility.test.ts`: riepilogo della riproducibilità nel laboratorio;
  - `i18n.test.tsx`: traduzioni inglesi delle nuove etichette.
- Risultati: server 368 test superati, app 72 test superati; controllo dei tipi e build senza errori.
