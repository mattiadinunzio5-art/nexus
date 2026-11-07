import { motion, useReducedMotion, type HTMLMotionProps } from 'framer-motion';
import type { ReactNode } from 'react';

const EASE = [0.22, 1, 0.36, 1] as const;

export function Reveal({ children, delay = 0, y = 28, className, ...rest }: { children: ReactNode; delay?: number; y?: number } & HTMLMotionProps<'div'>) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-12% 0px' }}
      transition={{ duration: 0.9, ease: EASE, delay }}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

/**
 * Titolo che compare parola per parola. L'osservazione dello scroll è sul titolo intero
 * (le singole parole partono nascoste dal loro contenitore e non risulterebbero mai «visibili»).
 * Il testo completo resta leggibile ai lettori di schermo tramite aria-label.
 */
export function WordsReveal({ text, className, as = 'h2', delay = 0 }: { text: string; className?: string; as?: 'h1' | 'h2' | 'h3' | 'p'; delay?: number }) {
  const reduce = useReducedMotion();
  const Tag = motion[as];
  const words = text.split(' ');
  return (
    <Tag className={className} aria-label={text} initial={reduce ? false : 'hidden'} whileInView="show" viewport={{ once: true, margin: '-8% 0px' }}>
      {words.map((w, i) => (
        <span key={i} aria-hidden className="inline-block overflow-hidden pb-[0.08em] align-bottom">
          <motion.span
            className="inline-block"
            variants={{ hidden: { y: '110%' }, show: { y: '0%', transition: { duration: 0.85, ease: EASE, delay: delay + i * 0.045 } } }}
          >
            {w}
            {i < words.length - 1 ? '\u00a0' : ''}
          </motion.span>
        </span>
      ))}
    </Tag>
  );
}

export function SectionLabel({ n, children }: { n: string; children: ReactNode }) {
  return (
    <p className="mb-6 flex items-center gap-3 text-[11px] font-medium uppercase tracking-[0.28em] text-mute">
      <span className="h-1.5 w-1.5 rounded-full bg-copper" aria-hidden />
      <span className="font-mono text-mute-2">({n})</span>
      {children}
    </p>
  );
}
