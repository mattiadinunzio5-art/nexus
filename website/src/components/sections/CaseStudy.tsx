import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, ArrowUpRight } from 'lucide-react';
import { CASE_STUDY } from '../../content/story';
import { MODULES_BY_SLUG } from '../../content/modules';
import { ModuleVisual } from '../ModuleVisual';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';

export function CaseStudy() {
  const [i, setI] = useState(0);
  const p = CASE_STUDY[i];
  const go = (d: number) => setI((v) => (v + d + CASE_STUDY.length) % CASE_STUDY.length);

  return (
    <section id="case-study" className="relative border-t border-line bg-coal py-28 md:py-36" aria-label="Case study: Inside the 2008 Financial Crisis">
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="05">Case Study</SectionLabel>
        <WordsReveal as="h2" text="Inside the 2008 Financial Crisis." className="font-serif text-[clamp(2.6rem,7vw,6.5rem)] leading-[0.92] tracking-tight" />
        <Reveal className="mt-10 grid gap-6 md:grid-cols-[1.4fr_1fr]">
          <blockquote className="border-l-2 border-copper pl-5 text-[clamp(1.1rem,2vw,1.5rem)] leading-snug text-ivory">
            “Why did the 2008 financial crisis occur, how did it spread across the global economy, and what alternative scenarios could have been possible?”
          </blockquote>
          <p className="rounded-xl border border-copper/40 bg-copper/5 p-4 text-xs leading-relaxed text-mute-2" role="note">
            <strong className="block text-[11px] uppercase tracking-[0.2em] text-copper">Demonstration</strong>
            This walkthrough shows how the work is organised in NEXUS. Illustrations are schematic, not data. The only historical facts cited are widely documented dates; no analysis result or simulation outcome is presented as real.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-6 lg:grid-cols-[300px_1fr]">
          <ol role="tablist" aria-label="Phases" className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-2 lg:mx-0 lg:block lg:space-y-1 lg:overflow-visible lg:px-0">
            {CASE_STUDY.map((c, k) => (
              <li key={c.phase} className="shrink-0">
                <button
                  role="tab"
                  aria-selected={k === i}
                  aria-controls="case-panel"
                  onClick={() => setI(k)}
                  className={`flex w-full items-center gap-3 whitespace-nowrap rounded-full border px-4 py-2 text-left text-sm transition lg:rounded-xl lg:border-transparent lg:py-3 ${k === i ? 'border-copper bg-void text-ivory lg:border-line' : 'border-line text-mute hover:text-ivory'}`}
                >
                  <span className={`font-mono text-[11px] ${k === i ? 'text-copper' : ''}`}>{String(k + 1).padStart(2, '0')}</span>
                  {c.phase}
                </button>
              </li>
            ))}
          </ol>

          <div id="case-panel" role="tabpanel" aria-label={p.phase} className="overflow-hidden rounded-2xl border border-line bg-void">
            <AnimatePresence mode="wait">
              <motion.div key={i} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }} className="grid h-full md:grid-cols-2">
                <div className="grain relative flex items-center border-b border-line p-6 md:border-b-0 md:border-r">
                  <ModuleVisual kind={p.visual} className="mx-auto h-56 w-full md:h-72" />
                  <p className="absolute bottom-3 left-4 text-[10px] uppercase tracking-[0.2em] text-mute">Schematic illustration</p>
                </div>
                <div className="flex flex-col p-7 md:p-9">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-copper">Phase {String(i + 1).padStart(2, '0')} / {String(CASE_STUDY.length).padStart(2, '0')}</p>
                  <h3 className="mt-3 font-serif text-4xl leading-tight">{p.phase}</h3>
                  <p className="mt-4 text-[15px] leading-relaxed text-ivory/90">{p.explain}</p>
                  <div className="mt-6 rounded-xl border border-line bg-coal p-4">
                    <p className="text-[10px] uppercase tracking-[0.22em] text-mute">Example</p>
                    <p className="mt-2 text-sm leading-relaxed text-mute-2">{p.example}</p>
                  </div>
                  <div className="mt-auto flex flex-wrap items-center justify-between gap-4 pt-8">
                    <Link to={`/architecture/${p.slug}`} className="group inline-flex items-center gap-2 text-sm text-ivory hover:text-copper">
                      {MODULES_BY_SLUG[p.slug].title} guide <ArrowUpRight className="h-4 w-4 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden />
                    </Link>
                    <div className="flex gap-2">
                      <button onClick={() => go(-1)} className="flex h-10 w-10 items-center justify-center rounded-full border border-line hover:border-ivory" aria-label="Previous phase"><ArrowLeft className="h-4 w-4" /></button>
                      <button onClick={() => go(1)} className="flex h-10 w-10 items-center justify-center rounded-full bg-ivory text-void hover:bg-copper" aria-label="Next phase"><ArrowRight className="h-4 w-4" /></button>
                    </div>
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
