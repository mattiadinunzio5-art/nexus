import { useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion, useScroll, useSpring, useTransform } from 'framer-motion';
import { ArrowUpRight } from 'lucide-react';
import { WORKFLOW } from '../../content/story';
import { MODULES_BY_SLUG } from '../../content/modules';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';
import { ModuleVisual } from '../ModuleVisual';

function StepCard({ i }: { i: number }) {
  const s = WORKFLOW[i];
  return (
    <Link to={`/architecture/${s.slug}`} className="group relative flex h-full flex-col justify-between rounded-2xl border border-line bg-coal p-7 transition-colors hover:border-copper/60 hover:bg-coal-2">
      <div className="flex items-center justify-between">
        <span className="font-serif text-5xl text-copper">{String(i + 1).padStart(2, '0')}</span>
        <ArrowUpRight className="h-5 w-5 text-mute transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-copper" aria-hidden />
      </div>
      <ModuleVisual kind={MODULES_BY_SLUG[s.slug].visual} className="my-4 h-28 w-full opacity-80 transition-opacity group-hover:opacity-100" />
      <div>
        <h3 className="text-2xl leading-tight">{s.step}</h3>
        <p className="mt-2 text-sm text-mute-2">{s.detail}</p>
        <p className="mt-5 text-[11px] uppercase tracking-[0.22em] text-mute">Module · {MODULES_BY_SLUG[s.slug].title}</p>
      </div>
    </Link>
  );
}

export function Workflow() {
  const reduce = useReducedMotion();
  const wrap = useRef<HTMLDivElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const [distance, setDistance] = useState(0);
  const { scrollYProgress } = useScroll({ target: wrap, offset: ['start start', 'end end'] });
  const x = useTransform(scrollYProgress, [0, 1], [0, -distance]);
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 30 });

  useLayoutEffect(() => {
    const measure = () => setDistance(Math.max(0, (track.current?.scrollWidth ?? 0) - window.innerWidth + 64));
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  const header = (
    <div className="mx-auto w-full max-w-[1440px] px-5 sm:px-8">
      <SectionLabel n="04">Research Workflow</SectionLabel>
      <WordsReveal as="h2" text="From a question to a report you can defend." className="max-w-4xl font-serif text-[clamp(2.4rem,6vw,5.5rem)] leading-[0.95] tracking-tight" />
    </div>
  );

  return (
    <section id="workflow" className="relative border-t border-line bg-void" aria-label="Research Workflow">
      {/* Desktop: scorrimento orizzontale guidato dallo scroll verticale */}
      {!reduce && (
        <div ref={wrap} className="relative hidden lg:block" style={{ height: `${Math.max(180, WORKFLOW.length * 38)}vh` }}>
          <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden pt-16">
            {header}
            <motion.div ref={track} style={{ x }} className="mt-14 flex gap-5 pl-8 pr-[30vw]">
              {WORKFLOW.map((_, i) => (
                <div key={i} className="relative h-[46vh] max-h-[420px] w-[340px] shrink-0">
                  <StepCard i={i} />
                  {i < WORKFLOW.length - 1 && <span className="absolute -right-5 top-1/2 h-px w-5 bg-line" aria-hidden />}
                </div>
              ))}
            </motion.div>
            <div className="mx-auto mt-10 w-full max-w-[1440px] px-8">
              <div className="h-px w-full bg-line"><motion.div style={{ scaleX: progress }} className="h-px origin-left bg-copper" /></div>
            </div>
          </div>
        </div>
      )}

      {/* Mobile, tablet e movimento ridotto: timeline verticale */}
      <div className={`py-28 ${reduce ? '' : 'lg:hidden'}`}>
        {header}
        <ol className="relative mx-auto mt-14 max-w-3xl px-5 sm:px-8">
          <span className="absolute bottom-6 left-[calc(1.25rem+11px)] top-6 w-px bg-line sm:left-[calc(2rem+11px)]" aria-hidden />
          {WORKFLOW.map((s, i) => (
            <Reveal key={i} delay={0.03}>
              <li className="relative flex gap-5 pb-6">
                <span className="relative z-10 mt-5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-copper bg-void font-mono text-[10px] text-copper">{i + 1}</span>
                <Link to={`/architecture/${s.slug}`} className="group flex-1 rounded-2xl border border-line bg-coal p-5 active:bg-coal-2">
                  <p className="text-lg">{s.step}</p>
                  <p className="mt-1 text-sm text-mute-2">{s.detail}</p>
                  <p className="mt-3 flex items-center gap-1 text-[11px] uppercase tracking-[0.2em] text-mute">{MODULES_BY_SLUG[s.slug].title} <ArrowUpRight className="h-3 w-3" aria-hidden /></p>
                </Link>
              </li>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
