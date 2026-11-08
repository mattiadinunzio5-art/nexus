/** Workflow, caso di studio e capacità in italiano: stessi fatti della versione inglese. */
import type { CaseVisual } from './story';
import type { ModuleSlug } from './modules';

export const WORKFLOW_IT: { step: string; detail: string; slug: ModuleSlug }[] = [
  { step: 'Domanda di ricerca', detail: 'Formula cosa vuoi capire.', slug: 'projects' },
  { step: 'Creazione del progetto', detail: 'Dai alla domanda una casa e un perimetro.', slug: 'projects' },
  { step: 'Raccolta dei documenti', detail: 'Importa i testi e i dataset su cui ti basi.', slug: 'documents' },
  { step: 'Bibliografia', detail: 'Registra e verifica ogni fonte.', slug: 'bibliography' },
  { step: 'Analisi finanziaria e storica', detail: 'Importa le serie, costruisci la cronologia.', slug: 'financial-intelligence' },
  { step: 'Time Machine', detail: 'Leggi il passato senza il senno di poi.', slug: 'time-machine' },
  { step: 'Knowledge Graph', detail: 'Collega attori, eventi e fenomeni.', slug: 'knowledge-graph' },
  { step: 'Ricerca AI', detail: 'Gli agenti analizzano, contestano e sintetizzano.', slug: 'research-war-room' },
  { step: 'Simulazione economica', detail: 'Prova scenari con ipotesi esplicite.', slug: 'economic-laboratory' },
  { step: 'Research Studio', detail: 'Struttura i risultati e citali.', slug: 'research-studio' },
  { step: 'Rapporto finale', detail: 'Approva ed esporta in PDF, DOCX o LaTeX.', slug: 'research-studio' },
];

export const CASE_STUDY_IT: { phase: string; slug: ModuleSlug; explain: string; example: string; visual: CaseVisual }[] = [
  {
    phase: 'Creazione del progetto',
    slug: 'projects',
    explain: 'La domanda viene divisa in tre filoni: cause, contagio, alternative.',
    example: 'Progetto «Dentro la crisi finanziaria del 2008», periodo 2001–2012, con un appunto per filone.',
    visual: 'project',
  },
  {
    phase: 'Raccolta dei documenti',
    slug: 'documents',
    explain: 'Rapporti ufficiali, articoli accademici e i tuoi appunti entrano nell’archivio e diventano ricercabili fino alla pagina.',
    example: 'Importi i rapporti e gli articoli che hai selezionato; chiedendo «Cosa ha bloccato il mercato interbancario?» ottieni citazioni localizzate da quei testi.',
    visual: 'documents',
  },
  {
    phase: 'Analisi finanziaria',
    slug: 'financial-intelligence',
    explain: 'Tassi, rendimenti, crescita e disoccupazione vengono importati con la loro provenienza e confrontati sulle variazioni, non sui livelli.',
    example: 'Serie FRED come FEDFUNDS e DGS10 (chiave gratuita), il tasso BCE sulle operazioni principali e la crescita del PIL USA dalla World Bank, analizzati per drawdown e volatilità.',
    visual: 'chart',
  },
  {
    phase: 'Ricostruzione storica',
    slug: 'historical-intelligence',
    explain: 'Gli eventi chiave vengono registrati con date, istituzioni, cause e fonti.',
    example: 'Eventi come il salvataggio di Bear Stearns (marzo 2008) e l’istanza di fallimento di Lehman Brothers (15 settembre 2008), ognuno collegato a fonti che verifichi tu.',
    visual: 'timeline',
  },
  {
    phase: 'Time Machine',
    slug: 'time-machine',
    explain: 'L’archivio viene visto a una data per separare ciò che si sapeva allora da ciò che si è capito dopo.',
    example: 'Imposta l’anno 2007: gli eventi successivi e le conseguenze retrospettive sono nascosti, e gli indicatori si fermano al 2007.',
    visual: 'clock',
  },
  {
    phase: 'Knowledge Graph',
    slug: 'knowledge-graph',
    explain: 'Banche, regolatori, strumenti ed eventi vengono collegati, ogni legame con la sua prova o etichettato come ipotesi.',
    example: 'Un’istituzione collegata a un evento da una relazione documentata; un canale di contagio che sospetti inserito come ipotesi tratteggiata.',
    visual: 'graph',
  },
  {
    phase: 'Research War Room',
    slug: 'research-war-room',
    explain: 'Gli agenti cercano nell’archivio, analizzano le serie, si contestano a vicenda e producono affermazioni tipizzate da approvare.',
    example: 'Lo scettico segnala un’affermazione basata su un solo documento e una correlazione presentata come causalità.',
    visual: 'agents',
  },
  {
    phase: 'Economic Laboratory',
    slug: 'economic-laboratory',
    explain: 'Gli scenari alternativi vengono esplorati come ipotesi esplicite ed etichettate.',
    example: 'Uno scenario controfattuale sul debito con un percorso dei tassi diverso — chiaramente marcato «scenario ipotetico», mai una ricostruzione di ciò che sarebbe successo.',
    visual: 'fan',
  },
  {
    phase: 'Research Studio',
    slug: 'research-studio',
    explain: 'Risultati, grafici e citazioni vengono assemblati in un rapporto approvabile solo quando ogni citazione è valida.',
    example: 'Un rapporto in dieci parti esportato in PDF o LaTeX, con riferimenti numerati e fonti non verificate segnalate.',
    visual: 'report',
  },
];

export const CAPABILITIES_IT: { title: string; text: string; slug: ModuleSlug }[] = [
  { title: 'Ricerca storica', text: 'Eventi strutturati con date a precisione variabile, fonti e affidabilità, e una vista nel tempo senza senno di poi.', slug: 'historical-intelligence' },
  { title: 'Financial Intelligence', text: 'Dati economici aperti da World Bank, Eurostat, BCE, ISTAT e FRED con provenienza completa, avvisi, rendimenti, volatilità, drawdown, test di stazionarietà e confronti onesti.', slug: 'financial-intelligence' },
  { title: 'Mappe della conoscenza', text: 'Un grafo di persone, istituzioni, eventi e idee in cui ogni relazione porta con sé la sua prova.', slug: 'knowledge-graph' },
  { title: 'Ricerca AI', text: 'Ricerca multi-agente supervisionata con affermazioni tipizzate, contro-analisi e approvazione obbligatoria.', slug: 'research-war-room' },
  { title: 'Simulazione economica', text: 'Monte Carlo, dinamica del debito, regole di politica monetaria, regressioni e backtest senza informazioni dal futuro, ipotesi comprese.', slug: 'economic-laboratory' },
  { title: 'Intelligenza documentale', text: 'Ricerca per parole chiave e semantica nel tuo archivio, con risposte fatte di citazioni letterali e localizzate.', slug: 'documents' },
  { title: 'Discovery Intelligence', text: 'Connessioni candidate, ipotesi con verifica, anomalie, catene causali e scenari — costruiti sul tuo archivio, con evidenze e fonti.', slug: 'discovery-intelligence' },
  { title: 'Rapporti di ricerca', text: 'Rapporti in dieci parti con citazioni verificabili, grafici e tabelle, esportati in PDF, DOCX e LaTeX.', slug: 'research-studio' },
];
