import { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { HeroGraph } from '../HeroGraph';
import { useI18n } from '../../lib/i18n';

const EASE = [0.22, 1, 0.36, 1] as const;

export function Hero() {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const { t, p } = useI18n();
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const graphScale = useTransform(scrollYProgress, [0, 1], [1, reduce ? 1 : 1.35]);
  const graphOpacity = useTransform(scrollYProgress, [0, 0.85], [1, 0]);
  const titleY = useTransform(scrollYProgress, [0, 1], ['0%', reduce ? '0%' : '-35%']);
  const contentOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);

  return (
    <section ref={ref} className="grain relative flex min-h-[100svh] flex-col overflow-hidden bg-void" aria-labelledby="hero-title">
      <motion.div style={{ scale: graphScale, opacity: graphOpacity }} className="absolute inset-0 md:left-[30%]">
        <HeroGraph className="h-full w-full" />
      </motion.div>
      {/* Velatura per la leggibilità del testo sopra il grafo. */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_70%,rgba(11,11,13,0.92),rgba(11,11,13,0.25)_60%,transparent)]" aria-hidden />

      <motion.div style={{ opacity: contentOpacity }} className="relative z-10 mx-auto flex w-full max-w-[1440px] flex-1 flex-col justify-end px-5 pb-10 pt-28 sm:px-8 md:pb-14">
        <motion.p
          initial={reduce ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: EASE, delay: 0.2 }}
          className="mb-6 flex items-center gap-3 text-[11px] uppercase tracking-[0.3em] text-mute-2"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-copper" aria-hidden /> {t.hero.eyebrow}
        </motion.p>

        <motion.h1 id="hero-title" style={{ y: titleY }} className="select-none text-[clamp(5.2rem,24vw,23rem)] font-semibold leading-[0.78] tracking-[-0.06em]" aria-label="NEXUS">
          {'NEXUS'.split('').map((c, i) => (
            <span key={i} aria-hidden className="inline-block overflow-hidden">
              <motion.span
                className="inline-block"
                initial={reduce ? false : { y: '105%' }}
                animate={{ y: '0%' }}
                transition={{ duration: 1.2, ease: EASE, delay: 0.25 + i * 0.07 }}
              >
                {c}
              </motion.span>
            </span>
          ))}
        </motion.h1>

        <div className="mt-8 grid gap-8 md:mt-10 md:grid-cols-[1.2fr_1fr] md:items-end">
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: EASE, delay: 0.75 }}
            className="font-serif text-[clamp(2rem,4.6vw,4.2rem)] italic leading-[1.02] text-balance"
          >
            {t.hero.tagline}
          </motion.p>
          <motion.div initial={reduce ? false : { opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease: EASE, delay: 0.9 }}>
            <p className="max-w-md text-[15px] leading-relaxed text-mute-2">
              {t.hero.intro}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to={p('/#vision')} className="group inline-flex items-center gap-2 rounded-full bg-ivory px-6 py-3 text-sm font-medium text-void transition hover:bg-copper">
                {t.hero.explore} <ArrowDownRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:translate-y-0.5" aria-hidden />
              </Link>
              <Link to={p('/#access')} className="group inline-flex items-center gap-2 rounded-full border border-ivory/30 px-6 py-3 text-sm font-medium transition hover:border-ivory">
                {t.hero.enter} <ArrowUpRight className="h-4 w-4 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden />
              </Link>
            </div>
          </motion.div>
        </div>
      </motion.div>

      <div className="relative z-10 border-t border-line/60">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-5 py-4 text-[10px] uppercase tracking-[0.28em] text-mute sm:px-8">
          <span>{t.hero.modules}</span>
          <span className="flex items-center gap-2"><span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-copper opacity-60 motion-reduce:hidden" /><span className="relative inline-flex h-2 w-2 rounded-full bg-copper" /></span>{t.hero.scroll}</span>
          <span className="hidden sm:inline">{t.hero.strip}</span>
        </div>
      </div>
    </section>
  );
}
