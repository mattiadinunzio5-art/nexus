/** Causal Engine e Scenario Simulator: origine delle relazioni, dati mancanti, dipendenze, riproducibilità. Vedi en.ts. */
export const EN_CAUSAL: Record<string, string> = {
  // Classi degli anelli e origine delle relazioni
  'Relazione causale documentata': 'Documented causal relation', 'Influenza documentata': 'Documented influence',
  'Relazione causale ipotizzata': 'Hypothesised causal relation', 'Influenza ipotizzata': 'Hypothesised influence',
  'Associazione (non causale)': 'Association (not causal)', 'Correlazione statistica': 'Statistical correlation',
  "{0} (ipotesi generata dall'AI, da verificare)": '{0} (AI-generated hypothesis, to be verified)',
  "{0} (ipotesi dell'utente)": '{0} (user hypothesis)',
  '{0} — attenzione: fonte con identità dubbia (DOI non trovato o metadati discordanti): non conta come documentata':
    '{0} — caution: source of doubtful identity (DOI not found or mismatching metadata): not counted as documented',
  "{0} anelli sono ipotesi generate dall'AI: non sono stati verificati da una persona né sostenuti da una fonte.":
    '{0} links are AI-generated hypotheses: they have not been checked by a person nor supported by a source.',
  '{0} anelli hanno una fonte con identità dubbia e sono stati trattati come ipotesi.': '{0} links have a source of doubtful identity and were treated as hypotheses.',
  '«Documentata» significa che una fonte è collegata alla relazione: NEXUS non verifica che la fonte la sostenga davvero.':
    '“Documented” means a source is linked to the relation: NEXUS does not check that the source actually supports it.',
  // Catene di trasmissione
  'Correlazioni calcolate sulle variazioni tra periodi consecutivi, alla frequenza comune più bassa, con p-value corretti per i ritardi provati e per il numero di passaggi della catena (Bonferroni).':
    'Correlations computed on changes between consecutive periods, at the lowest common frequency, with p-values adjusted for the lags tried and for the number of steps in the chain (Bonferroni).',
  'Un anticipo temporale non dimostra un effetto: entrambe le serie possono seguire un fattore comune.': 'A lead in time does not prove an effect: both series may follow a common factor.',
  '{0} ({1} variazioni escluse perché a cavallo di periodi mancanti).': '{0} ({1} changes excluded because they span missing periods).',
  // Dati mancanti
  '«{0}»: {1} variazioni escluse perché a cavallo di periodi mancanti (i buchi non vengono colmati).':
    '“{0}”: {1} changes excluded because they span missing periods (gaps are not filled).',
  '«{0}»: osservazioni a intervalli irregolari, variazioni calcolate tra osservazioni successive.': '“{0}”: observations at irregular intervals, changes computed between successive observations.',
  '«{0}»: {1} osservazioni senza valore ignorate.': '“{0}”: {1} observations without a value ignored.',
  '«{0}»: {1} variazioni tra periodi consecutivi, ne servono almeno {2}.': '“{0}”: {1} changes between consecutive periods, at least {2} are needed.',
  // Strategic Foresight: legami tra le variabili
  'Legami storici tra le variabili': 'Historical links between variables',
  'Correlazione delle variazioni nello stesso periodo. Il modello simula ogni variabile da sola: questi legami servono a capire se gli estremi degli scenari possono verificarsi insieme.':
    'Correlation of changes in the same period. The model simulates each variable on its own: these links help judge whether the scenario extremes can occur together.',
  'poco coerente con gli scenari estremi': 'hardly consistent with the extreme scenarios',
  'In passato si sono mosse in senso opposto a quanto assumono gli scenari ottimistico e avverso: è improbabile che i loro estremi si verifichino insieme.':
    'In the past they moved opposite to what the optimistic and adverse scenarios assume: their extremes are unlikely to occur together.',
  'Legame storico compatibile con gli scenari estremi.': 'Historical link consistent with the extreme scenarios.',
  'Nessun legame statisticamente significativo nel periodo comune.': 'No statistically significant link in the common period.',
  'Periodo comune insufficiente per stimare il legame.': 'Common period too short to estimate the link.',
  '«{0}» e «{1}»: variazioni storicamente correlate (r = {2}, n = {3}) in senso opposto a quello combinato negli scenari estremi, che quindi sono poco coerenti per questa coppia.':
    '“{0}” and “{1}”: historically correlated changes (r = {2}, n = {3}) in the opposite direction to the one combined in the extreme scenarios, which are therefore hardly consistent for this pair.',
  'Riproducibilità: seme {0}, {1} traiettorie, blocchi di {2}, numpy {3}; impronta dei dati: {4}.':
    'Reproducibility: seed {0}, {1} paths, blocks of {2}, numpy {3}; data fingerprint: {4}.',
  // Laboratorio
  'Riproducibilità': 'Reproducibility', 'Seme {0} · {1}': 'Seed {0} · {1}', 'Impronta dei dati «{0}»: {1}': 'Data fingerprint “{0}”: {1}',
  'Stessi parametri, stesso seme e stessa impronta dei dati = stesso risultato.': 'Same parameters, same seed and same data fingerprint = same result.',
  "Incertezza: shock normali su tasso e crescita, correlati tra loro ma indipendenti da un anno all'altro (nessuna persistenza)":
    'Uncertainty: normal shocks to rate and growth, correlated with each other but independent from one year to the next (no persistence)',
  '{0} estrazioni della crescita nominale sotto −99% sono state portate a −99%: la deviazione standard indicata è troppo ampia per il modello.':
    '{0} draws of nominal growth below −99% were set to −99%: the standard deviation given is too large for the model.',
  '{0} periodi senza dati per tutte le variabili nel periodo comune: le variazioni a cavallo sono escluse':
    '{0} periods without data for all variables in the common period: changes spanning them are excluded',
  'Solo {0} rendimenti tra periodi consecutivi: ne servono almeno 23.': 'Only {0} returns between consecutive periods: at least 23 are needed.',
};
