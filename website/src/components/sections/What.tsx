import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import type { ModuleSlug } from '../../content/modules';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';

const PILLARS: { label: string; slug: ModuleSlug }[] = [
  { label: 'Document research', slug: 'documents' },
  { label: 'Economic & financial analysis', slug: 'financial-intelligence' },
  { label: 'Historical reconstruction', slug: 'historical-intelligence' },
  { label: 'Temporal analysis', slug: 'time-machine' },
  { label: 'Knowledge Graph', slug: 'knowledge-graph' },
  { label: 'AI agents', slug: 'research-war-room' },
  { label: 'Economic simulation', slug: 'economic-laboratory' },
  { label: 'Report production', slug: 'research-studio' },
];

export function What() {
  return (
    <section id="what" className="border-t border-line bg-coal py-28 md:py-36" aria-label="What is NEXUS">
      <div className="mx-auto grid max-w-[1440px] gap-16 px-5 sm:px-8 lg:grid-cols-[1fr_1fr] lg:gap-24">
        <div>
          <SectionLabel n="02">What is NEXUS</SectionLabel>
          <WordsReveal as="h2" text="A platform for research, analysis and simulation of knowledge." className="font-serif text-[clamp(2.4rem,5vw,4.6rem)] leading-[0.98] tracking-tight" />
          <Reveal delay={0.2}>
            <p className="mt-8 max-w-xl text-[15px] leading-relaxed text-mute-2">
              NEXUS is not a chatbot. It is a working environment where your documents, data and chronologies live together, connected by the sources that support them. AI is optional and supervised: without it, NEXUS still searches, computes, cross-checks and writes nothing it cannot prove.
            </p>
            <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-mute-2">
              It runs on your own computer at zero cost, with open-source software and open data — and can be run as a multi-user service.
            </p>
          </Reveal>
        </div>
        <ol className="self-end border-t border-line">
          {PILLARS.map((p, i) => (
            <Reveal key={p.slug} delay={i * 0.05}>
              <li className="border-b border-line">
                <Link to={`/architecture/${p.slug}`} className="group flex items-center gap-6 py-5 transition-colors hover:text-copper">
                  <span className="font-mono text-xs text-mute">0{i + 1}</span>
                  <span className="flex-1 text-[clamp(1.1rem,2vw,1.5rem)]">{p.label}</span>
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
