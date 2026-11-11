import { DATA_POLICY, type LicenseEntry, type Permission } from '../content/dataPolicy';
import { useI18n } from '../lib/i18n';
import { usePageMeta } from '../lib/meta';

/** Pagina pubblica «Copyright & Data Policy»: principi e registro delle licenze (generato dal backend). */

const TEXT = {
  it: {
    intro: 'NEXUS usa solo dati aperti, con licenza dichiarata per ogni fonte. Questa pagina riporta, fonte per fonte, licenza, attribuzione richiesta, condizioni d\'uso e modifiche effettuate. Le stesse informazioni compaiono nell\'app accanto a ogni serie, evento e documento.',
    principles: 'Principi',
    rules: [
      'Nella Biblioteca NEXUS entrano solo dati aperti con una licenza registrata: senza scheda di licenza, l\'importazione viene bloccata dal sistema.',
      'Per ogni elemento NEXUS conserva fonte originale, URL e data di acquisizione; licenza, attribuzione e condizioni d\'uso sono nella scheda della fonte.',
      'Dei libri e degli articoli protetti da copyright NEXUS conserva solo i riferimenti bibliografici (autore, titolo, anno, DOI), mai il testo.',
      'Gli unici testi integrali sono opere di pubblico dominio, libere anche in Italia e nell\'Unione europea.',
      'I documenti e i dati caricati da un utente restano privati nel suo account e non entrano nella Biblioteca condivisa.',
      'NEXUS non modifica i valori delle fonti: i dati mancanti restano mancanti, e ogni trasformazione calcolata è dichiarata come tale.',
    ],
    registry: 'Registro delle fonti',
    fields: { license: 'Licenza', attribution: 'Attribuzione obbligatoria', commercial: 'Uso commerciale', redistribution: 'Redistribuzione',
      territorial: 'Limitazioni territoriali', modifications: 'Modifiche effettuate da NEXUS', verified: 'Condizioni verificate il', terms: 'pagina ufficiale', site: 'sito' },
    perm: { yes: 'Sì', conditional: 'Con condizioni', no: 'No' } as Record<Permission, string>,
    library: 'Biblioteca NEXUS', outside: 'Fuori dalla Biblioteca', perItem: 'Da verificare serie per serie',
    disclaimer: 'Le condizioni sono riassunte dalle pagine ufficiali di ciascuna fonte, indicate con la data di verifica. Questa pagina non costituisce parere legale: in caso di dubbio fa fede il testo della licenza originale. Per segnalazioni: nexus.analytic.research@gmail.com.',
    version: (v: string, d: string) => `Versione ${v} · aggiornata il ${d}`,
  },
  en: {
    intro: 'NEXUS uses only open data, with a declared licence for every source. This page lists, source by source, the licence, required attribution, terms of use and changes made. The same information appears in the app next to every series, event and document.',
    principles: 'Principles',
    rules: [
      'Only open data with a registered licence enter the NEXUS Library: without a licence entry, the system blocks the import.',
      'For every item NEXUS keeps the original source, URL and acquisition date; licence, attribution and terms of use are in the source\'s entry.',
      'For copyrighted books and articles NEXUS keeps only the bibliographic references (author, title, year, DOI), never the text.',
      'The only full texts are public-domain works, free in Italy and the European Union as well.',
      'Documents and data uploaded by a user stay private in their account and never enter the shared Library.',
      'NEXUS does not alter source values: missing data stay missing, and every computed transformation is labelled as such.',
    ],
    registry: 'Source registry',
    fields: { license: 'Licence', attribution: 'Required attribution', commercial: 'Commercial use', redistribution: 'Redistribution',
      territorial: 'Territorial restrictions', modifications: 'Changes made by NEXUS', verified: 'Terms checked on', terms: 'official page', site: 'website' },
    perm: { yes: 'Yes', conditional: 'With conditions', no: 'No' } as Record<Permission, string>,
    library: 'NEXUS Library', outside: 'Outside the Library', perItem: 'To be checked series by series',
    disclaimer: 'Terms are summarised from each source\'s official pages, linked with the date they were checked. This page is not legal advice: if in doubt, the original licence text prevails. To report an issue: nexus.analytic.research@gmail.com.',
    version: (v: string, d: string) => `Version ${v} · updated on ${d}`,
  },
};

