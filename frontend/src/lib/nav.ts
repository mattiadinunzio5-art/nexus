import {
  Activity,
  Newspaper,
  BookMarked,
  FileText,
  MessageSquareQuote,
  BookOpenText,
  Briefcase,
  ChartLine,
  Compass,
  Database,
  FlaskConical,
  FolderKanban,
  Landmark,
  LayoutDashboard,
  Network,
  Radar,
  Scale,
  Settings,
  Swords,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  code?: string;
  phase?: number;
  moduleId?: string;
  /** Altri percorsi in cui la voce risulta attiva (es. la Time Machine dentro Historical Intelligence). */
  alsoActive?: string[];
}

/**
 * Navigazione. I moduli condividono gli id con il registro del backend
 * (core/modules.py), che resta la fonte di verità per stato e contenuti.
 */
export const MODULE_NAV: NavItem[] = [
  { to: '/discovery', label: 'Discovery Intelligence', icon: Radar },
  { to: '/history', label: 'Historical Intelligence', icon: Landmark, moduleId: 'historical', alsoActive: ['/time-machine'] },
  { to: '/financial', moduleId: 'financial', label: 'Financial Intelligence', icon: ChartLine },
  { to: '/graph', label: 'Knowledge Graph', icon: Network, moduleId: 'knowledge-graph' },
  { to: '/war-room', moduleId: 'war-room', label: 'Research War Room', icon: Swords },
  { to: '/lab', moduleId: 'economic-lab', label: 'Economic Laboratory', icon: FlaskConical },
  { to: '/studio', moduleId: 'research-studio', label: 'Research Studio', icon: BookOpenText },
];

/** Moduli raggiungibili come scheda di un altro (non nel menu, ma con una pagina propria). */
const MODULE_ROUTES_EXTRA: Record<string, string> = { 'time-machine': '/time-machine', business: '/account' };

export const MAIN_NAV: NavItem[] = [
  { to: '/start', label: 'Inizia da qui', icon: Compass },
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/briefing', label: 'Daily Briefing', icon: Newspaper },
  { to: '/projects', label: 'Projects', icon: FolderKanban },
];

export const ARCHIVE_NAV: NavItem[] = [
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/bibliography', label: 'Bibliography', icon: BookMarked },
  { to: '/research', label: 'Ask the Archive', icon: MessageSquareQuote },
];

/** Sezione «System», chiusa per impostazione predefinita. Le notifiche sono nella campanella in alto. */
export const SYSTEM_NAV: NavItem[] = [
  { to: '/account', label: 'Account & piano', icon: Briefcase, moduleId: 'business' },
  { to: '/sources', label: 'Sources & Connectors', icon: Database },
  { to: '/activity', label: 'Activity Log', icon: Activity },
  { to: '/settings', label: 'Impostazioni', icon: Settings },
  { to: '/data-policy', label: 'Copyright & Data Policy', icon: Scale },
];

/** Percorso della pagina di un modulo (pagina reale se implementato, altrimenti scheda «in preparazione»). */
export function moduleRoute(id: string): string {
  return MODULE_NAV.find((n) => n.moduleId === id)?.to ?? MODULE_ROUTES_EXTRA[id] ?? `/modules/${id}`;
}
