import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from 'framer-motion';
import { useAuth } from '../lib/auth';
import { counterpart, useI18n } from '../lib/i18n';

export function useNav() {
  const { t, p } = useI18n();
  return [
    { label: t.nav.vision, to: p('/#why') },
    { label: t.nav.architecture, to: p('/#modules') },
    { label: t.nav.workflow, to: p('/#how') },
    { label: t.nav.caseStudy, to: p('/#case') },
    { label: t.nav.cases, to: p('/cases') },
    { label: t.nav.access, to: p('/#access') },
  ];
}

function LangSwitch({ className = '' }: { className?: string }) {
  const { t, lang } = useI18n();
  const { pathname, hash } = useLocation();
  return (
    <Link to={counterpart(pathname, hash)} hrefLang={lang === 'en' ? 'it' : 'en'} lang={lang === 'en' ? 'it' : 'en'}
      className={`rounded-full border border-line px-3 py-2 text-[12px] font-medium text-mute-2 transition hover:border-ivory hover:text-ivory ${className}`}
      aria-label={`${t.language}: ${t.switchTo}`}>
      {t.switchToShort}
    </Link>
  );
}

export function Logo({ className = '' }: { className?: string }) {
  const { p } = useI18n();
  return (
    <Link to={p('/')} className={`group flex items-center gap-2.5 ${className}`} aria-label="NEXUS — home">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <path d="M9 23V9l14 14V9" fill="none" stroke="#D97736" strokeWidth="1.8" strokeLinecap="round" />
        {[[9, 9], [23, 23], [9, 23], [23, 9]].map(([x, y]) => <circle key={`${x}${y}`} cx={x} cy={y} r="2.1" fill="#F3F0E9" />)}
      </svg>
      <span className="text-[15px] font-semibold tracking-[0.32em]">NEXUS</span>
    </Link>
  );
}

export function Navbar() {
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [open, setOpen] = useState(false);
  const { session } = useAuth();
  const { pathname, hash } = useLocation();
  const { t, p } = useI18n();
  const NAV = useNav();

  useMotionValueEvent(scrollY, 'change', (y) => {
    const prev = scrollY.getPrevious() ?? 0;
    setScrolled(y > 24);
    setHidden(y > 400 && y > prev && !open);
  });
  useEffect(() => setOpen(false), [pathname, hash]);
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  return (
    <>
      <motion.header
        animate={{ y: hidden ? -96 : 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        className={`fixed inset-x-0 top-0 z-50 transition-colors duration-500 ${scrolled || open ? 'border-b border-line/70 bg-void/80 backdrop-blur-xl' : 'border-b border-transparent'}`}
      >
        <nav className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-5 sm:px-8" aria-label={t.navMain}>
          <Logo />
          <ul className="hidden items-center gap-1 rounded-full border border-line/80 bg-coal/60 p-1 backdrop-blur md:flex">
            {NAV.map((n) => (
              <li key={n.to}>
                <Link to={n.to} className={`block rounded-full px-4 py-1.5 text-[13px] transition-colors hover:bg-ivory hover:text-void ${n.to.endsWith(hash) && hash ? 'bg-ivory text-void' : pathname === n.to ? 'bg-ivory text-void' : 'text-mute-2'}`}>
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-2">
            <LangSwitch />
            <NavLink to={p(session ? '/account' : '/signin')} className="hidden rounded-full bg-ivory px-4 py-2 text-[13px] font-medium text-void transition hover:bg-copper sm:block">
              {session ? t.account : t.signIn}
            </NavLink>
            <button
              onClick={() => setOpen((o) => !o)}
              className="flex h-10 w-10 flex-col items-center justify-center gap-1.5 rounded-full border border-line md:hidden"
              aria-label={open ? t.closeMenu : t.openMenu}
              aria-expanded={open}
              aria-controls="mobile-menu"
            >
              <span className={`h-px w-4 bg-ivory transition ${open ? 'translate-y-[3.5px] rotate-45' : ''}`} />
              <span className={`h-px w-4 bg-ivory transition ${open ? '-translate-y-[3.5px] -rotate-45' : ''}`} />
            </button>
          </div>
        </nav>
      </motion.header>
      <AnimatePresence>
        {open && (
          <motion.div
            id="mobile-menu"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-40 flex flex-col bg-void px-6 pb-10 pt-24 md:hidden"
          >
            <ul className="flex-1 space-y-1">
              {NAV.map((n, i) => (
                <motion.li key={n.to} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 + i * 0.05, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}>
                  <Link to={n.to} className="flex items-baseline gap-4 border-b border-line py-4 font-serif text-4xl">
                    <span className="font-sans text-xs text-mute">0{i + 1}</span>
                    {n.label}
                  </Link>
                </motion.li>
              ))}
            </ul>
            <Link to={p(session ? '/account' : '/signin')} className="rounded-full bg-ivory py-4 text-center font-medium text-void">
              {session ? t.account : t.signIn}
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
