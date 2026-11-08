/** Informativa privacy (art. 13 GDPR) — italiano e inglese. Aggiornare `updated` a ogni modifica. */

export const PRIVACY_CONTACT = { name: 'Mattia Di Nunzio', email: 'mattiadinunzio5@gmail.com' };

export interface PrivacySection { title: string; body: string[] }
export interface PrivacyDoc { title: string; updated: string; intro: string; sections: PrivacySection[] }

const C = PRIVACY_CONTACT;

export const PRIVACY_IT: PrivacyDoc = {
  title: 'Informativa sulla privacy',
  updated: 'Ultimo aggiornamento: 9 novembre 2026',
  intro: `Questa informativa spiega quali dati personali tratta NEXUS (il sito e la piattaforma online), perché e con quali diritti per te. NEXUS è un progetto personale e non commerciale: non vende dati, non mostra pubblicità e non usa strumenti di profilazione.`,
  sections: [
    { title: '1. Titolare del trattamento', body: [`${C.name} — email: ${C.email}. Per qualsiasi domanda o richiesta sui tuoi dati puoi scrivere a questo indirizzo.`] },
    {
      title: '2. Quali dati trattiamo',
      body: [
        'Dati dell’account: indirizzo email e password. La password è gestita dal servizio di autenticazione (Supabase) in forma cifrata: nessuno, nemmeno il titolare, può leggerla.',
        'Contenuti che inserisci: progetti, note, eventi, fonti, serie di dati e documenti che carichi nella piattaforma. Restano visibili solo a te e alle persone con cui scegli di condividerli.',
        'Dati tecnici: i server registrano automaticamente dati come indirizzo IP, tipo di browser, data e ora delle richieste, necessari per il funzionamento e la sicurezza.',
        'Memoria del browser: il sito e la piattaforma salvano nel tuo browser solo ciò che serve a mantenerti collegato (sessione) e alcune preferenze. Non usiamo cookie di profilazione né strumenti di analisi o statistiche di terzi.',
        'Messaggi: se ci scrivi (per esempio con il pulsante «Suggerisci»), trattiamo il tuo indirizzo email e il contenuto del messaggio per risponderti.',
      ],
    },
    {
      title: '3. Perché li trattiamo (finalità e basi giuridiche)',
      body: [
        'Per creare e gestire il tuo account e fornirti la piattaforma (esecuzione del servizio che richiedi, art. 6.1.b GDPR).',
        'Per proteggere il servizio da abusi e garantirne la sicurezza (legittimo interesse, art. 6.1.f GDPR).',
        'Per rispondere ai tuoi messaggi (art. 6.1.b o 6.1.f GDPR). Non usiamo i tuoi dati per marketing.',
      ],
    },
    {
      title: '4. Demo senza account',
      body: ['La demo pubblica non richiede alcun dato personale: il browser riceve un codice temporaneo, valido poche ore, che consente solo di consultare il progetto di esempio.'],
    },
    {
      title: '5. A chi affidiamo i dati (fornitori)',
      body: [
        'Supabase — autenticazione, database e archivio dei file (server nell’Unione europea).',
        'Render — server della piattaforma (Francoforte, Germania).',
        'Vercel — pubblicazione del sito e dell’interfaccia della piattaforma (rete globale).',
        'Questi fornitori agiscono come responsabili del trattamento secondo i propri accordi sul trattamento dei dati. Alcuni hanno sede negli Stati Uniti: gli eventuali trasferimenti fuori dall’UE avvengono con le garanzie previste dal GDPR (clausole contrattuali standard e/o EU-U.S. Data Privacy Framework).',
      ],
    },
    {
      title: '6. Per quanto tempo',
      body: [
        'I dati dell’account e i tuoi contenuti restano finché l’account è attivo. Se chiedi la cancellazione, vengono eliminati entro 30 giorni (salvo copie di sicurezza, sovrascritte nei cicli successivi).',
        'I dati tecnici dei server sono conservati per il tempo limitato previsto dai fornitori.',
      ],
    },
    {
      title: '7. I tuoi diritti',
      body: [
        `Puoi chiedere in qualsiasi momento di accedere ai tuoi dati, correggerli, cancellarli (anche cancellare l’account), limitarne o opporti al trattamento e riceverli in un formato portabile: basta scrivere a ${C.email}. Risponderemo entro un mese.`,
        'Hai anche il diritto di presentare reclamo al Garante per la protezione dei dati personali (www.garanteprivacy.it).',
      ],
    },
    { title: '8. Minori', body: ['NEXUS non è destinato a persone sotto i 14 anni.'] },
    { title: '9. Modifiche', body: ['Se questa informativa cambia, la nuova versione sarà pubblicata su questa pagina con la data di aggiornamento.'] },
  ],
};

