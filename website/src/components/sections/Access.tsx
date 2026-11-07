import { Link } from 'react-router-dom';
import { ArrowUpRight, Terminal } from 'lucide-react';
import { useAuth } from '../../lib/auth';
import { Reveal, SectionLabel, WordsReveal } from '../Reveal';

const INSTALL = `git clone https://github.com/mattiadinunzio5-art/nexus.git
cd nexus
scripts/setup.sh
scripts/dev.sh          # http://127.0.0.1:5173`;

export function Access() {
  const { configured, session } = useAuth();
  return (
    <section id="access" className="grain relative overflow-hidden border-t border-line bg-void py-28 md:py-40" aria-label="Access">
      <div className="relative mx-auto max-w-[1440px] px-5 sm:px-8">
        <SectionLabel n="07">Access</SectionLabel>
        <WordsReveal as="h2" text="Enter the Nexus." className="font-serif text-[clamp(3.4rem,11vw,10rem)] leading-[0.88] tracking-tight" />
        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          <Reveal className="flex flex-col rounded-2xl border border-line bg-coal p-7 md:p-9">
            <p className="text-[11px] uppercase tracking-[0.24em] text-copper">Account</p>
            {session ? (
              <>
                <h3 className="mt-3 text-2xl">You are signed in.</h3>
                <p className="mt-3 text-sm leading-relaxed text-mute-2">{session.user.email}</p>
                <div className="mt-auto pt-8"><Link to="/account" className="inline-flex rounded-full bg-ivory px-6 py-3 text-sm font-medium text-void hover:bg-copper">Go to your account</Link></div>
              </>
            ) : configured ? (
              <>
                <h3 className="mt-3 text-2xl">Create your NEXUS account.</h3>
                <p className="mt-3 text-sm leading-relaxed text-mute-2">
                  Your account identifies you on this site and reserves your access to the hosted platform. Today the platform itself runs on your own computer — see the right panel.
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-8">
                  <Link to="/signup" className="inline-flex items-center gap-2 rounded-full bg-ivory px-6 py-3 text-sm font-medium text-void transition hover:bg-copper">Create Account <ArrowUpRight className="h-4 w-4" aria-hidden /></Link>
                  <Link to="/signin" className="inline-flex rounded-full border border-ivory/30 px-6 py-3 text-sm font-medium transition hover:border-ivory">Sign In</Link>
                </div>
              </>
            ) : (
              <>
                <h3 className="mt-3 text-2xl">Online registration is not open yet.</h3>
                <p className="mt-3 text-sm leading-relaxed text-mute-2" role="status">
                  Account creation will be enabled once the authentication service is configured for this site. Until then no form pretends to sign you in — you can already use NEXUS by running it on your own computer.
                </p>
                <div className="mt-auto flex flex-wrap gap-3 pt-8">
                  <span className="inline-flex cursor-not-allowed rounded-full border border-line px-6 py-3 text-sm text-mute" aria-disabled="true">Create Account — coming soon</span>
                </div>
              </>
            )}
          </Reveal>
          <Reveal delay={0.1} className="flex flex-col rounded-2xl border border-line bg-coal p-7 md:p-9">
            <p className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-copper"><Terminal className="h-3.5 w-3.5" aria-hidden /> Run the platform</p>
            <h3 className="mt-3 text-2xl">Use NEXUS today, on your computer.</h3>
            <p className="mt-3 text-sm leading-relaxed text-mute-2">Free and open-source. Requires Python 3.11–3.13, Node.js and Git. On Windows use Git Bash.</p>
            <pre className="mt-6 overflow-x-auto rounded-xl border border-line bg-void p-4 font-mono text-[12px] leading-relaxed text-ivory/90"><code>{INSTALL}</code></pre>
            <p className="mt-4 text-xs text-mute">Add <code className="text-ivory/80">--lan</code> to open it from your phone on the same Wi-Fi, with mandatory login.</p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
