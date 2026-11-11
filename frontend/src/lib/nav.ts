import {
  Activity,
  Bell,
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
  GraduationCap,
  History,
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
}

/**
 * Navigazione. I moduli condividono gli id con il registro del backend
 * (core/modules.py), che resta la fonte di verità per stato e contenuti.
 */
export const MODULE_NAV: NavItem[] = [
  { to: '/discovery', label: 'Discovery Intelligence', icon: Radar, code: '◆' },
  { to: '/history', label: 'Historical Intelligence', icon: Landmark, code: 'A', moduleId: 'historical' },
  { to: '/financial', moduleId: 'financial', label: 'Financial Intelligence', icon: ChartLine, code: 'B' },
  { to: '/time-machine', label: 'Time Machine', icon: History, code: 'C', moduleId: 'time-machine' },
  { to: '/graph', label: 'Knowledge Graph', icon: Network, code: 'D', moduleId: 'knowledge-graph' },
  { to: '/war-room', moduleId: 'war-room', label: 'Research War Room', icon: Swords, code: 'E' },
  { to: '/lab', moduleId: 'economic-lab', label: 'Economic Laboratory', icon: FlaskConical, code: 'F' },
  { to: '/studio', moduleId: 'research-studio', label: 'Research Studio', icon: BookOpenText, code: 'G' },
  { to: '/account', moduleId: 'business', label: 'NEXUS Business', icon: Briefcase, code: 'H' },
];

export const MAIN_NAV: NavItem[] = [
  { to: '/start', label: 'Inizia da qui', icon: Compass },
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/briefing', label: 'Daily Briefing', icon: Newspaper },
  { to: '/lessons', label: 'Guided Lessons', icon: GraduationCap },
];

export const ARCHIVE_NAV: NavItem[] = [
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/bibliography', label: 'Bibliography', icon: BookMarked },
  { to: '/research', label: 'Ask the Archive', icon: MessageSquareQuote },
];

export const WORKSPACE_NAV: NavItem[] = [
  { to: '/projects', label: 'Projects', icon: FolderKanban },
  { to: '/sources', label: 'Sources & Connectors', icon: Database },
  { to: '/activity', label: 'Activity Log', icon: Activity },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/settings', label: 'System', icon: Settings },
  { to: '/data-policy', label: 'Copyright & Data Policy', icon: Scale },
];

/** Percorso della pagina di un modulo (pagina reale se implementato, altrimenti scheda «in preparazione»). */
export function moduleRoute(id: string): string {
  return MODULE_NAV.find((n) => n.moduleId === id)?.to ?? `/modules/${id}`;
}
