import { NavLink } from 'react-router-dom';

/** Historical Intelligence e Time Machine sono un unico modulo: due schede sugli stessi eventi. */
export function HistoryTabs() {
  const cls = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:text-paper'}`;
  return (
    <nav aria-label="Schede di Historical Intelligence" className="mb-4 flex gap-1 border-b border-ink-700 pb-2">
      <NavLink to="/history" end className={cls}>Eventi</NavLink>
      <NavLink to="/time-machine" className={cls}>Time Machine</NavLink>
    </nav>
  );
}
