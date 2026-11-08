import type { ModuleSlug } from './modules';

export const WORKFLOW: { step: string; detail: string; slug: ModuleSlug }[] = [
  { step: 'Research Question', detail: 'Formulate what you want to understand.', slug: 'projects' },
  { step: 'Project Creation', detail: 'Give the question a home and a scope.', slug: 'projects' },
  { step: 'Document Collection', detail: 'Import the texts and datasets you rely on.', slug: 'documents' },
  { step: 'Bibliography', detail: 'Register and verify every source.', slug: 'bibliography' },
  { step: 'Financial & Historical Analysis', detail: 'Import series, build the chronology.', slug: 'financial-intelligence' },
  { step: 'Time Machine', detail: 'Read the past without hindsight.', slug: 'time-machine' },
  { step: 'Knowledge Graph', detail: 'Connect actors, events and phenomena.', slug: 'knowledge-graph' },
  { step: 'AI Research', detail: 'Agents analyse, challenge and synthesise.', slug: 'research-war-room' },
  { step: 'Economic Simulation', detail: 'Test scenarios with explicit assumptions.', slug: 'economic-laboratory' },
  { step: 'Research Studio', detail: 'Structure the findings and cite them.', slug: 'research-studio' },
  { step: 'Final Report', detail: 'Approve and export to PDF, DOCX or LaTeX.', slug: 'research-studio' },
];

export type CaseVisual = 'project' | 'documents' | 'chart' | 'timeline' | 'clock' | 'graph' | 'agents' | 'fan' | 'report';

/**
 * Caso di studio dimostrativo. Contiene solo fatti storici ampiamente documentati
 * (date di eventi noti) e descrive COME l'utente lavorerebbe in NEXUS: nessun risultato
 * di analisi o simulazione viene presentato come reale.
 */
export const CASE_STUDY: { phase: string; slug: ModuleSlug; explain: string; example: string; visual: CaseVisual }[] = [
  {
    phase: 'Project creation',
    slug: 'projects',
    explain: 'The question is broken into three strands: causes, contagion, alternatives.',
    example: 'Project “Inside the 2008 Financial Crisis”, scope 2001–2012, with one note per strand.',
    visual: 'project',
  },
  {
    phase: 'Document collection',
    slug: 'documents',
    explain: 'Official reports, academic papers and your own notes enter the archive and become searchable to the page.',
    example: 'You import the reports and papers you have selected; asking “What triggered the interbank freeze?” returns located quotations from them.',
    visual: 'documents',
  },
  {
    phase: 'Financial analysis',
    slug: 'financial-intelligence',
    explain: 'Rates, yields, growth and unemployment are imported with their provenance and compared on changes, not levels.',
    example: 'FRED series such as FEDFUNDS and DGS10 (free key), the ECB main refinancing rate and World Bank GDP growth for the United States, analysed for drawdowns and volatility.',
    visual: 'chart',
  },
  {
    phase: 'Historical reconstruction',
    slug: 'historical-intelligence',
    explain: 'Key events are recorded with dates, institutions, causes and sources.',
    example: 'Events such as the rescue of Bear Stearns (March 2008) and the bankruptcy filing of Lehman Brothers (15 September 2008), each linked to sources you verify.',
    visual: 'timeline',
  },
  {
    phase: 'Time Machine',
    slug: 'time-machine',
    explain: 'The archive is viewed as of a date to separate what was known then from what was understood later.',
    example: 'Set the year to 2007: later events and retrospective consequences are hidden, and indicators stop at 2007.',
    visual: 'clock',
  },
  {
    phase: 'Knowledge Graph',
    slug: 'knowledge-graph',
    explain: 'Banks, regulators, instruments and events are connected, each link with its evidence or labelled as hypothesis.',
    example: 'An institution linked to an event by a sourced relation; a contagion channel you suspect entered as a dashed hypothesis.',
    visual: 'graph',
  },
  {
    phase: 'Research War Room',
    slug: 'research-war-room',
    explain: 'Agents search the archive, analyse the series, challenge each other and produce typed claims for your approval.',
    example: 'The sceptic flags a claim resting on a single document and a correlation presented as causation.',
    visual: 'agents',
  },
  {
    phase: 'Economic Laboratory',
    slug: 'economic-laboratory',
    explain: 'Alternative scenarios are explored as explicit, labelled hypotheses.',
    example: 'A counterfactual debt scenario with a different rate path — clearly marked “hypothetical scenario”, never a reconstruction of what would have happened.',
    visual: 'fan',
  },
  {
    phase: 'Research Studio',
    slug: 'research-studio',
    explain: 'Findings, charts and citations are assembled into a report that can be approved only when every citation checks out.',
    example: 'A ten-part report exported to PDF or LaTeX, with numbered references and unverified sources flagged.',
    visual: 'report',
  },
];

export const CAPABILITIES: { title: string; text: string; slug: ModuleSlug }[] = [
  { title: 'Historical Research', text: 'Structured events with variable-precision dates, sources and reliability, and a time-aware view without hindsight.', slug: 'historical-intelligence' },
  { title: 'Financial Intelligence', text: 'Open economic data from the World Bank, Eurostat, the ECB, ISTAT and FRED with full provenance, alerts, returns, volatility, drawdowns, stationarity tests and honest comparisons.', slug: 'financial-intelligence' },
  { title: 'Knowledge Mapping', text: 'A graph of people, institutions, events and ideas where every relation carries its evidence.', slug: 'knowledge-graph' },
  { title: 'AI Research', text: 'Supervised multi-agent research with typed claims, counter-analysis and mandatory approval.', slug: 'research-war-room' },
  { title: 'Economic Simulation', text: 'Monte Carlo, debt dynamics, policy rules, regressions and look-ahead-free backtests, assumptions included.', slug: 'economic-laboratory' },
  { title: 'Document Intelligence', text: 'Keyword and semantic search across your archive, answering with located, verbatim quotations.', slug: 'documents' },
  { title: 'Discovery Intelligence', text: 'Candidate connections, hypotheses with verification, anomalies, causal chains and scenarios — built on your archive, with evidence and sources.', slug: 'discovery-intelligence' },
  { title: 'Research Reporting', text: 'Ten-part reports with verifiable citations, charts and tables, exported to PDF, DOCX and LaTeX.', slug: 'research-studio' },
];
