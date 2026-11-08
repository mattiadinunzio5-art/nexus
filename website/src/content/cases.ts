/**
 * Casi del mese: note di metodo bilingui. Contengono solo fatti ampiamente documentati
 * e rimandano alle fonti ufficiali; nessun dato o risultato viene presentato come scoperta.
 */
import type { ModuleSlug } from './modules';

export interface CaseText {
  title: string;
  dek: string;
  sections: { heading: string; paragraphs: string[] }[];
}

export interface CaseArticle {
  slug: string;
  date: string; // AAAA-MM
  minutes: number;
  modules: ModuleSlug[];
  sources: { label: string; url: string }[];
  en: CaseText;
  it: CaseText;
}

export const CASES: CaseArticle[] = [
  {
    slug: 'reading-2008-without-hindsight',
    date: '2026-11',
    minutes: 5,
    modules: ['time-machine', 'historical-intelligence', 'financial-intelligence'],
    sources: [
      { label: 'Financial Crisis Inquiry Commission, The Financial Crisis Inquiry Report (2011)', url: 'https://www.govinfo.gov/app/details/GPO-FCIC' },
      { label: 'ALFRED — Archival FRED, Federal Reserve Bank of St. Louis', url: 'https://alfred.stlouisfed.org/' },
      { label: 'FRED — Federal Reserve Economic Data', url: 'https://fred.stlouisfed.org/' },
    ],
    en: {
      title: 'Reading 2008 without hindsight',
      dek: 'How to separate what was knowable in the summer of 2008 from what we understood after Lehman Brothers — and why today’s data can mislead you.',
      sections: [
        {
          heading: 'The problem',
          paragraphs: [
            'Once we know how a crisis ended, every earlier signal looks obvious. This is hindsight bias, and it is the most common error in historical-economic research: judging decisions with information that did not exist when they were taken.',
            'For 2008 the trap is especially strong. The bankruptcy filing of Lehman Brothers on 15 September 2008 reorganises how we read everything before it, including the rescue of Bear Stearns in March of the same year.',
          ],
        },
        {
          heading: 'The method in NEXUS',
          paragraphs: [
            'Record the events you study in Historical Intelligence, each with its source, and add dated knowledge items: what was reported at the time, what emerged later from investigations and archives.',
            'Open the Time Machine and set the year to 2008 in strict mode. Later events and retrospective consequences disappear, and hidden items are counted rather than silently dropped. Then switch on hindsight to see exactly what was added afterwards.',
            'Write two short paragraphs in a note: one using only the strict view, one with hindsight. The difference between them is the subject of your analysis.',
          ],
        },
        {
          heading: 'The data trap',
          paragraphs: [
            'Macroeconomic series are revised. The value of a 2008 indicator that you download today is not necessarily the value that was published in 2008. NEXUS warns you about this in the Time Machine, but it cannot fix it with today’s data alone.',
            'When the question depends on what decision-makers saw at the time, use vintage data: the St. Louis Fed’s ALFRED archive keeps past releases of many FRED series. Import the vintage you need as a CSV, with ALFRED as the declared source.',
          ],
        },
        {
          heading: 'What to avoid',
          paragraphs: [
            'Do not present a correlation between series as a cause. Do not cite an event without a verifiable source. Do not treat a counterfactual scenario from the Economic Laboratory as what would have happened: it is a labelled hypothesis.',
          ],
        },
      ],
    },
    it: {
      title: 'Leggere il 2008 senza il senno di poi',
      dek: 'Come separare ciò che si poteva sapere nell’estate del 2008 da ciò che abbiamo capito dopo Lehman Brothers — e perché i dati di oggi possono ingannarti.',
      sections: [
        {
          heading: 'Il problema',
          paragraphs: [
            'Quando sappiamo come è finita una crisi, ogni segnale precedente sembra ovvio. È il senno di poi, ed è l’errore più comune nella ricerca storico-economica: giudicare decisioni con informazioni che non esistevano quando sono state prese.',
            'Per il 2008 la trappola è particolarmente forte. L’istanza di fallimento di Lehman Brothers del 15 settembre 2008 riorganizza il modo in cui leggiamo tutto ciò che viene prima, compreso il salvataggio di Bear Stearns del marzo dello stesso anno.',
          ],
        },
        {
          heading: 'Il metodo in NEXUS',
          paragraphs: [
            'Registra gli eventi che studi in Historical Intelligence, ognuno con la sua fonte, e aggiungi gli elementi di conoscenza datati: cosa si diceva all’epoca, cosa è emerso dopo da inchieste e archivi.',
            'Apri la Time Machine e imposta l’anno 2008 in modalità rigorosa. Gli eventi successivi e le conseguenze retrospettive spariscono, e gli elementi nascosti vengono contati invece di essere eliminati in silenzio. Poi attiva il senno di poi per vedere esattamente cosa è stato aggiunto dopo.',
            'Scrivi due brevi paragrafi in un appunto: uno usando solo la vista rigorosa, uno con il senno di poi. La differenza tra i due è l’oggetto della tua analisi.',
          ],
        },
        {
          heading: 'La trappola dei dati',
          paragraphs: [
            'Le serie macroeconomiche vengono riviste. Il valore di un indicatore del 2008 che scarichi oggi non è necessariamente quello pubblicato nel 2008. NEXUS te lo segnala nella Time Machine, ma con i soli dati di oggi non può correggerlo.',
            'Quando la domanda dipende da ciò che vedevano i decisori dell’epoca, usa i dati d’annata: l’archivio ALFRED della Fed di St. Louis conserva le pubblicazioni passate di molte serie FRED. Importa l’annata che ti serve come CSV, indicando ALFRED come fonte.',
          ],
        },
        {
          heading: 'Cosa evitare',
          paragraphs: [
            'Non presentare una correlazione tra serie come una causa. Non citare un evento senza una fonte verificabile. Non trattare uno scenario controfattuale dell’Economic Laboratory come ciò che sarebbe successo: è un’ipotesi etichettata.',
          ],
        },
      ],
    },
  },
  {
    slug: 'where-italian-inflation-data-comes-from',
    date: '2026-11',
    minutes: 4,
    modules: ['financial-intelligence', 'sources', 'bibliography'],
    sources: [
      { label: 'ISTAT — IstatData, consumer price indices', url: 'https://esploradati.istat.it/databrowser/' },
      { label: 'Eurostat — Harmonised Indices of Consumer Prices (HICP)', url: 'https://ec.europa.eu/eurostat/web/hicp' },
      { label: 'European Central Bank — Monetary policy strategy', url: 'https://www.ecb.europa.eu/mopo/strategy/html/index.en.html' },
      { label: 'ECB Data Portal', url: 'https://data.ecb.europa.eu/' },
    ],
    en: {
      title: 'Where Italian inflation data comes from',
      dek: 'NIC, FOI, HICP: three official measures of consumer prices in Italy. Which one to use depends on your question — and NEXUS lets you import them side by side.',
      sections: [
        {
          heading: 'Three indices, three purposes',
          paragraphs: [
            'ISTAT, the Italian national statistical institute, publishes three consumer price indices. NIC refers to the whole resident population. FOI refers to households of blue- and white-collar workers and is used, by law, to update amounts such as rents. HICP (IPCA in Italian) is harmonised across the European Union so that countries can be compared.',
            'The three measures differ in the population they represent and in how some items are treated, so their rates can diverge. None of them is “the” inflation rate: each answers a different question.',
          ],
        },
        {
          heading: 'Which one for which question',
          paragraphs: [
            'Comparing Italy with other European countries, or reading inflation against the European Central Bank’s objective, calls for the HICP: the ECB defines price stability in terms of the euro-area HICP. Studying the cost of living of Italian households points to NIC or FOI.',
          ],
        },
        {
          heading: 'How to do it in NEXUS',
          paragraphs: [
            'Financial Intelligence offers a ready series “HICP, annual average rate of change — Italy” from Eurostat, and the World Bank’s consumer price inflation for Italy. For the euro area as a whole, import the ECB series ICP M.U2.N.000000.4.ANR. For NIC and FOI, use the ISTAT connector with the dataflow and series key shown in IstatData.',
            'Then use Compare: NEXUS aligns the dates, and if frequencies differ it asks you to choose how to resample. Register each statistical release in the Bibliography so that your report cites it correctly.',
          ],
        },
      ],
    },
    it: {
      title: 'Da dove vengono i dati sull’inflazione italiana',
      dek: 'NIC, FOI, IPCA: tre misure ufficiali dei prezzi al consumo in Italia. Quale usare dipende dalla tua domanda — e NEXUS ti permette di importarle e confrontarle.',
      sections: [
        {
          heading: 'Tre indici, tre scopi',
          paragraphs: [
            'L’ISTAT pubblica tre indici dei prezzi al consumo. Il NIC si riferisce all’intera popolazione residente. Il FOI si riferisce alle famiglie di operai e impiegati ed è usato, per legge, per aggiornare importi come gli affitti. L’IPCA (HICP in inglese) è armonizzato nell’Unione europea perché i paesi si possano confrontare.',
            'Le tre misure differiscono per la popolazione rappresentata e per il trattamento di alcune voci, quindi i loro tassi possono divergere. Nessuna è «il» tasso d’inflazione: ognuna risponde a una domanda diversa.',
          ],
        },
        {
          heading: 'Quale indice per quale domanda',
          paragraphs: [
            'Per confrontare l’Italia con altri paesi europei, o per leggere l’inflazione rispetto all’obiettivo della Banca Centrale Europea, serve l’IPCA: la BCE definisce la stabilità dei prezzi in termini di HICP dell’area dell’euro. Per studiare il costo della vita delle famiglie italiane servono il NIC o il FOI.',
          ],
        },
        {
          heading: 'Come farlo in NEXUS',
          paragraphs: [
            'Financial Intelligence offre una serie pronta «HICP, variazione media annua — Italia» da Eurostat e l’inflazione dei prezzi al consumo per l’Italia della World Bank. Per l’area dell’euro nel suo insieme, importa la serie BCE ICP M.U2.N.000000.4.ANR. Per NIC e FOI usa il connettore ISTAT con il dataflow e la chiave della serie indicati in IstatData.',
            'Poi usa Confronta: NEXUS allinea le date e, se le frequenze sono diverse, ti chiede come ricampionare. Registra ogni pubblicazione statistica in Bibliography così il rapporto la cita correttamente.',
          ],
        },
      ],
    },
  },
];

export const CASES_BY_SLUG = Object.fromEntries(CASES.map((c) => [c.slug, c])) as Record<string, CaseArticle>;
