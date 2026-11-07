import { Link, Navigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowUpRight, ExternalLink } from 'lucide-react';
import { CASES, CASES_BY_SLUG, type CaseArticle } from '../content/cases';
import { Reveal, SectionLabel, WordsReveal } from '../components/Reveal';
import { useI18n } from '../lib/i18n';
import { usePageMeta } from '../lib/meta';

export function formatMonth(ym: string, lang: 'en' | 'it') {
  const [y, m] = ym.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, 1)).toLocaleDateString(lang === 'it' ? 'it-IT' : 'en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' });
}

export function CaseCard({ c, i }: { c: CaseArticle; i: number }) {
  const { t, p, lang } = useI18n();
  const x = c[lang];
  return (
    <Reveal delay={i * 0.08} className="h-full">
      <Link to={p(`/cases/${c.slug}`)} className="group flex h-full flex-col rounded-2xl border border-line bg-coal p-7 transition-colors hover:border-copper/60 hover:bg-coal-2">
        <p className="text-[11px] uppercase tracking-[0.22em] text-copper">{formatMonth(c.date, lang)} · {t.cases.minutes(c.minutes)}</p>
        <h3 className="mt-4 font-serif text-3xl leading-tight">{x.title}</h3>
        <p className="mt-3 flex-1 text-sm leading-relaxed text-mute-2">{x.dek}</p>
        <span className="mt-6 inline-flex items-center gap-2 text-sm text-ivory group-hover:text-copper">{t.cases.read} <ArrowUpRight className="h-4 w-4 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden /></span>
      </Link>
    </Reveal>
  );
}

/** Anteprima nella home. */
export function CasesTeaser() {
  const { t, p } = useI18n();
  return (
    <section id="cases" className="border-t border-line bg-coal py-28 md:py-36" aria-label={t.cases.label}>
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <div className="grid gap-8 md:grid-cols-[1.4fr_1fr] md:items-end">
          <div>
            <SectionLabel n="07">{t.cases.label}</SectionLabel>
            <WordsReveal key={t.cases.homeTitle} as="h2" text={t.cases.homeTitle} className="font-serif text-[clamp(2.4rem,6vw,5.5rem)] leading-[0.95] tracking-tight" />
          </div>
          <Reveal><p className="text-[15px] leading-relaxed text-mute-2">{t.cases.intro}</p></Reveal>
        </div>
        <div className="mt-14 grid gap-4 md:grid-cols-2">{CASES.slice(0, 2).map((c, i) => <CaseCard key={c.slug} c={c} i={i} />)}</div>
        <Link to={p('/cases')} className="mt-10 inline-flex items-center gap-2 rounded-full border border-ivory/30 px-6 py-3 text-sm font-medium transition hover:border-ivory">{t.cases.all} <ArrowUpRight className="h-4 w-4" aria-hidden /></Link>
      </div>
    </section>
  );
}

export function CasesPage() {
  const { t } = useI18n();
  usePageMeta(t.cases.pageTitle, t.cases.pageDescription);
  return (
    <section className="min-h-[100svh] bg-void pb-28 pt-32">
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="—">{t.cases.label}</SectionLabel>
        <WordsReveal key={t.cases.title} as="h1" text={t.cases.title} className="max-w-5xl font-serif text-[clamp(2.6rem,7vw,6.5rem)] leading-[0.95] tracking-tight" />
        <p className="mt-8 max-w-2xl text-[15px] leading-relaxed text-mute-2">{t.cases.intro}</p>
        <div className="mt-14 grid gap-4 md:grid-cols-2">{CASES.map((c, i) => <CaseCard key={c.slug} c={c} i={i} />)}</div>
      </div>
    </section>
  );
}

export function CaseArticlePage() {
  const { slug = '' } = useParams();
  const { t, p, lang, modulesBySlug } = useI18n();
  const c = CASES_BY_SLUG[slug];
  usePageMeta(c ? c[lang].title : t.cases.notFound, c ? c[lang].dek : undefined);
  if (!c) return <Navigate to={p('/404')} replace />;
  const x = c[lang];
  return (
    <article className="bg-void pb-24 pt-28">
      <header className="mx-auto max-w-3xl px-5 sm:px-8">
        <Link to={p('/cases')} className="inline-flex items-center gap-2 text-sm text-mute hover:text-ivory"><ArrowLeft className="h-4 w-4" aria-hidden /> {t.cases.all}</Link>
        <p className="mt-10 text-[11px] uppercase tracking-[0.24em] text-copper">{t.cases.label} · {formatMonth(c.date, lang)} · {t.cases.minutes(c.minutes)}</p>
        <WordsReveal key={x.title} as="h1" text={x.title} className="mt-4 font-serif text-[clamp(2.6rem,6vw,4.8rem)] leading-[0.98] tracking-tight" />
        <p className="mt-6 text-[clamp(1.1rem,1.8vw,1.35rem)] leading-relaxed text-ivory/90">{x.dek}</p>
      </header>
      <div className="mx-auto mt-14 max-w-3xl px-5 sm:px-8">
        {x.sections.map((s) => (
          <Reveal key={s.heading} className="border-t border-line py-10">
            <h2 className="text-sm uppercase tracking-[0.22em] text-mute">{s.heading}</h2>
            {s.paragraphs.map((para) => <p key={para.slice(0, 40)} className="mt-5 text-[16px] leading-[1.75] text-ivory/90">{para}</p>)}
          </Reveal>
        ))}
        <div className="grid gap-8 border-t border-line py-10 md:grid-cols-2">
          <div>
            <h2 className="text-sm uppercase tracking-[0.22em] text-mute">{t.cases.sources}</h2>
            <ul className="mt-4 space-y-3 text-sm">
              {c.sources.map((s) => <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer noopener" className="inline-flex items-start gap-2 text-mute-2 hover:text-ivory">{s.label}<ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden /></a></li>)}
            </ul>
          </div>
          <div>
            <h2 className="text-sm uppercase tracking-[0.22em] text-mute">{t.cases.modules}</h2>
            <ul className="mt-4 flex flex-wrap gap-2">
              {c.modules.map((m) => <li key={m}><Link to={p(`/architecture/${m}`)} className="inline-flex rounded-full border border-line px-4 py-2 text-sm hover:border-copper hover:text-copper">{modulesBySlug[m].title}</Link></li>)}
            </ul>
          </div>
        </div>
      </div>
    </article>
  );
}
