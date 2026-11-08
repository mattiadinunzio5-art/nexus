import { PRIVACY_EN, PRIVACY_IT } from '../content/privacy';
import { useI18n } from '../lib/i18n';
import { usePageMeta } from '../lib/meta';

export function Privacy() {
  const { lang } = useI18n();
  const doc = lang === 'it' ? PRIVACY_IT : PRIVACY_EN;
  usePageMeta(doc.title);
  return (
    <section className="bg-void px-5 pb-24 pt-32 sm:px-8 md:pt-40">
      <article className="mx-auto max-w-3xl">
        <h1 className="font-serif text-[clamp(2.6rem,7vw,4.5rem)] leading-[0.95] tracking-tight">{doc.title}</h1>
        <p className="mt-4 text-[11px] uppercase tracking-[0.22em] text-mute">{doc.updated}</p>
        <p className="mt-8 text-[15px] leading-relaxed text-mute-2">{doc.intro}</p>
        {doc.sections.map((s) => (
          <section key={s.title} className="mt-10">
            <h2 className="text-xl text-ivory">{s.title}</h2>
            {s.body.map((b) => <p key={b.slice(0, 40)} className="mt-3 text-[15px] leading-relaxed text-mute-2">{b}</p>)}
          </section>
        ))}
      </article>
    </section>
  );
}
