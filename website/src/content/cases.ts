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
];

export const CASES_BY_SLUG = Object.fromEntries(CASES.map((c) => [c.slug, c])) as Record<string, CaseArticle>;
