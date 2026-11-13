import { Link } from 'react-router-dom';
import { ArrowUpRight, Play } from 'lucide-react';
import { HOME_EN, HOME_IT } from '../../content/home';
import { useI18n } from '../../lib/i18n';
import { demoUrl } from '../../lib/supabase';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';

function useHome() {
  const { lang } = useI18n();
  return lang === 'it' ? HOME_IT : HOME_EN;
}

const H2 = 'font-serif text-[clamp(2.2rem,5vw,4.4rem)] leading-[0.98] tracking-tight';

/** 02 — Il problema e la soluzione in tre punti. */
export function Why() {
  const h = useHome().why;
  return (
    <section id="why" className="border-t border-line bg-void py-24 md:py-32" aria-label={h.label}>
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="01">{h.label}</SectionLabel>
        <WordsReveal as="h2" key={h.title} text={h.title} className={`max-w-5xl ${H2}`} />
        <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-3">
          {h.points.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.08} className="bg-coal p-7 md:p-8">
              <span className="font-serif text-4xl text-copper">{['I', 'II', 'III'][i]}</span>
              <h3 className="mt-6 text-lg font-medium">{p.title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-mute-2">{p.text}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/** 03 — I sette moduli in una griglia compatta, ognuno con il link alla sua guida. */
export function Modules() {
  const h = useHome().mods;
  const { p } = useI18n();
  return (
    <section id="modules" className="border-t border-line bg-coal py-24 md:py-32" aria-label={h.label}>
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="02">{h.label}</SectionLabel>
        <div className="grid gap-6 md:grid-cols-[1.4fr_1fr] md:items-end">
          <WordsReveal as="h2" key={h.title} text={h.title} className={H2} />
          <p className="text-[15px] leading-relaxed text-mute-2">{h.intro}</p>
        </div>
        <ul className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {h.items.map((m, i) => (
            <li key={m.slug} className="bg-void">
              <Reveal delay={(i % 3) * 0.06}>
                <Link to={p(`/architecture/${m.slug}`)} className="group flex h-full flex-col gap-3 p-6 transition-colors hover:bg-coal-2 md:p-7">
                  <span className="flex items-center justify-between">
                    <span translate="no" className="text-xl tracking-tight">{m.title}</span>
                    <ArrowUpRight className="h-5 w-5 text-mute transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-copper" aria-hidden />
                  </span>
                  <span className="text-sm leading-relaxed text-mute-2">{m.text}</span>
                </Link>
              </Reveal>
            </li>
          ))}
          <li className="flex items-center bg-void p-6 text-sm leading-relaxed text-mute md:p-7 lg:col-span-2">{h.archive}</li>
        </ul>
      </div>
    </section>
  );
}

/** 04 — Come funziona, in quattro passi su una sola schermata. */
export function HowItWorks() {
  const h = useHome().how;
  return (
    <section id="how" className="border-t border-line bg-void py-24 md:py-32" aria-label={h.label}>
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="03">{h.label}</SectionLabel>
        <WordsReveal as="h2" key={h.title} text={h.title} className={`max-w-4xl ${H2}`} />
        <ol className="mt-12 grid gap-8 md:grid-cols-4">
          {h.steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.08}>
              <li className="border-t border-line pt-6">
                <span className="font-mono text-xs text-copper">0{i + 1}</span>
                <h3 className="mt-3 text-lg font-medium">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-mute-2">{s.text}</p>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}

/** 05 — Un caso reale: il 1929, con il video della lezione guidata. */
export function Case1929() {
  const h = useHome().case29;
  const { lang } = useI18n();
  const demo = demoUrl(lang);
  return (
    <section id="case" className="border-t border-line bg-coal py-24 md:py-32" aria-label={h.label}>
      <div className="mx-auto grid max-w-[1440px] gap-12 px-5 sm:px-8 lg:grid-cols-[1fr_1.3fr] lg:items-center">
        <div>
          <SectionLabel n="04">{h.label}</SectionLabel>
          <WordsReveal as="h2" key={h.title} text={h.title} className={H2} />
          <p className="mt-6 max-w-xl text-[15px] leading-relaxed text-mute-2">{h.text}</p>
          <ul className="mt-6 space-y-2 text-sm text-mute-2">
            {h.bullets.map((b) => <li key={b} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" aria-hidden />{b}</li>)}
          </ul>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            {demo && (
              <a href={demo} className="inline-flex items-center gap-2 rounded-full bg-copper px-6 py-3 text-sm font-medium text-void transition hover:bg-ivory">
                <Play className="h-4 w-4" aria-hidden /> {h.demo}
              </a>
            )}
            <span className="text-xs text-mute">{h.lessons}</span>
          </div>
        </div>
        <Reveal>
          <video controls preload="metadata" poster="/video/crisi-1929.jpg" aria-label={h.caption}
            className="w-full rounded-2xl border border-line bg-black">
            <source src="/video/crisi-1929.mp4" type="video/mp4" />
          </video>
          <p className="mt-3 text-xs text-mute">{h.caption}</p>
        </Reveal>
      </div>
    </section>
  );
}

/** Link di fiducia sotto l'accesso: fonti e licenze. */
export function TrustLink() {
  const { p } = useI18n();
  return (
    <div className="border-t border-line bg-void py-6 text-center">
      <Link to={p('/data-policy')} className="text-[11px] uppercase tracking-[0.22em] text-mute hover:text-copper">{useHome().trust} →</Link>
    </div>
  );
}
