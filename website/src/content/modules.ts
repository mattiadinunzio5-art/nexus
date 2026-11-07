/**
 * Contenuti dei moduli NEXUS.
 *
 * Ogni testo descrive ciò che la piattaforma fa davvero (repository nexus, fasi 1–8).
 * I limiti noti sono dichiarati nel campo `limits`: il sito non promette funzioni assenti.
 */

export type ModuleSlug =
  | 'dashboard' | 'projects' | 'documents' | 'bibliography' | 'financial-intelligence' | 'historical-intelligence'
  | 'time-machine' | 'knowledge-graph' | 'research-war-room' | 'economic-laboratory' | 'research-studio' | 'sources';

export interface ModuleContent {
  slug: ModuleSlug;
  index: string;
  title: string;
  kicker: string;
  tagline: string;
  description: string;
  mainFunction: string;
  whyUseful: string[];
  guide: { title: string; detail: string }[];
  inputs: string[];
  outputs: string[];
  example: { title: string; steps: string[] };
  connections: { slug: ModuleSlug; why: string }[];
  limits: string[];
  visual: 'dashboard' | 'folders' | 'pages' | 'citations' | 'chart' | 'timeline' | 'clock' | 'graph' | 'agents' | 'fan' | 'report' | 'plug';
}

export const MODULES: ModuleContent[] = [
  {
    slug: 'dashboard',
    index: '01',
    title: 'Dashboard',
    kicker: 'Overview',
    tagline: 'The state of your research, at a glance.',
    description:
      'The dashboard is the first screen of NEXUS. It gathers the real state of your workspace — projects, sources, indicators, events, reports, AI activity and notifications — and says explicitly when a section has no data yet.',
    mainFunction: 'Summarise everything that is happening in your research environment and take you to it in one click.',
    whyUseful: [
      'You resume work exactly where you left it, without hunting through modules.',
      'Every number shown comes from your own archive, with its date and source — never placeholder figures.',
      'Empty sections say why they are empty and how to fill them, so nothing looks complete when it is not.',
    ],
    guide: [
      { title: 'Read the overview', detail: 'Each card summarises one area: sources status, recent searches, active projects, latest indicator values, archive events, reports, AI research runs and notifications.' },
      { title: 'Customise the layout', detail: 'Press “Personalizza” to reorder cards or hide the ones you do not need. The layout is saved on the server for your account.' },
      { title: 'Search everything', detail: 'The search bar at the top looks across projects, documents (full text), historical events, graph entities, series and reports.' },
      { title: 'Use the context panel', detail: 'The side panel shows system status and recent activity; on other pages it explains what you are looking at.' },
    ],
    inputs: ['Nothing to enter: the dashboard reads the data you create in the other modules.'],
    outputs: ['A live summary of your workspace', 'Shortcuts into projects, series, events, reports and research runs', 'A searchable activity log of every relevant operation'],
    example: {
      title: 'Monday morning',
      steps: [
        'Open NEXUS: the indicators card shows the last published value of the series you imported, with its date.',
        'A notification says a research run is awaiting your approval.',
        'Click it, review the agents’ work, approve — the dashboard updates immediately.',
      ],
    },
    connections: [
      { slug: 'projects', why: 'Active projects are listed on the dashboard.' },
      { slug: 'financial-intelligence', why: 'Imported series feed the indicators card.' },
      { slug: 'research-war-room', why: 'AI activity shows recent and pending research runs.' },
    ],
    limits: ['Values are the latest observations published by each source: NEXUS shows no real-time market quotes.'],
    visual: 'dashboard',
  },
  {
    slug: 'projects',
    index: '02',
    title: 'Projects',
    kicker: 'Organisation',
    tagline: 'One question, one place.',
    description:
      'A project is the container of a research effort. It holds the objective, and it groups the reports, notes and research runs that belong to the same question.',
    mainFunction: 'Give each research question a home, so that its reports, notes and AI runs stay together.',
    whyUseful: [
      'Separates parallel lines of research cleanly.',
      'Reports and notes can be attached to a project and shared with collaborators in multi-user mode.',
      'Each project has its own comment thread and a history of who changed what.',
    ],
    guide: [
      { title: 'Create a project', detail: 'Open Progetti → “Nuovo progetto”. Give it a clear title, e.g. “The 2008 financial crisis”.' },
      { title: 'Define the research objective', detail: 'Use the description to state the question, the hypotheses you want to test and the scope you intend to cover.' },
      { title: 'Organise the questions', detail: 'Write sub-questions as notes in the Research Studio, attached to the project; each can become a research run in the War Room.' },
      { title: 'Set the period of analysis', detail: 'The period is applied where it matters: as year filters in Historical Intelligence, as the date in the Time Machine and as the range of the series you analyse.' },
      { title: 'Discuss and track', detail: 'Open the comments icon: members — readers included — can comment, and the history lists every change with its author.' },
      { title: 'Start from a lesson', detail: 'Lezioni guidate creates a ready project on the 1929 crash, 1970s inflation or the 2008 crisis, with a step-by-step guide.' },
      { title: 'Manage the project', detail: 'Edit, archive or restore it at any time. Deletion is irreversible and always asks for explicit confirmation.' },
    ],
    inputs: ['Title', 'Description with objective and scope', 'Optional: collaborators (multi-user mode)'],
    outputs: ['A project page listed on the dashboard', 'A shared container for reports, notes and research runs', 'Comments and a change history'],
    example: {
      title: 'Starting a study',
      steps: [
        'Title: “Monetary consequences of the end of Bretton Woods”.',
        'Description: objective, the 1968–1979 window, the question about inflation in Italy.',
        'Three notes with sub-questions, later launched as War Room runs inside the project.',
      ],
    },
    connections: [
      { slug: 'research-studio', why: 'Reports and notes are attached to projects.' },
      { slug: 'research-war-room', why: 'Research runs can belong to a project.' },
      { slug: 'dashboard', why: 'Active projects appear on the dashboard.' },
    ],
    limits: ['A project has a title, a description and a status; the period of analysis is applied in the analysis modules rather than stored as a project field.'],
    visual: 'folders',
  },
  {
    slug: 'documents',
    index: '03',
    title: 'Documents',
    kicker: 'Archive',
    tagline: 'Your sources, readable and searchable to the page.',
    description:
      'The document archive imports PDF, DOCX, CSV, XLSX, TXT and Markdown files, extracts their text, splits it into passages that keep their page or paragraph, and indexes everything for keyword and semantic search.',
    mainFunction: 'Turn a pile of files into a searchable archive where every answer points to the exact passage it comes from.',
    whyUseful: [
      'Ask a question and get the literal sentences that answer it, with document and page.',
      'Full-text ranking (BM25) is combined with semantic search, so related wording is found too.',
      'Text that looks like instructions to an AI is flagged and treated strictly as data.',
    ],
    guide: [
      { title: 'Import a file', detail: 'Documenti → choose a file (up to 25 MB), optional title and author, and a category: research material, personal work or dataset.' },
      { title: 'Check the extraction', detail: 'Open the document to read the extracted passages with their locator (p. 12, § 4–6, rows 1–40). Duplicates are detected automatically.' },
      { title: 'Link the bibliographic record', detail: 'Connect the document to its entry in the Bibliography: citations will then use the full reference instead of the file name.' },
      { title: 'Search and ask', detail: 'Use “Interroga l’archivio” to search (keyword, semantic or hybrid) or to ask a question answered with verbatim, located quotations.' },
      { title: 'Keep the archive clean', detail: 'Edit metadata, download the original, or delete with explicit confirmation — the index is updated accordingly.' },
    ],
    inputs: ['PDF (with a text layer), DOCX, CSV, XLSX, TXT, MD', 'Optional: title, author, category', 'Optional: a single public-domain text from Project Gutenberg by ebook ID'],
    outputs: ['Indexed passages with page or paragraph locators', 'Ranked search results with a support level', 'Answers made of documented quotations, or an explicit “missing data”'],
    example: {
      title: 'A central-bank report',
      steps: [
        'Import a 120-page PDF report you have downloaded.',
        'Ask: “When did the policy rate start to rise?”',
        'NEXUS returns the matching sentences, each labelled with page number and support level.',
      ],
    },
    connections: [
      { slug: 'bibliography', why: 'Documents cite their bibliographic record.' },
      { slug: 'research-war-room', why: 'Agents search the archive as evidence.' },
      { slug: 'knowledge-graph', why: 'A relation can cite a specific passage as its source.' },
    ],
    limits: ['Scanned PDFs without a text layer are rejected with a clear message: OCR is not included yet.'],
    visual: 'pages',
  },
  {
    slug: 'bibliography',
    index: '04',
    title: 'Bibliography',
    kicker: 'Provenance',
    tagline: 'Every claim traceable to a source you can check.',
    description:
      'The bibliography stores the references behind your research. NEXUS never creates sources by itself: each record is entered by you or confirmed against a registry, and its verification status is always visible.',
    mainFunction: 'Keep a verified list of references that documents, events, graph relations and reports can cite.',
    whyUseful: [
      'DOIs can be checked against Crossref; mismatches in title or year are reported.',
      'Unverified sources are flagged everywhere they are used — including in exported reports.',
      'Editing a record resets its verification, so a check always refers to the current data.',
    ],
    guide: [
      { title: 'Register a source', detail: 'Bibliografia → “Nuova fonte”: type, title, authors, year, publisher, journal, pages, DOI, ISBN, URL and access date.' },
      { title: 'Let NEXUS validate it', detail: 'DOI format, ISBN check digit and URL are validated on entry.' },
      { title: 'Verify', detail: 'Use “Verifica DOI su Crossref”, or declare that you checked the original. The status and the date of the check are stored.' },
      { title: 'Connect it', detail: 'Link the source to documents, historical events and graph relations; cite it in reports as [@id, p. 12].' },
      { title: 'Exchange with Zotero', detail: 'Import a BibTeX file from Zotero, Mendeley or JabRef — entries arrive as unverified — and export your bibliography to BibTeX.' },
    ],
    inputs: ['Bibliographic fields', 'Optional DOI for registry verification', 'Optional BibTeX file'],
    outputs: ['A formatted citation', 'A verification status: unverified, verified by you, verified on registry, not found', 'Numbered references in exported reports', 'A BibTeX file'],
    example: {
      title: 'Checking a journal article',
      steps: [
        'Enter the article with its DOI.',
        'Press “Verifica DOI su Crossref”: the registry confirms it but reports a different year.',
        'NEXUS shows the discrepancy so you can correct the record.',
      ],
    },
    connections: [
      { slug: 'documents', why: 'Documents point to their bibliographic record.' },
      { slug: 'historical-intelligence', why: 'Events list their sources and warn when none is verified.' },
      { slug: 'research-studio', why: 'Reports cite sources and build the bibliography automatically.' },
    ],
    limits: ['Registry verification covers DOIs via Crossref; books without a DOI are verified by your own declaration.'],
    visual: 'citations',
  },
  {
    slug: 'financial-intelligence',
    index: '05',
    title: 'Financial Intelligence',
    kicker: 'Data',
    tagline: 'Economic series with their provenance attached.',
    description:
      'Financial Intelligence imports time series from open sources, records where each one comes from, and computes the analyses an economist needs — returns, volatility, drawdowns, moving averages, trend and stationarity tests, comparisons and correlations.',
    mainFunction: 'Bring macroeconomic and market data into your research with full provenance, and analyse it correctly.',
    whyUseful: [
      'Every series carries its source, unit, frequency, period, the update date declared by the source and its missing values.',
      'Missing values are counted and never interpolated; anomalies are flagged, never removed.',
      'Series with different frequencies are compared only after an explicit resampling you choose.',
    ],
    guide: [
      { title: 'Import a series', detail: 'Importa serie → pick a suggested series (e.g. inflation, GDP, unemployment, public debt) or enter a code from World Bank, Eurostat, the ECB, ISTAT, Our World in Data or FRED.' },
      { title: 'Or upload your own', detail: 'Upload a CSV with date and value columns; the source field is mandatory.' },
      { title: 'Read the series', detail: 'The chart, a data table and the provenance panel show exactly what the source published.' },
      { title: 'Analyse', detail: 'Choose levels (prices, indices) or rates (percentages). NEXUS computes returns, annualised volatility, drawdown, CAGR, moving averages, linear trend, ADF test and autocorrelation.' },
      { title: 'Compare', detail: 'Select up to eight series: NEXUS aligns common dates, rebases them to 100 and computes correlations — on changes by default, because correlations of trending levels are often spurious.' },
      { title: 'Set alerts', detail: 'Get a notification when the source publishes a new value or the latest value crosses a threshold. Alerts are checked on refresh, with “Controlla ora” or with a script you schedule.' },
    ],
    inputs: ['A source code (e.g. FP.CPI.TOTL.ZG + ITA for World Bank) or a CSV', 'A free FRED API key, only for FRED series', 'Analysis choices: moving-average windows, return type, resampling'],
    outputs: ['Interactive charts with table view', 'Statistics with the number of observations used', 'Correlation matrix and the resampling procedure applied', 'Notifications on new data or thresholds'],
    example: {
      title: 'Inflation in Italy',
      steps: [
        'Import “Inflation, consumer prices (annual %) — Italy” from the World Bank.',
        'NEXUS shows 1960–2025, the source’s last update date and zero missing values.',
        'The ADF test reports whether the series is likely stationary; the anomaly detector flags the largest jumps for you to check.',
      ],
    },
    connections: [
      { slug: 'time-machine', why: 'Indicators are shown as of the selected date.' },
      { slug: 'economic-laboratory', why: 'Series feed bootstrap simulations, regressions and backtests.' },
      { slug: 'research-studio', why: 'Series charts can be embedded in reports.' },
    ],
    limits: [
      'No real-time quotes: the latest value is the latest observation published by the source.',
      'Series are the current published version, including later revisions.',
      'IMF, OECD and BIS are listed among sources but not connected yet.',
    ],
    visual: 'chart',
  },
  {
    slug: 'historical-intelligence',
    index: '06',
    title: 'Historical Intelligence',
    kicker: 'History',
    tagline: 'Events as structured, sourced knowledge.',
    description:
      'Historical Intelligence is an archive of events. Each record holds dates of variable precision (BC included), period, region and countries, categories, description, causes, consequences, people, institutions, economic implications, sources and a reliability grade.',
    mainFunction: 'Build a chronology you can filter, cite and connect — and always know how reliable each entry is.',
    whyUseful: [
      'Reliability is explicit: established, probable, disputed or unverified.',
      'An event without verified sources displays a warning wherever it appears.',
      'Each event is also a node of the Knowledge Graph, so it can be linked to other events and entities.',
    ],
    guide: [
      { title: 'Create an event', detail: 'Historical Intelligence → “Nuovo evento”. Dates accept year only, month or full day; negative years are BC; year 0 does not exist.' },
      { title: 'Place it', detail: 'Set period, region and countries, and choose categories: economic, monetary, banking, industrial, war and geopolitics, revolutions, financial crises, empires, capitalism.' },
      { title: 'Explain it', detail: 'Fill in causes, consequences, people and institutions involved, and economic implications.' },
      { title: 'Source it', detail: 'Link bibliography entries with page numbers and set the reliability grade with a note.' },
      { title: 'Record what was known when', detail: 'Add dated knowledge items — contemporary, later discovery, archival release, historiography — to feed the Time Machine.' },
    ],
    inputs: ['Title and dates', 'Context fields', 'Sources and reliability'],
    outputs: ['A filterable chronology by category, country and period', 'Event pages with sources and warnings', 'Event nodes in the Knowledge Graph'],
    example: {
      title: 'Building a crisis chronology',
      steps: [
        'Create the events you want to study, each with its dates and categories.',
        'Link each to a verified source; the warning disappears once one is verified.',
        'Link related events with typed relations (“preceded”, “influenced”).',
      ],
    },
    connections: [
      { slug: 'time-machine', why: 'Events and dated knowledge drive the time-aware view.' },
      { slug: 'knowledge-graph', why: 'Every event is a graph entity.' },
      { slug: 'bibliography', why: 'Sources support each event.' },
    ],
    limits: ['The archive starts empty: NEXUS does not ship invented events. Demo records are clearly labelled DEMO and have no sources.'],
    visual: 'timeline',
  },
  {
    slug: 'time-machine',
    index: '07',
    title: 'Time Machine',
    kicker: 'Time',
    tagline: 'See the past without hindsight.',
    description:
      'The Time Machine shows your archive as it would have looked at a chosen date. In strict mode it hides later events, retrospective consequences and knowledge that emerged afterwards — the protection against hindsight bias.',
    mainFunction: 'Reconstruct what was knowable at a given moment, and compare it with what we know today.',
    whyUseful: [
      'Separates contemporary information from later discoveries, archives and historiography.',
      'Marks events still ongoing at the selected date.',
      'Shows economic indicators available up to that date — with a warning that today’s values may include revisions.',
    ],
    guide: [
      { title: 'Choose a moment', detail: 'Enter a year (negative for BC) and optionally a country and a category.' },
      { title: 'Read the strict view', detail: 'Only events started by that year appear; their consequences are hidden; only knowledge dated up to that year is shown. Hidden items are counted, never silently dropped.' },
      { title: 'Switch on hindsight', detail: 'Tick “Senno di poi” to add later knowledge, highlighted as such, and compare.' },
      { title: 'Use it in analysis', detail: 'Open an event’s detail or the indicators panel to see the economic picture at that date.' },
    ],
    inputs: ['A year', 'Optional filters', 'Dated knowledge items recorded in Historical Intelligence'],
    outputs: ['A chronology as of the date', 'Counts of hidden later events and information', 'Indicators as of the date, with revision caveat'],
    example: {
      title: 'Standing in 1972',
      steps: [
        'Set the year to 1972.',
        'Events after 1972 disappear; the consequences of earlier events are hidden as retrospective.',
        'The indicators panel shows the inflation value recorded for 1972 in the current version of the series.',
      ],
    },
    connections: [
      { slug: 'historical-intelligence', why: 'Provides events and dated knowledge.' },
      { slug: 'financial-intelligence', why: 'Provides indicators as of the date.' },
      { slug: 'economic-laboratory', why: 'Backtests apply the same no-look-ahead principle.' },
    ],
    limits: ['Indicator values are today’s version of each series, not the vintage published at the time.'],
    visual: 'clock',
  },
  {
    slug: 'knowledge-graph',
    index: '08',
    title: 'Knowledge Graph',
    kicker: 'Connections',
    tagline: 'Relations you can defend.',
    description:
      'The Knowledge Graph connects people, states, companies, banks, institutions, events, documents, economic theories and indicators. Every relation must cite a source or a document passage — or be explicitly declared a hypothesis.',
    mainFunction: 'Map how the elements of your research are connected, and keep evidence attached to every connection.',
    whyUseful: [
      'Provenance is mandatory: sourced, user hypothesis or AI hypothesis — the last only created by research agents after your approval.',
      'Explore around any entity with depth and filters; centrality highlights the nodes that bridge clusters.',
      'Find the shortest path between two entities to discover non-obvious links.',
    ],
    guide: [
      { title: 'Create entities', detail: 'Knowledge Graph → “+ Entità”: type, name, period, description. Events are added automatically from Historical Intelligence.' },
      { title: 'Connect them', detail: '“+ Relazione”: choose the type — caused, influenced, contemporary of, related to, financed, involved in, replaced, preceded — and its provenance.' },
      { title: 'Explore', detail: 'Click a node to open its card and relations; centre the graph on it and set the depth.' },
      { title: 'Analyse', detail: 'Filter by relation type or provenance; use “Percorso” for the shortest path.' },
    ],
    inputs: ['Entities', 'Relations with a source, a document passage, or a hypothesis label'],
    outputs: ['An interactive network with layout and centrality', 'Relation lists with their evidence', 'Shortest paths'],
    example: {
      title: 'Who connects to what',
      steps: [
        'Add an institution and two events.',
        'Link them: one relation cites a verified source, another is your hypothesis (dashed line).',
        'Ask for the path between two distant entities.',
      ],
    },
    connections: [
      { slug: 'historical-intelligence', why: 'Events become entities.' },
      { slug: 'documents', why: 'Relations can cite a passage.' },
      { slug: 'research-war-room', why: 'Agents propose relations as AI hypotheses.' },
    ],
    limits: ['The layout is computed for clarity, not geography; very large graphs are trimmed to the most connected nodes.'],
    visual: 'graph',
  },
  {
    slug: 'research-war-room',
    index: '09',
    title: 'Research War Room',
    kicker: 'AI research',
    tagline: 'Several specialists, one supervised answer.',
    description:
      'The War Room runs a structured multi-agent research process: a planner, a researcher using your archive, a historian, an economist, a quant analyst, a sceptic and a synthesiser. Nothing is published until you approve it.',
    mainFunction: 'Divide a research question into tasks, gather evidence from your data, challenge the findings and produce a synthesis you approve.',
    whyUseful: [
      'Every claim is typed — documented fact, interpretation, hypothesis, estimate, missing data — and a fact without evidence is automatically downgraded.',
      'The sceptic looks for contradictions, weak sources, single-source reliance and correlation mistaken for causation.',
      'Each step records who executed it — the AI model or the local engine — with duration and tokens.',
    ],
    guide: [
      { title: 'Choose an AI provider (optional)', detail: 'Sistema → Credenziali: Ollama (free, on your computer), an OpenAI-compatible endpoint, or the Anthropic API with your own key. Without one, NEXUS runs in local mode.' },
      { title: 'Ask the question', detail: 'War Room → write the question; optionally select the series the quant analyst should use.' },
      { title: 'Follow the agents', detail: 'Planning → research → historian, economist, quant → sceptic → synthesis. In local mode the steps that need a language model are shown as “not executed”, never simulated.' },
      { title: 'Verify', detail: 'Each claim links to the evidence it cites; documents flagged for suspicious instructions are marked.' },
      { title: 'Approve or reject', detail: 'Approve the run; optionally accept the proposed graph relations, saved as AI hypotheses. Turn the run into a report draft in the Research Studio.' },
    ],
    inputs: ['A research question', 'Your archive: documents, events, series', 'Optional AI provider and credentials'],
    outputs: ['Typed claims with evidence and support level', 'Counter-analysis and declared limitations', 'An approved run, ready to become a report'],
    example: {
      title: 'A local-mode run',
      steps: [
        'Question: “How did inflation in Italy change in the 1970s?”',
        'The researcher finds two passages, one event and the matching inflation series.',
        'The quant computes statistics; the sceptic notes that the event has no verified source; the economist is marked “not executed” because no AI provider is configured.',
      ],
    },
    connections: [
      { slug: 'documents', why: 'Passages are the main evidence.' },
      { slug: 'financial-intelligence', why: 'Series feed the quant analyst.' },
      { slug: 'research-studio', why: 'Approved runs become report drafts.' },
    ],
    limits: ['Small local models are slower and less accurate than large hosted ones; the guards limit, but do not eliminate, model errors.', 'One run at a time, with a maximum number of automatic steps.'],
    visual: 'agents',
  },
  {
    slug: 'economic-laboratory',
    index: '10',
    title: 'Economic Laboratory',
    kicker: 'Simulation',
    tagline: 'Scenarios with their assumptions on the table.',
    description:
      'The Economic Laboratory runs quantitative models: Monte Carlo simulations, public-debt dynamics with rate shocks and crises, sensitivity analysis, inflation scenarios, monetary-policy rules, regressions and backtests. Every result declares its hypotheses, variables, parameters, method, data and limits.',
    mainFunction: 'Explore “what if” questions rigorously, with transparent assumptions.',
    whyUseful: [
      'Each simulation states what it assumes and what it cannot tell you.',
      'Counterfactual scenarios are labelled as hypotheses, never as reconstructions of history.',
      'Backtests apply signals only from the next period — tested to guarantee no look-ahead — and disclose survivorship and revision bias.',
    ],
    guide: [
      { title: 'Define the scenario', detail: 'Choose a model, e.g. “Debito pubblico e tassi”, and enter initial debt, interest rates, growth, primary balance and horizon.' },
      { title: 'Change the parameters', detail: 'Add a rate shock, a crisis window or uncertainty on rates and growth.' },
      { title: 'Analyse the variables', detail: 'Use sensitivity analysis to see which parameter moves the result most (tornado table).' },
      { title: 'Compare scenarios', detail: 'Baseline, shock and crisis paths appear on the same chart; Monte Carlo adds a percentile fan.' },
      { title: 'Interpret', detail: 'Read the methodological sheet: hypotheses, method, data used and limitations.' },
    ],
    inputs: ['Model parameters', 'Optional: a series for bootstrap, regression or backtest'],
    outputs: ['Paths, percentile fans and tables', 'A full methodological record', 'Results reusable as charts in reports'],
    example: {
      title: 'A rate shock on public debt',
      steps: [
        'Initial debt and rates from your imported series; a +1 point shock on market rates.',
        'The effective cost of debt rises gradually as debt is refinanced, at the pace of its average maturity.',
        'The result shows the extra debt at the horizon and the primary balance that would stabilise it — as a scenario, not a forecast.',
      ],
    },
    connections: [
      { slug: 'financial-intelligence', why: 'Real series provide inputs.' },
      { slug: 'time-machine', why: 'Shares the no-hindsight principle.' },
      { slug: 'research-studio', why: 'Simulation charts can be embedded in reports.' },
    ],
    limits: ['Simulations depend entirely on the quality of the data and on the model: they illustrate mechanisms, they do not predict.'],
    visual: 'fan',
  },
  {
    slug: 'research-studio',
    index: '11',
    title: 'Research Studio',
    kicker: 'Writing',
    tagline: 'From evidence to a finished report.',
    description:
      'The Research Studio turns your work into professional documents. Reports follow a ten-part structure — title, abstract, introduction, methodology, analysis, evidence, counter-arguments, conclusions, limitations and an automatic bibliography — with charts, tables and verifiable citations, exported to PDF, DOCX and LaTeX.',
    mainFunction: 'Organise, write and export your findings with every citation checked.',
    whyUseful: [
      'Citations like [@12, p. 4] become numbered references; citations to non-existent sources are reported.',
      'A report can be approved only when its sections are complete and its citations valid; any later edit returns it to draft.',
      'Drafts are exported with a DRAFT watermark and a notice for unverified sources.',
      'LaTeX export produces a ZIP ready for Overleaf, with main.tex, references.bib and the figures.',
    ],
    guide: [
      { title: 'Organise', detail: 'Keep notes linked to projects, sources and documents.' },
      { title: 'Structure the report', detail: 'Create a report, or generate a draft from an approved War Room run.' },
      { title: 'Create chapters', detail: 'Add extra chapters after any section and reorder them.' },
      { title: 'Add charts and tables', detail: 'Embed series and simulation charts, or paste a table as CSV.' },
      { title: 'Cite and check', detail: 'Cite sources in the text; the check panel lists empty sections, invalid citations and unverified sources.' },
      { title: 'Produce the final document', detail: 'Approve, then export to PDF, DOCX or LaTeX. The Daily Briefing summarises your data with dates and sources.' },
    ],
    inputs: ['Text', 'Bibliography entries', 'Series and simulations to embed'],
    outputs: ['PDF, DOCX and LaTeX reports with figures, tables and bibliography', 'A Daily Briefing'],
    example: {
      title: 'From run to report',
      steps: [
        'Generate a draft from an approved run: methodology, analysis and counter-arguments are prefilled with typed claims.',
        'Add the inflation chart and a debt scenario, write the conclusions.',
        'Fix one invalid citation flagged by the check, approve, export to PDF.',
      ],
    },
    connections: [
      { slug: 'research-war-room', why: 'Approved runs become drafts.' },
      { slug: 'bibliography', why: 'Builds the bibliography.' },
      { slug: 'financial-intelligence', why: 'Charts come from series.' },
    ],
    limits: ['Reports are edited section by section in plain text with simple lists; there is no rich-text editor yet.'],
    visual: 'report',
  },
  {
    slug: 'sources',
    index: '12',
    title: 'Sources & Connectors',
    kicker: 'Integrations',
    tagline: 'Open data, honestly connected.',
    description:
      'NEXUS connects to open data sources through modular connectors. Each one shows whether it is implemented, whether it needs a key, the last observed availability, and links to the terms of use.',
    mainFunction: 'Bring external data in without hiding where it comes from or what it allows.',
    whyUseful: [
      'Availability is checked with a real request, recording status, HTTP code and latency.',
      'Responses are cached: when a source is offline, NEXUS uses the cached copy and says so.',
      'Licences are not summarised as certainties: each connector links to the official terms.',
    ],
    guide: [
      { title: 'Review the sources', detail: 'Fonti e connettori lists each source with its category, whether it needs a key and its implementation status.' },
      { title: 'Check availability', detail: 'Press “Verifica” on a source, or “Verifica tutte”.' },
      { title: 'Configure keys', detail: 'FRED needs a free personal key, stored encrypted on your computer and never displayed again.' },
      { title: 'Understand the limits', detail: 'Read each source’s terms before any commercial use; third-party data keep their original licences.' },
    ],
    inputs: ['Optional API keys (FRED)'],
    outputs: ['Availability status per source', 'Imported series with provenance', 'Cached copies for offline use'],
    example: {
      title: 'When a source is down',
      steps: [
        'You press “Aggiorna dalla fonte” on a series while the source is unreachable.',
        'NEXUS serves the cached copy and labels it as such on the series page.',
        'The connector status records the failure with its error.',
      ],
    },
    connections: [
      { slug: 'financial-intelligence', why: 'Connectors import the series.' },
      { slug: 'documents', why: 'Project Gutenberg imports single public-domain texts.' },
      { slug: 'dashboard', why: 'Source status appears on the dashboard.' },
    ],
    limits: [
      'Implemented: World Bank, Eurostat, European Central Bank, ISTAT, Our World in Data, FRED (with key), Project Gutenberg.',
      'Declared but not yet connected: IMF, OECD, BIS.',
    ],
    visual: 'plug',
  },
];

export const MODULES_BY_SLUG = Object.fromEntries(MODULES.map((m) => [m.slug, m])) as Record<ModuleSlug, ModuleContent>;
