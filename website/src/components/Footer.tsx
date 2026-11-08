import { Link } from 'react-router-dom';
import { Logo, useNav } from './Navbar';
import { useI18n } from '../lib/i18n';

export function Footer() {
  const { t, p, modules } = useI18n();
  const NAV = useNav();
  return (
    <footer className="border-t border-line bg-void">
      <div className="mx-auto grid max-w-[1440px] gap-12 px-5 py-16 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Logo />
          <p className="mt-5 max-w-sm text-sm leading-relaxed text-mute">{t.footer.about}</p>
        </div>
        <div>
          <p className="mb-4 text-[11px] uppercase tracking-[0.24em] text-mute">{t.footer.site}</p>
          <ul className="space-y-2 text-sm">{NAV.map((n) => <li key={n.to}><Link to={n.to} className="text-mute-2 hover:text-ivory">{n.label}</Link></li>)}</ul>
        </div>
        <div>
          <p className="mb-4 text-[11px] uppercase tracking-[0.24em] text-mute">{t.footer.modules}</p>
          <ul className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2 md:grid-cols-1 lg:grid-cols-2">
            {modules.map((m) => <li key={m.slug}><Link to={p(`/architecture/${m.slug}`)} className="text-mute-2 hover:text-ivory" translate="no">{m.title}</Link></li>)}
          </ul>
        </div>
      </div>
      <div className="mx-auto flex max-w-[1440px] flex-wrap justify-between gap-3 border-t border-line px-5 py-6 text-[11px] uppercase tracking-[0.2em] text-mute sm:px-8">
        <span>© {new Date().getFullYear()} NEXUS</span>
        <span className="flex flex-wrap gap-4">
          <Link to={p('/privacy')} className="hover:text-ivory">{t.footer.privacy}</Link>
          <a href="mailto:mattiadinunzio5@gmail.com" className="hover:text-ivory">{t.footer.contact}</a>
        </span>
        <span>{t.footer.tagline}</span>
      </div>
    </footer>
  );
}
