import { Link } from 'react-router-dom';
import { ArrowUpRight, Terminal } from 'lucide-react';
import { useAuth } from '../../lib/auth';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';
import { useI18n } from '../../lib/i18n';
import { appUrl } from '../../lib/supabase';

const INSTALL = `git clone https://github.com/mattiadinunzio5-art/nexus.git
cd nexus
scripts/setup.sh
scripts/dev.sh          # http://127.0.0.1:5173`;

export function Access() {
  const { configured, session } = useAuth();
  const { t, p } = useI18n();
  const a = t.access;
  return (
    <section id="access" className="grain relative overflow-hidden border-t border-line bg-void py-28 md:py-40" aria-label={a.label}>
      <div className="relative mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="08">{a.label}</SectionLabel>
        <WordsReveal as="h2" key={a.title} text={a.title} className="font-serif text-[clamp(3.4rem,11vw,10rem)] leading-[0.88] tracking-tight" />
        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          <Reveal className="flex flex-col rounded-2xl border border-line bg-coal p-7 md:p-9">
            <p className="text-[11px] uppercase tracking-[0.24em] text-copper">{a.account}</p>
            {session ? (
              <>
                <h3 className="mt-3 text-2xl">{a.signedIn}</h3>
                <p className="mt-3 text-sm leading-relaxed text-mute-2">{session.user.email}</p>
                {appUrl && <p className="mt-3 text-sm leading-relaxed text-mute-2">{a.onlineText}</p>}
                <div className="mt-auto flex flex-wrap gap-3 pt-8">
                  {appUrl && <a href={appUrl} className="inline-flex items-center gap-2 rounded-full bg-copper px-6 py-3 text-sm font-medium text-void hover:bg-ivory">{a.openApp} <ArrowUpRight className="h-4 w-4" aria-hidden /></a>}
                  <Link to={p('/account')} className="inline-flex rounded-full bg-ivory px-6 py-3 text-sm font-medium text-void hover:bg-copper">{a.goAccount}</Link>
                </div>
              </>
            ) : configured ? (
              <>
                <h3 className="mt-3 text-2xl">{a.createTitle}</h3>
                <p className="mt-3 text-sm leading-relaxed text-mute-2">
                  {a.createText}
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-8">
                  <Link to={p('/signup')} className="inline-flex items-center gap-2 rounded-full bg-ivory px-6 py-3 text-sm font-medium text-void transition hover:bg-copper">{a.create} <ArrowUpRight className="h-4 w-4" aria-hidden /></Link>
                  <Link to={p('/signin')} className="inline-flex rounded-full border border-ivory/30 px-6 py-3 text-sm font-medium transition hover:border-ivory">{a.signIn}</Link>
                </div>
              </>
            ) : (
              <>
                <h3 className="mt-3 text-2xl">{a.closedTitle}</h3>
                <p className="mt-3 text-sm leading-relaxed text-mute-2" role="status">
                  {a.closedText}
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-8">
                  <span className="inline-flex cursor-not-allowed rounded-full border border-line px-6 py-3 text-sm text-mute" aria-disabled="true">{a.soon}</span>
                </div>
              </>
            )}
          </Reveal>
          <Reveal delay={0.1} className="flex flex-col rounded-2xl border border-line bg-coal p-7 md:p-9">
            <p className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-copper"><Terminal className="h-3.5 w-3.5" aria-hidden /> {a.run}</p>
            <h3 className="mt-3 text-2xl">{a.runTitle}</h3>
            <p className="mt-3 text-sm leading-relaxed text-mute-2">{a.runText}</p>
            <pre className="mt-6 overflow-x-auto rounded-xl border border-line bg-void p-4 font-mono text-[12px] leading-relaxed text-ivory/90"><code>{INSTALL}</code></pre>
            <p className="mt-4 text-xs text-mute">{a.lan[0]} <code className="text-ivory/80">--lan</code> {a.lan[1]}</p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
