/** Testi rimasti in italiano dopo le Fasi 1–3 (frammenti accanto a valori, suggerimenti, voci di menu). Vedi en.ts. */
export const EN_RITOCCHI: Record<string, string> = {
  'Biblioteca': 'Library', 'del': 'on',
  // Ambito e progetto
  'Ambito:': 'Scope:', '· si cambia dalla barra in alto': '· change it from the bar at the top',
  'ricerche nella War Room': 'War Room research runs', '· Rapporti:': '· Reports:', '{0} elementi dalla Biblioteca ·': '{0} items from the Library ·',
  'modifica': 'edit', 'lettura': 'read only', 'Collegato:': 'Linked:',
  // Ricerca e selettori
  'Posizione del passaggio nella classifica della ricerca, rispetto al primo risultato. Non dice se il passaggio risponde.':
    'Position of the passage in the search ranking, relative to the top result. It does not say whether the passage answers.',
  'Quota dei concetti della domanda (anche tradotti) presenti nel passaggio.': 'Share of the question\'s concepts (including translations) found in the passage.',
  '· mancano:': '· missing:',
  'I concetti devono comparire insieme nella stessa frase. Stima lessicale: il significato va verificato leggendo la frase.':
    'The concepts must appear together in the same sentence. Lexical estimate: check the meaning by reading the sentence.',
  'Nessun risultato': 'No results', 'Nessun risultato tra le tue voci': 'No results among your items',
  'Scrivi almeno': 'Type at least', 'caratteri per cercare anche nella Biblioteca.': 'characters to search the Library too.',
  // Account: integrità dei file
  'mai eseguito': 'never run', 'ultimo controllo {0} ({1})': 'last check {0} ({1})',
  'file ·': 'files ·', 'documenti': 'documents', 'nel cestino · documenti senza file:': 'in trash · documents without a file:',
  '· file orfani:': '· orphan files:', '· dimensioni diverse:': '· size mismatches:', '· contenuto alterato:': '· altered content:',
  '(su': '(of', 'verificati con SHA-256) · cestino scaduto:': 'checked with SHA-256) · expired trash:',
  // Bibliografia
  'DOI esistente': 'DOI exists', 'DOI non trovato': 'DOI not found', '· confronto con': '· compared with', 'Interrogato:': 'Queried:',
  '· licenza nel registro: {0}': '· licence in registry: {0}', 'Provenienza:': 'Provenance:',
  'Es. CC BY 4.0, pubblico dominio, tutti i diritti riservati': 'E.g. CC BY 4.0, public domain, all rights reserved',
  'Da dove vengono questi metadati (catalogo, archivio, import)': 'Where these metadata come from (catalogue, archive, import)',
  ': controlla che il DOI esista su Crossref e confronta campo per campo titolo, autori, anno e rivista. Un DOI esistente con metadati discordanti non è mai una fonte verificata.':
    ': checks that the DOI exists on Crossref and compares title, authors, year and journal field by field. An existing DOI with mismatching metadata is never a verified source.',
  // Discovery
  "Base dell'ipotesi:": 'Basis of the hypothesis:',
  '. Correlazione, associazione temporale, ipotesi e causalità sono livelli diversi: «causalità documentata» richiede una relazione causale con fonte nel Knowledge Graph.':
    '. Correlation, temporal association, hypothesis and causality are different levels: "documented causality" requires a sourced causal relation in the Knowledge Graph.',
  '(non ancora possibile)': '(not possible yet)', 'Confermata (non ancora possibile)': 'Confirmed (not possible yet)',
  'Per confermare servono almeno due controlli a favore, di cui uno documentario (passaggi nei documenti, fonti indipendenti o relazioni con fonte nel grafo). Una correlazione, anche robusta, da sola non basta.':
    'Confirming requires at least two supporting checks, one of them documentary (passages in documents, independent sources or sourced relations in the graph). A correlation alone, however robust, is not enough.',
  'Ultima modifica:': 'Last edited:', ". L'esito precedente è decaduto: verifica di nuovo.": '. The previous result has expired: verify again.',
  'Informazioni mancanti (una per riga)': 'Missing information (one per line)', 'Metodo di verifica (uno per riga)': 'Verification method (one per line)',
  // Documenti
  '· eliminato': '· deleted', 'file non recuperabile': 'file not recoverable', 'recuperabile fino al {0}': 'recoverable until {0}',
  // Grafo
  'Motivazione:': 'Rationale:', 'Proposta dalla ricerca #': 'Proposed by research run #',
  // Historical Intelligence
  'Disponibile dal (anno)': 'Available from (year)', 'Fatto del (AAAA-MM-GG)': 'Fact date (YYYY-MM-DD)', 'Pubblicata il (AAAA-MM-GG)': 'Published on (YYYY-MM-DD)',
  "Tre date distinte: quando è avvenuto il fatto, quando il dato o il documento è stato pubblicato, da quando l'informazione era disponibile.":
    'Three separate dates: when the fact happened, when the data or document was published, and since when the information was available.',
  // Laboratorio
  'Obbligatorio per serie mensili, trimestrali…': 'Required for monthly, quarterly… series', '— (serie annuale)': '— (annual series)',
  "Media dell'anno": 'Annual mean', "Somma dell'anno": 'Annual sum', "Ultimo valore dell'anno": 'Last value of the year',
  'Scarto degli scenari (± crescita)': 'Scenario spread (± growth)', 'Base = crescita storica della serie': 'Baseline = historical growth of the series',
  'Scenario ottimistico: «parametro: valore»': 'Optimistic scenario: "parameter: value"', 'Scenario pessimistico: «parametro: valore»': 'Pessimistic scenario: "parameter: value"',
  'NEXUS non propone valori: elasticità, tassi e valori di partenza vanno presi da fonti e citati nel rapporto.':
    'NEXUS does not suggest values: elasticities, rates and starting values must come from sources and be cited in the report.',
  'Valori calcolati:': 'Computed values:', "l'anno": 'a year', ', dati della serie).': ', series data).',
  'Rispetto a «': 'Compared with "', '» a fine orizzonte:': '" at the end of the horizon:', 'a fine orizzonte': 'at the end of the horizon',
  '{0} a fine orizzonte': '{0} at the end of the horizon', '· Effetto dello shock a fine orizzonte:': '· Shock effect at the end of the horizon:',
  'Crescita storica di riferimento:': 'Reference historical growth:',
  // Lezioni
  'Unità:': 'Unit:', 'Dove:': 'Where:',
  // Research Studio
  'Modifiche non salvate: restano qui anche se cambi sezione, finché non premi «Salva sezione».':
    'Unsaved changes: they stay here even if you switch section, until you press "Save section".',
  'Questa sezione è stata modificata altrove (per esempio con «Cita nel rapporto») mentre avevi modifiche non salvate: qui vedi la tua bozza. Salvandola sostituisci la versione salvata.':
    'This section was changed elsewhere (for example with "Cite in report") while you had unsaved changes: you are seeing your draft. Saving it replaces the saved version.',
  'Usa la versione salvata': 'Use the saved version', 'Nessuna versione precedente: la cronologia parte dal primo salvataggio.': 'No previous versions: history starts from the first save.',
  'parole': 'words', '{0} parole · {1} citazioni': '{0} words · {1} citations',
  'affermazioni rilevanti:': 'relevant claims:', 'con fonte nella frase,': 'with a source in the sentence,', 'con fonte nel paragrafo,': 'with a source in the paragraph,',
  'senza supporto': 'unsupported', '. Citazioni con pagina:': '. Citations with page:', '. Fonti citate:': '. Sources cited:',
  'Fonti citate:': 'Sources cited:', 'primarie,': 'primary,', 'secondarie': 'secondary', ', {0} da classificare': ', {0} to classify',
  '(senza pagina)': '(no page)', 'da sistemare': 'to fix', 'primaria': 'primary', 'secondaria': 'secondary',
  // Time Machine
  '(dato del': '(data for', ', data di pubblicazione sconosciuta': ', publication date unknown', ', pubblicato nel {0}': ', published in {0}',
  ', scaricato il {0}': ', downloaded on {0}', "[Disponibile all'epoca ·": '[Available at the time ·', 'Fonte successiva (': 'Later source (',
  '[Acquisita dopo ·': '[Acquired later ·', 'Fonte:': 'Source:',
  // War Room
  'Tentativo': 'Attempt', 'di 3': 'of 3',
  '· ripresa dalle fasi già completate ({0}): nessun lavoro perso': '· resumed from completed phases ({0}): no work lost',
};
