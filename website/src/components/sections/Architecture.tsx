import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowUpRight } from 'lucide-react';
import { useI18n } from '../../lib/i18n';
import { ModuleVisual } from '../ModuleVisual';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';

export function Architecture() {
  const [active, setActive] = useState(0);
  const { t, p, modules: MODULES } = useI18n();
  const m = MODULES[active];
  return (
    <section id="architecture" className="relative border-t border-line bg-void py-28 md:py-36" aria-label={t.arch.label}>
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <div className="grid gap-8 md:grid-cols-[1.4fr_1fr] md:items-end">
          <div>
            <SectionLabel n="03">{t.arch.label}</SectionLabel>
            <WordsReveal as="h2" key={t.arch.title} text={t.arch.title} className="font-serif text-[clamp(2.6rem,6.5vw,6rem)] leading-[0.95] tracking-tight" />
          </div>
          <Reveal>
            <p className="text-[15px] leading-relaxed text-mute-2">
              {t.arch.intro}
            </p>
          </Reveal>
        </div>

        {/* Desktop: indice editoriale + pannello fisso */}
        <div className="mt-20 hidden gap-16 lg:grid lg:grid-cols-[1.15fr_1fr]">
          <ol role="list" className="border-t border-line">
            {MODULES.map((mod, i) => (
              <li key={mod.slug} className="border-b border-line">
                <Link
                  to={p(`/architecture/${mod.slug}`)}
                  onMouseEnter={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  className="group flex items-baseline gap-6 py-4"
                  aria-describedby={i === active ? 'module-preview' : undefined}
                >
                  <span className={`w-8 font-mono text-xs transition-colors ${i === active ? 'text-copper' : 'text-mute'}`}>{mod.index}</span>
                  <span className={`flex-1 text-[clamp(1.6rem,2.6vw,2.6rem)] leading-tight tracking-tight transition-all duration-500 ${i === active ? 'translate-x-2 text-ivory' : 'text-mute group-hover:text-mute-2'}`}>
                    {mod.title}
                  </span>
                  <span className={`text-[11px] uppercase tracking-[0.2em] transition-opacity ${i === active ? 'text-copper opacity-100' : 'opacity-0'}`}>{mod.kicker}</span>
                </Link>
              </li>
            ))}
          </ol>
          <div className="relative">
            <div className="sticky top-24">
              <AnimatePresence mode="wait">
                <motion.div
                  key={m.slug}
                  id="module-preview"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                  className="overflow-hidden rounded-2xl border border-line bg-coal"
                >
                  <div className="grain relative border-b border-line bg-void/60 p-6">
                    <ModuleVisual kind={m.visual} className="mx-auto h-56 w-full" />
                  </div>
                  <div className="p-8">
                    <p className="text-[11px] uppercase tracking-[0.24em] text-copper">{m.index} · {m.kicker}</p>
                    <h3 className="mt-3 font-serif text-4xl">{m.tagline}</h3>
                    <p className="mt-4 text-sm leading-relaxed text-mute-2">{m.description}</p>
                    <Link to={p(`/architecture/${m.slug}`)} className="group mt-7 inline-flex items-center gap-2 rounded-full bg-ivory px-5 py-2.5 text-sm font-medium text-void transition hover:bg-copper">
                      {t.arch.open(m.title)} <ArrowUpRight className="h-4 w-4 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden />
                    </Link>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Mobile e tablet: schede a scorrimento verticale */}
        <ol className="mt-14 space-y-3 lg:hidden">
          {MODULES.map((mod, i) => (
            <Reveal key={mod.slug} delay={Math.min(i, 3) * 0.04}>
              <li>
                <Link to={p(`/architecture/${mod.slug}`)} className="group flex items-center gap-4 overflow-hidden rounded-2xl border border-line bg-coal p-4 active:bg-coal-2">
                  <div className="h-20 w-28 shrink-0 rounded-xl bg-void/70 p-1.5"><ModuleVisual kind={mod.visual} className="h-full w-full" /></div>
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-[11px] text-copper">{mod.index}</p>
                    <p className="text-lg leading-tight">{mod.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-mute">{mod.tagline}</p>
                  </div>
                  <ArrowUpRight className="h-5 w-5 shrink-0 text-mute" aria-hidden />
                </Link>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
