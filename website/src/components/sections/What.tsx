import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import type { ModuleSlug } from '../../content/modules';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';
import { useI18n } from '../../lib/i18n';

const PILLAR_SLUGS: ModuleSlug[] = ['documents', 'financial-intelligence', 'historical-intelligence', 'time-machine', 'knowledge-graph', 'research-war-room', 'economic-laboratory', 'research-studio'];

export function What() {
  const { t, p } = useI18n();
  const PILLARS = PILLAR_SLUGS.map((slug, i) => ({ slug, label: t.what.pillars[i] }));
  return (
    <section id="what" className="border-t border-line bg-coal py-28 md:py-36" aria-label={t.what.label}>
      <div className="mx-auto grid max-w-[1440px] gap-16 px-5 sm:px-8 lg:grid-cols-[1fr_1fr] lg:gap-24">
        <div>
          <SectionLabel n="02">{t.what.label}</SectionLabel>
          <WordsReveal as="h2" key={t.what.title} text={t.what.title} className="font-serif text-[clamp(2.4rem,5vw,4.6rem)] leading-[0.98] tracking-tight" />
          <Reveal delay={0.2}>
            <p className="mt-8 max-w-xl text-[15px] leading-relaxed text-mute-2">{t.what.p1}</p>
            <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-mute-2">{t.what.p2}</p>
          </Reveal>
        </div>
        <ol className="self-end border-t border-line">
          {PILLARS.map((pl, i) => (
            <Reveal key={pl.slug} delay={i * 0.05}>
              <li className="border-b border-line">
                <Link to={p(`/architecture/${pl.slug}`)} className="group flex items-center gap-6 py-5 transition-colors hover:text-copper">
                  <span className="font-mono text-xs text-mute">0{i + 1}</span>
                  <span className="flex-1 text-[clamp(1.1rem,2vw,1.5rem)]">{pl.label}</span>
                  <ArrowUpRight className="h-5 w-5 text-mute transition group-hover:translate-x-1 group-hover:-translate-y-1 group-hover:text-copper" aria-hidden />
                </Link>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
