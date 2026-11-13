import { NavLink, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { rememberedSearch } from '../../lib/lastLocation';
import { ChevronDown, ShieldCheck, X } from 'lucide-react';
import { useAuth } from '../../state/Auth';
import { ARCHIVE_NAV, MAIN_NAV, MODULE_NAV, SYSTEM_NAV, type NavItem } from '../../lib/nav';

function Item({ item, onNavigate, badge }: { item: NavItem; onNavigate: () => void; badge?: number }) {
  const Icon = item.icon;
  const { pathname } = useLocation();
  const extra = item.alsoActive?.some((p) => pathname === p || pathname.startsWith(p + '/')) ?? false;
  return (
    <NavLink
      to={item.to + rememberedSearch(item.to)}
      end={item.to === '/'}
      data-module={item.moduleId}
      onClick={onNavigate}
      className={({ isActive: active }) => {
        const isActive = active || extra;
        return `group flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors ${
          isActive ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:bg-ink-850 hover:text-paper'
        }`;
      }}
    >
      {({ isActive: active }) => { const isActive = active || extra; return (
        <>
          <Icon className={`size-4 shrink-0 ${isActive ? 'text-gold-400' : ''}`} aria-hidden />
          {item.code && <span className="w-3 font-mono text-[11px] text-steel-500">{item.code}</span>}
          <span className="min-w-0 flex-1 truncate">{item.label}</span>
          {item.phase !== undefined && (
            <span className="font-mono text-[10px] text-steel-500" title={`In preparazione — Fase ${item.phase}`}>
              F{item.phase}
            </span>
          )}
          {!!badge && (
            <span className="rounded bg-gold-400 px-1.5 text-[10px] font-semibold text-ink-950" aria-label={`${badge} non lette`}>
              {badge}
            </span>
          )}
        </>
      ); }}
    </NavLink>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <p className="mb-1.5 px-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-steel-500">{title}</p>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

const SYSTEM_KEY = 'nexus.sidebar.system';

/** Sezione «System» richiudibile: chiusa di default, aperta da sola se si è su una delle sue pagine. */
function SystemSection({ isAdmin, onNavigate }: { isAdmin: boolean; onNavigate: () => void }) {
  const { pathname } = useLocation();
  const items = isAdmin ? [...SYSTEM_NAV, { to: '/admin', label: 'Administration', icon: ShieldCheck }] : SYSTEM_NAV;
  const here = items.some((i) => pathname === i.to || pathname.startsWith(i.to + '/'));
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(SYSTEM_KEY) === '1'; } catch { return false; }
  });
  const shown = open || here;
  const toggle = () => {
    const next = !shown;
    setOpen(next);
    try { localStorage.setItem(SYSTEM_KEY, next ? '1' : '0'); } catch { /* storage non disponibile */ }
  };
  return (
    <div className="mt-5">
      <button type="button" onClick={toggle} aria-expanded={shown} aria-controls="nexus-system-nav"
        className="mb-1.5 flex w-full items-center justify-between rounded px-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-steel-500 hover:text-paper">
        System <ChevronDown className={`size-3.5 transition-transform ${shown ? 'rotate-180' : ''}`} aria-hidden />
      </button>
      {shown && <div id="nexus-system-nav" className="space-y-0.5">{items.map((i) => <Item key={i.to} item={i} onNavigate={onNavigate} />)}</div>}
    </div>
  );
}

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { mode, user } = useAuth();
  const isAdmin = mode !== 'local' && user?.role === 'admin';
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-black/50 lg:hidden" onClick={onClose} aria-hidden />}
      <aside
        id="nexus-sidebar"
        aria-label="Navigazione principale"
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-ink-700 bg-ink-900 lg:static lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-ink-700 px-4">
          <div className="flex items-baseline gap-2">
            <span className="text-base font-semibold tracking-[0.3em] text-gold-400">NEXUS</span>
            <span className="text-[10px] uppercase tracking-widest text-steel-500">v0.1</span>
          </div>
          <button className="rounded p-1 text-steel-400 hover:text-paper lg:hidden" onClick={onClose} aria-label="Chiudi menu">
            <X className="size-4" />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 pb-6 pt-1">
          <Section title="Overview">
            {MAIN_NAV.map((i) => <Item key={i.to} item={i} onNavigate={onClose} />)}
          </Section>
          <Section title="Archive">
            {ARCHIVE_NAV.map((i) => <Item key={i.to} item={i} onNavigate={onClose} />)}
          </Section>
          <Section title="Modules">
            {MODULE_NAV.map((i) => <Item key={i.to} item={i} onNavigate={onClose} />)}
          </Section>
          <SystemSection isAdmin={isAdmin} onNavigate={onClose} />
        </nav>
        <p className="border-t border-ink-700 px-4 py-3 text-[11px] leading-relaxed text-steel-500">
          {mode !== 'local' && user ? <>Connesso come <span className="text-steel-300">{user.display_name}</span> · piano {user.plan}</> : 'Modalità locale personale · dati sul tuo computer'}
        </p>
      </aside>
    </>
  );
}