const TONE: Record<Permission, string> = { yes: 'text-emerald-300', conditional: 'text-amber-300', no: 'text-rose-300' };

function Entry({ e, t }: { e: LicenseEntry; t: (typeof TEXT)['it'] }) {
  const lib = DATA_POLICY.library.includes(e.id);
  const row = (label: string, value: React.ReactNode) => (
    <div className="grid gap-1 border-t border-line py-3 sm:grid-cols-[12rem_1fr] sm:gap-4">
      <dt className="text-[11px] uppercase tracking-[0.16em] text-mute">{label}</dt>
      <dd className="text-[14px] leading-relaxed text-mute-2">{value}</dd>
    </div>
  );
  return (
    <section className="mt-8 rounded-lg border border-line p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg text-ivory">{e.name}</h3>
        <span className="text-[11px] uppercase tracking-[0.18em] text-copper">{lib ? t.library : t.outside}{e.status === 'per_item' ? ` · ${t.perItem}` : ''}</span>
      </div>
      <p className="mt-1 text-sm text-mute">{e.publisher} · <a href={e.homepage} target="_blank" rel="noreferrer noopener" className="underline hover:text-ivory">{t.fields.site}</a></p>
      <p className="mt-3 text-[14px] leading-relaxed text-mute-2">{e.applies_to}</p>
      <dl className="mt-4">
        {row(t.fields.license, <a href={e.license_url} target="_blank" rel="noreferrer noopener" className="text-ivory underline">{e.license}</a>)}
        {row(t.fields.attribution, e.attribution)}
        {row(t.fields.commercial, <><span className={TONE[e.commercial]}>{t.perm[e.commercial]}</span> — {e.commercial_note}</>)}
        {row(t.fields.redistribution, <><span className={TONE[e.redistribution]}>{t.perm[e.redistribution]}</span> — {e.redistribution_note}</>)}
        {row(t.fields.territorial, e.territorial)}
        {row(t.fields.modifications, e.modifications)}
        {row(t.fields.verified, <>{e.verified_on} · <a href={e.terms_url} target="_blank" rel="noreferrer noopener" className="underline hover:text-ivory">{t.fields.terms}</a></>)}
      </dl>
      {e.notes && <p className="mt-3 text-sm text-mute">{e.notes}</p>}
    </section>
  );
}

export function DataPolicy() {
  const { lang } = useI18n();
  const t = TEXT[lang === 'it' ? 'it' : 'en'];
  const entries = lang === 'it' ? DATA_POLICY.it : DATA_POLICY.en;
  usePageMeta('Copyright & Data Policy');
  return (
    <section className="bg-void px-5 pb-24 pt-32 sm:px-8 md:pt-40">
      <article className="mx-auto max-w-3xl">
        <h1 className="font-serif text-[clamp(2.4rem,7vw,4.5rem)] leading-[0.95] tracking-tight">Copyright &amp; Data Policy</h1>
        <p className="mt-4 text-[11px] uppercase tracking-[0.22em] text-mute">{t.version(DATA_POLICY.version, DATA_POLICY.updated)}</p>
        <p className="mt-8 text-[15px] leading-relaxed text-mute-2">{t.intro}</p>
        <h2 className="mt-12 text-xl text-ivory">{t.principles}</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-mute-2">
          {t.rules.map((r) => <li key={r.slice(0, 40)}>{r}</li>)}
        </ul>
        <h2 className="mt-12 text-xl text-ivory">{t.registry}</h2>
        {entries.map((e) => <Entry key={e.id} e={e} t={t} />)}
        <p className="mt-10 text-sm leading-relaxed text-mute">{t.disclaimer}</p>
      </article>
    </section>
  );
}