export const PRIVACY_EN: PrivacyDoc = {
  title: 'Privacy policy',
  updated: 'Last updated: 9 November 2026',
  intro: 'This policy explains which personal data NEXUS (the website and the online platform) processes, why, and what rights you have. NEXUS is a personal, non-commercial project: it does not sell data, show ads or use profiling tools.',
  sections: [
    { title: '1. Data controller', body: [`${C.name} — email: ${C.email}. Write to this address for any question or request about your data.`] },
    {
      title: '2. What data we process',
      body: [
        'Account data: email address and password. The password is handled by the authentication service (Supabase) in encrypted form: nobody, not even the controller, can read it.',
        'Content you add: projects, notes, events, sources, data series and documents you upload. They are visible only to you and to the people you choose to share them with.',
        'Technical data: servers automatically log data such as IP address, browser type, date and time of requests, needed for operation and security.',
        'Browser storage: the site and the platform store in your browser only what is needed to keep you signed in (session) and a few preferences. We use no profiling cookies and no third-party analytics.',
        'Messages: if you write to us (for example with the “Suggest” button), we process your email address and message in order to reply.',
      ],
    },
    {
      title: '3. Why we process it (purposes and legal bases)',
      body: [
        'To create and manage your account and provide the platform (performance of the service you request, Art. 6(1)(b) GDPR).',
        'To protect the service against abuse and keep it secure (legitimate interest, Art. 6(1)(f) GDPR).',
        'To answer your messages (Art. 6(1)(b) or (f) GDPR). We do not use your data for marketing.',
      ],
    },
    { title: '4. Demo without an account', body: ['The public demo requires no personal data: the browser receives a temporary code, valid for a few hours, that only allows browsing the sample project.'] },
    {
      title: '5. Who we rely on (providers)',
      body: [
        'Supabase — authentication, database and file storage (servers in the European Union).',
        'Render — platform server (Frankfurt, Germany).',
        'Vercel — hosting of the website and of the platform interface (global network).',
        'These providers act as processors under their data processing agreements. Some are based in the United States: any transfer outside the EU relies on the safeguards provided by the GDPR (standard contractual clauses and/or the EU-U.S. Data Privacy Framework).',
      ],
    },
    {
      title: '6. How long',
      body: [
        'Account data and your content are kept while the account is active. If you ask for deletion, they are removed within 30 days (backup copies are overwritten in later cycles).',
        'Server technical data is kept for the limited period set by the providers.',
      ],
    },
    {
      title: '7. Your rights',
      body: [
        `You can ask at any time to access, correct or delete your data (including deleting your account), restrict or object to processing, and receive it in a portable format: write to ${C.email}. We will reply within one month.`,
        'You also have the right to lodge a complaint with your data protection authority (in Italy: Garante per la protezione dei dati personali, www.garanteprivacy.it).',
      ],
    },
    { title: '8. Children', body: ['NEXUS is not intended for people under 14.'] },
    { title: '9. Changes', body: ['If this policy changes, the new version will be published on this page with its update date.'] },
  ],
};
