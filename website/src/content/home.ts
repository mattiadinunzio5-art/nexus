/** Testi della home (6 sezioni): brevi, per essere letti fino in fondo. */
export interface HomeText {
  why: { label: string; title: string; points: { title: string; text: string }[] };
  mods: { label: string; title: string; intro: string; items: { slug: string; title: string; text: string }[]; archive: string };
  how: { label: string; title: string; steps: { title: string; text: string }[] };
  case29: { label: string; title: string; text: string; bullets: string[]; demo: string; lessons: string; caption: string };
  trust: string;
}

export const HOME_IT: HomeText = {
  why: {
    label: 'Perché NEXUS',
    title: 'Storia ed economia nello stesso posto, con le fonti sempre visibili.',
    points: [
      { title: 'Ogni fatto ha una fonte', text: 'Eventi, dati e collegamenti dicono sempre da dove vengono, con licenza e stato di verifica.' },
      { title: 'Fatti e ipotesi restano separati', text: 'L’AI e Discovery propongono collegamenti, ma un’ipotesi non diventa mai un fatto da sola.' },
      { title: 'Niente dati inventati', text: 'I buchi restano buchi: NEXUS non stima e non riempie, ti dice dove cercare.' },
    ],
  },
  mods: {
    label: 'I moduli',
    title: 'Sette moduli, un unico archivio.',
    intro: 'Ogni modulo ha una guida completa: aprila per vedere cosa fa e come si usa.',
    items: [
      { slug: 'historical-intelligence', title: 'Historical Intelligence', text: 'Eventi con date, cause, conseguenze e fonti. Con la Time Machine li vedi senza il senno di poi.' },
      { slug: 'financial-intelligence', title: 'Financial Intelligence', text: 'Serie ufficiali (Banca Mondiale, Eurostat, BCE, Maddison) con grafici, statistiche e licenza.' },
      { slug: 'knowledge-graph', title: 'Knowledge Graph', text: 'Persone, istituzioni ed eventi collegati: ogni legame ha una fonte o è un’ipotesi dichiarata.' },
      { slug: 'discovery-intelligence', title: 'Discovery', text: 'Propone connessioni e anomalie tra eventi e dati, sempre da verificare.' },
      { slug: 'research-war-room', title: 'Research War Room', text: 'Più agenti AI lavorano sulle tue evidenze, con una controanalisi critica.' },
      { slug: 'economic-laboratory', title: 'Economic Laboratory', text: 'Simulazioni e scenari con ipotesi esplicite: modelli, non previsioni.' },
      { slug: 'research-studio', title: 'Research Studio', text: 'Rapporti con citazioni verificabili, esportabili in PDF, Word e LaTeX.' },
    ],
    archive: 'In più, l’archivio: documenti, bibliografia con verifica dei DOI e domande alle tue fonti.',
  },
  how: {
    label: 'Come funziona',
    title: 'Da una domanda a un rapporto, in quattro passi.',
    steps: [
      { title: 'Parti dai dati', text: 'Esplora la Biblioteca NEXUS (18.000 eventi, 3.500 serie ufficiali) o importa i tuoi documenti.' },
      { title: 'Costruisci la cronologia', text: 'Ogni evento con le sue fonti e il suo grado di attendibilità.' },
      { title: 'Collega e verifica', text: 'Knowledge Graph, Discovery e Time Machine: collegamenti con fonte, ipotesi dichiarate.' },
      { title: 'Scrivi', text: 'Un rapporto con citazioni verificabili, pronto da esportare.' },
    ],
  },
  case29: {
    label: 'Un caso reale',
    title: 'Il crollo di Wall Street del 1929, modulo per modulo.',
    text: 'Due minuti e mezzo per vedere NEXUS al lavoro su una crisi vera: l’evento con le sue fonti, il Dow Jones da 381 a 41 punti, il 1930 visto senza il senno di poi, le ipotesi da verificare, fino al rapporto esportato.',
    bullets: ['Fonti: Friedman e Schwartz, Kindleberger, Galbraith', 'Dati: FRED e NBER Macrohistory Database', 'Nessuna registrazione per provare la demo'],
    demo: 'Prova la demo',
    lessons: 'Altre lezioni guidate: inflazione degli anni ’70, crisi del 2008',
    caption: 'Video della lezione guidata sul crollo del 1929: dalle fonti al rapporto (2 minuti e mezzo, in italiano)',
  },
  trust: 'Fonti e licenze di ogni dato',
};

export const HOME_EN: HomeText = {
  why: {
    label: 'Why NEXUS',
    title: 'History and economics in one place, with sources always visible.',
    points: [
      { title: 'Every fact has a source', text: 'Events, data and links always state where they come from, with licence and verification status.' },
      { title: 'Facts and hypotheses stay separate', text: 'AI and Discovery suggest links, but a hypothesis never becomes a fact on its own.' },
      { title: 'No invented data', text: 'Gaps stay gaps: NEXUS does not estimate or fill them, it tells you where to look.' },
    ],
  },
  mods: {
    label: 'The modules',
    title: 'Seven modules, one archive.',
    intro: 'Each module has a full guide: open it to see what it does and how to use it.',
    items: [
      { slug: 'historical-intelligence', title: 'Historical Intelligence', text: 'Events with dates, causes, consequences and sources. The Time Machine shows them without hindsight.' },
      { slug: 'financial-intelligence', title: 'Financial Intelligence', text: 'Official series (World Bank, Eurostat, ECB, Maddison) with charts, statistics and licence.' },
      { slug: 'knowledge-graph', title: 'Knowledge Graph', text: 'People, institutions and events linked: every link has a source or is a declared hypothesis.' },
      { slug: 'discovery-intelligence', title: 'Discovery', text: 'Suggests connections and anomalies between events and data, always to be checked.' },
      { slug: 'research-war-room', title: 'Research War Room', text: 'Several AI agents work on your evidence, with a critical counter-analysis.' },
      { slug: 'economic-laboratory', title: 'Economic Laboratory', text: 'Simulations and scenarios with explicit assumptions: models, not forecasts.' },
      { slug: 'research-studio', title: 'Research Studio', text: 'Reports with verifiable citations, exportable to PDF, Word and LaTeX.' },
    ],
    archive: 'Plus the archive: documents, a bibliography with DOI checks, and questions to your sources.',
  },
  how: {
    label: 'How it works',
    title: 'From a question to a report, in four steps.',
    steps: [
      { title: 'Start from data', text: 'Explore the NEXUS Library (18,000 events, 3,500 official series) or import your own documents.' },
      { title: 'Build the timeline', text: 'Every event with its sources and reliability.' },
      { title: 'Link and check', text: 'Knowledge Graph, Discovery and Time Machine: sourced links, declared hypotheses.' },
      { title: 'Write', text: 'A report with verifiable citations, ready to export.' },
    ],
  },
  case29: {
    label: 'A real case',
    title: 'The 1929 Wall Street crash, module by module.',
    text: 'Two and a half minutes to see NEXUS at work on a real crisis: the event with its sources, the Dow Jones from 381 to 41 points, 1930 seen without hindsight, hypotheses to check, up to the exported report.',
    bullets: ['Sources: Friedman and Schwartz, Kindleberger, Galbraith', 'Data: FRED and the NBER Macrohistory Database', 'No sign-up needed to try the demo'],
    demo: 'Try the demo',
    lessons: 'More guided lessons: 1970s inflation, the 2008 crisis',
    caption: 'Video of the guided lesson on the 1929 crash: from sources to report (2.5 minutes, in Italian)',
  },
  trust: 'Sources and licences of every data point',
};
