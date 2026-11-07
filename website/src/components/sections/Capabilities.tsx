import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { useI18n } from '../../lib/i18n';
import { ModuleVisual } from '../ModuleVisual';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';

export function Capabilities() {
  const { t, p, capabilities: CAPABILITIES, modulesBySlug: MODULES_BY_SLUG } = useI18n();
  return (
    <section id="capabilities" className="border-t border-line bg-void py-28 md:py-36" aria-label={t.caps.label}>
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="06">{t.caps.label}</SectionLabel>
        <WordsReveal as="h2" key={t.caps.title} text={t.caps.title} className="font-serif text-[clamp(2.4rem,6vw,5.5rem)] leading-[0.95] tracking-tight" />
        <div className="mt-16 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((c, i) => (
            <Reveal key={c.title} delay={(i % 3) * 0.08} className={i === 0 ? 'lg:col-span-2' : ''}>
              <Link to={p(`/architecture/${c.slug}`)} className="group flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-coal transition-colors hover:border-copper/50">
                <div className="grain relative h-44 border-b border-line bg-void/50 p-4 transition-transform duration-700 group-hover:scale-[1.02]">
                  <ModuleVisual kind={MODULES_BY_SLUG[c.slug].visual} className="h-full w-full" />
                </div>
                <div className="flex flex-1 flex-col p-6">
                  <div className="flex items-start justify-between gap-4">
                    <h3 className="text-xl">{c.title}</h3>
                    <ArrowUpRight className="h-5 w-5 shrink-0 text-mute transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-copper" aria-hidden />
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-mute-2">{c.text}</p>
                </div>
              </Link>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
