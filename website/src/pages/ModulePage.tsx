import { Link, Navigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, ArrowUpRight, Check, Info } from 'lucide-react';
import { MODULES, MODULES_BY_SLUG, type ModuleSlug } from '../content/modules';
import { ModuleVisual } from '../components/ModuleVisual';
import { Reveal, WordsReveal } from '../components/Reveal';
import { usePageMeta } from '../lib/meta';

function Block({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <Reveal className="grid gap-6 border-t border-line py-12 md:grid-cols-[260px_1fr] md:py-16">
      <h2 className="flex items-baseline gap-3 text-sm uppercase tracking-[0.22em] text-mute">
        <span className="font-mono text-copper">{n}</span>{title}
      </h2>
      <div>{children}</div>
    </Reveal>
  );
}

export function ModulePage() {
  const { slug } = useParams();
  const m = MODULES_BY_SLUG[slug as ModuleSlug];
  usePageMeta(m ? `${m.title} — guide` : 'Module not found', m ? `${m.tagline} ${m.mainFunction}` : undefined);
  if (!m) return <Navigate to="/404" replace />;
  const idx = MODULES.indexOf(m);
  const prev = MODULES[(idx - 1 + MODULES.length) % MODULES.length];
  const next = MODULES[(idx + 1) % MODULES.length];

  return (
    <article className="bg-void pt-28">
      <header className="mx-auto max-w-[1440px] px-5 sm:px-8">
        <Link to="/#architecture" className="inline-flex items-center gap-2 text-sm text-mute hover:text-ivory"><ArrowLeft className="h-4 w-4" aria-hidden /> Architecture</Link>
        <div className="mt-10 grid gap-10 lg:grid-cols-[1.3fr_1fr] lg:items-end">
          <div>
            <p className="text-[11px] uppercase tracking-[0.28em] text-copper">Module {m.index} · {m.kicker}</p>
            <WordsReveal as="h1" text={m.title} className="mt-4 text-[clamp(3rem,9vw,8rem)] font-semibold leading-[0.9] tracking-[-0.04em]" />
            <p className="mt-6 font-serif text-[clamp(1.6rem,3vw,2.6rem)] italic leading-tight text-ivory/90">{m.tagline}</p>
          </div>
          <Reveal className="grain relative overflow-hidden rounded-2xl border border-line bg-coal p-6">
            <ModuleVisual kind={m.visual} className="h-56 w-full" />
          </Reveal>
        </div>
      </header>

      <div className="mx-auto mt-16 max-w-[1440px] px-5 pb-10 sm:px-8 md:mt-24">
        <Block n="01" title="Description"><p className="max-w-3xl text-[clamp(1.1rem,1.8vw,1.4rem)] leading-relaxed">{m.description}</p></Block>
        <Block n="02" title="Main function"><p className="max-w-3xl font-serif text-[clamp(1.5rem,2.6vw,2.2rem)] leading-snug">{m.mainFunction}</p></Block>
        <Block n="03" title="Why it is useful">
          <ul className="grid gap-4 md:grid-cols-3">
            {m.whyUseful.map((w) => <li key={w} className="rounded-xl border border-line bg-coal p-5 text-sm leading-relaxed text-mute-2"><Check className="mb-3 h-4 w-4 text-copper" aria-hidden />{w}</li>)}
          </ul>
        </Block>
        <Block n="04" title="How to use it">
          <ol className="space-y-px overflow-hidden rounded-xl border border-line bg-line">
            {m.guide.map((g, i) => (
              <li key={g.title} className="flex gap-5 bg-coal p-5 md:p-6">
                <span className="font-serif text-3xl leading-none text-copper">{i + 1}</span>
                <div><p className="font-medium">{g.title}</p><p className="mt-1 text-sm leading-relaxed text-mute-2">{g.detail}</p></div>
              </li>
            ))}
          </ol>
        </Block>
        <Block n="05" title="What it needs">
          <ul className="space-y-2">{m.inputs.map((x) => <li key={x} className="flex gap-3 text-[15px] text-ivory/90"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" aria-hidden />{x}</li>)}</ul>
        </Block>
        <Block n="06" title="What it produces">
          <ul className="space-y-2">{m.outputs.map((x) => <li key={x} className="flex gap-3 text-[15px] text-ivory/90"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-ivory" aria-hidden />{x}</li>)}</ul>
        </Block>
        <Block n="07" title="Example">
          <div className="rounded-2xl border border-line bg-coal p-6 md:p-8">
            <p className="font-serif text-2xl">{m.example.title}</p>
            <ol className="mt-5 space-y-3">{m.example.steps.map((s, i) => <li key={s} className="flex gap-4 text-sm leading-relaxed text-mute-2"><span className="font-mono text-xs text-copper">{String(i + 1).padStart(2, '0')}</span>{s}</li>)}</ol>
          </div>
        </Block>
        <Block n="08" title="Connected modules">
          <ul className="grid gap-3 md:grid-cols-3">
            {m.connections.map((c) => (
              <li key={c.slug}>
                <Link to={`/architecture/${c.slug}`} className="group flex h-full flex-col rounded-xl border border-line bg-coal p-5 transition-colors hover:border-copper/50">
                  <span className="flex items-center justify-between font-medium">{MODULES_BY_SLUG[c.slug].title}<ArrowUpRight className="h-4 w-4 text-mute group-hover:text-copper" aria-hidden /></span>
                  <span className="mt-2 text-sm text-mute-2">{c.why}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Block>
        <Block n="09" title="Limits">
          <ul className="space-y-3">{m.limits.map((l) => <li key={l} className="flex gap-3 rounded-xl border border-copper/30 bg-copper/5 p-4 text-sm leading-relaxed text-mute-2"><Info className="mt-0.5 h-4 w-4 shrink-0 text-copper" aria-hidden />{l}</li>)}</ul>
        </Block>
      </div>

      <nav className="border-t border-line" aria-label="Other modules">
        <div className="mx-auto grid max-w-[1440px] md:grid-cols-2">
          <Link to={`/architecture/${prev.slug}`} className="group flex items-center gap-4 border-b border-line px-5 py-10 sm:px-8 md:border-b-0 md:border-r">
            <ArrowLeft className="h-5 w-5 text-mute transition group-hover:-translate-x-1 group-hover:text-copper" aria-hidden />
            <span><span className="block text-[11px] uppercase tracking-[0.22em] text-mute">Previous · {prev.index}</span><span className="text-2xl">{prev.title}</span></span>
          </Link>
          <Link to={`/architecture/${next.slug}`} className="group flex items-center justify-end gap-4 px-5 py-10 text-right sm:px-8">
            <span><span className="block text-[11px] uppercase tracking-[0.22em] text-mute">Next · {next.index}</span><span className="text-2xl">{next.title}</span></span>
            <ArrowRight className="h-5 w-5 text-mute transition group-hover:translate-x-1 group-hover:text-copper" aria-hidden />
          </Link>
        </div>
      </nav>
    </article>
  );
}
