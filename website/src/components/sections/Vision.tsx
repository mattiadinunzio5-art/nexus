import { useRef } from 'react';
import { motion, useScroll, useTransform, type MotionValue } from 'framer-motion';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';
import { useI18n } from '../../lib/i18n';


function Word({ children, progress, range }: { children: string; progress: MotionValue<number>; range: [number, number] }) {
  const opacity = useTransform(progress, range, [0.16, 1]);
  return (
    <motion.span style={{ opacity }} className="inline">
      {children}{' '}
    </motion.span>
  );
}

export function Vision() {
  const ref = useRef<HTMLParagraphElement>(null);
  const { t } = useI18n();
  const MANIFESTO = t.vision.manifesto;
  const POINTS = t.vision.points;
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.85', 'end 0.45'] });
  const words = MANIFESTO.split(' ');
  return (
    <section id="vision" className="relative bg-void py-28 md:py-40" aria-label={t.vision.label}>
      <div className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="01">{t.vision.label}</SectionLabel>
        <WordsReveal as="h2" key={t.vision.title} text={t.vision.title} className="max-w-5xl font-serif text-[clamp(2.6rem,7vw,6.5rem)] leading-[0.95] tracking-tight" />
        <p key={MANIFESTO} ref={ref} className="mt-16 max-w-4xl text-[clamp(1.25rem,2.6vw,2.15rem)] font-light leading-[1.35] text-ivory md:mt-24" aria-label={MANIFESTO}>
          {words.map((w, i) => (
            <Word key={i} progress={scrollYProgress} range={[i / words.length, (i + 1) / words.length]}>{w}</Word>
          ))}
        </p>
        <div className="mt-20 grid gap-px overflow-hidden rounded-2xl border border-line bg-line md:mt-28 md:grid-cols-2 lg:grid-cols-4">
          {POINTS.map((p, i) => (
            <Reveal key={p.n} delay={i * 0.08} className="group relative bg-coal p-7 transition-colors hover:bg-coal-2 md:p-8">
              <span className="font-serif text-4xl text-copper">{p.n}</span>
              <h3 className="mt-10 text-lg font-medium">{p.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-mute-2">{p.text}</p>
              <span className="absolute inset-x-0 bottom-0 h-px origin-left scale-x-0 bg-copper transition-transform duration-700 group-hover:scale-x-100" aria-hidden />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
