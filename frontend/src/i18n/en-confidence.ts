/** Confidence System: motivazioni della valutazione delle fonti (testi del server e dell'interfaccia). Vedi en.ts. */
export const EN_CONFIDENCE: Record<string, string> = {
  // Stati della scheda
  "Controllata sull'originale": 'Checked against the original', 'Metadati confermati': 'Metadata confirmed',
  "Controllata dall'utente sull'originale": 'Checked by the user against the original',
  'Metadati confermati dal registro (contenuto non controllato)': 'Metadata confirmed by the registry (content not checked)',
  // Avvisi sugli eventi
  "Le fonti collegate non hanno identità accertata (né registro né controllo sull'originale).":
    'The linked sources have no established identity (neither registry nor check against the original).',
  "Nessuna fonte indica la pagina: il sostegno dell'evento va letto nella fonte.": 'No source gives the page: support for the event must be read in the source.',
  // Bibliografia
  'Valutazione della fonte: perché': 'Source assessment: why', 'Valutazione non disponibile.': 'Assessment not available.',
  // Valutazione di una fonte
  "Metadati: confermati dal registro (Crossref): l'opera esiste ed è citata correttamente; il contenuto non è stato controllato":
    'Metadata: confirmed by the registry (Crossref): the work exists and is cited correctly; the content was not checked',
  "Metadati: controllati dall'utente sull'originale (dichiarazione dell'utente)": "Metadata: checked by the user against the original (user's statement)",
  'Metadati: DOI trovato nel registro, ma alla scheda mancano dati essenziali': 'Metadata: DOI found in the registry, but the record lacks essential data',
  "Metadati: DOI trovato ma i metadati del registro non corrispondono alla scheda: identità dell'opera dubbia":
    'Metadata: DOI found but the registry metadata do not match the record: identity of the work doubtful',
  "Metadati: Identificativo non trovato nel registro: identità dell'opera dubbia": 'Metadata: identifier not found in the registry: identity of the work doubtful',
  'Metadati: non controllati': 'Metadata: not checked',
  'Autorevolezza: raccolta compilativa ({0}), da usare come punto di partenza verso le fonti citate':
    'Authority: compilation ({0}), to be used as a starting point towards the sources it cites',
  'Autorevolezza: editore o ente istituzionale': 'Authority: institutional publisher or body',
  'Autorevolezza: pubblicazione editoriale o accademica (editore non riconosciuto come istituzionale)':
    'Authority: editorial or academic publication (publisher not recognised as institutional)',
  'Autorevolezza: documento, archivio o dataset di un ente non riconosciuto come istituzionale':
    'Authority: document, archive or dataset from a body not recognised as institutional',
  'Autorevolezza: pagina web o tipo di fonte non specificato': 'Authority: web page or unspecified source type',
  'Originalità: primaria (indicata in bibliografia)': 'Originality: primary (stated in the bibliography)',
  'Originalità: secondaria (indicata in bibliografia)': 'Originality: secondary (stated in the bibliography)',
  'Originalità: primaria (dedotta dal tipo di fonte)': 'Originality: primary (inferred from the source type)',
  'Originalità: secondaria (dedotta dal tipo di fonte)': 'Originality: secondary (inferred from the source type)',
  'Originalità: non indicata': 'Originality: not stated', 'Originalità: terziaria (compilazione di altre fonti)': 'Originality: tertiary (compilation of other sources)',
  "Originalità: riprende un'altra fonte indicata in bibliografia (non è una conferma indipendente di quella)":
    'Originality: draws on another source listed in the bibliography (not an independent confirmation of it)',
  'Provenienza della scheda: {0}': 'Record provenance: {0}', 'importazione automatica «{0}»': 'automatic import “{0}”',
  "Data: pubblicata prima dell'evento, può documentare il contesto ma non l'evento": 'Date: published before the event, it can document the context but not the event',
  // Valutazione di un insieme di fonti
  'Fonti: nessuna fonte bibliografica collegata': 'Sources: no bibliography source linked',
  "Indipendenza: {0} fonti utilizzabili in {1} gruppi indipendenti (alcune hanno un'origine comune)": 'Independence: {0} usable sources in {1} independent groups (some share an origin)',
  'Indipendenza: {0} fonti utilizzabili in {1} gruppi indipendenti': 'Independence: {0} usable sources in {1} independent groups',
  'Origine comune: «{0}» e «{1}»: {2}': 'Common origin: “{0}” and “{1}”: {2}',
  'stessa opera o stessa fonte primaria dichiarata': 'same work or same declared primary source', 'autore in comune ({0})': 'shared author ({0})',
  'stessa raccolta compilativa ({0})': 'same compilation ({0})',
  'Escluse: {0} fonti con identità dubbia (DOI non trovato o metadati discordanti)': 'Excluded: {0} sources of doubtful identity (DOI not found or mismatching metadata)',
  'Qualità: {0} gruppi contengono una fonte con identità accertata e autorevolezza almeno media': 'Quality: {0} groups contain a source with established identity and at least medium authority',
  "Metadati: {0} fonti senza identità accertata (né registro né controllo dell'utente)": "Metadata: {0} sources without established identity (neither registry nor user's check)",
  "Ancoraggio: nessun collegamento indica la pagina o il passaggio a sostegno dell'affermazione": 'Anchoring: no link gives the page or passage supporting the claim',
  'Ancoraggio: {0} collegamenti indicano pagina o passaggio (da leggere: indicarli non prova il sostegno)': 'Anchoring: {0} links give a page or passage (to be read: giving them does not prove support)',
  'Contraddizioni: {0} rilevate': 'Contradictions: {0} found',
  "Contenuto: NEXUS non controlla che le fonti sostengano l'affermazione. La verifica dei metadati riguarda solo l'identità dell'opera; il sostegno va accertato leggendo la fonte.":
    "Content: NEXUS does not check that the sources support the claim. Metadata verification only concerns the work's identity; support must be established by reading the source.",
  // Verifica delle ipotesi
  '{0} fonti in {1} gruppi indipendenti; {2} gruppi con una fonte con identità accertata e autorevolezza almeno media. Controllo sulle fonti, non sul contenuto: va letto se sostengono il legame.':
    '{0} sources in {1} independent groups; {2} groups with a source of established identity and at least medium authority. A check on the sources, not on the content: read them to see whether they support the link.',
  '{0} fonti in {1} gruppi indipendenti; {2} gruppi con una fonte con identità accertata e autorevolezza almeno media; {3} escluse per identità dubbia. Controllo sulle fonti, non sul contenuto: va letto se sostengono il legame.':
    '{0} sources in {1} independent groups; {2} groups with a source of established identity and at least medium authority; {3} excluded for doubtful identity. A check on the sources, not on the content: read them to see whether they support the link.',
};
