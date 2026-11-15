import { api } from '../../api/client';
import { useAsync } from '../../lib/useAsync';
import { useScope, type ScopeMode } from '../../state/Scope';

const MODES: [ScopeMode, string][] = [['project', 'Solo progetto'], ['mine', 'Le mie'], ['library', 'Solo Biblioteca'], ['all', 'Tutti']];

/** Ambito globale: progetto attivo e cosa mostrare negli elenchi (Documenti, Bibliografia, Financial, Storia, Grafo, Time Machine). */
export function ScopeBar() {
  const { projectId, projectTitle, mode, setProject, setMode } = useScope();
  // Si ricarica quando cambia il progetto attivo: un progetto appena creato e attivato compare subito.
  const projects = useAsync(() => api.projects('active'), [projectId]);
  const list = (projects.data ?? []).filter((p) => !p.library);
  const missing = projectId && !list.some((p) => p.id === projectId);
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-ink-800 bg-ink-950/60 px-4 py-1.5 text-xs" data-testid="scope-bar">
      <label className="flex items-center gap-1.5 text-steel-400">
        Progetto
        <select aria-label="Progetto attivo" className="rounded border border-ink-700 bg-ink-900 px-1.5 py-0.5 text-paper"
          value={projectId ?? ''} onChange={(e) => {
            const id = e.target.value ? Number(e.target.value) : null;
            setProject(id, list.find((p) => p.id === id)?.title ?? '');
          }}>
          <option value="">Nessuno</option>
          {missing && <option value={projectId}>{projectTitle || `Progetto #${projectId}`}</option>}
          {list.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
        </select>
      </label>
      <div className="flex gap-0.5" role="radiogroup" aria-label="Ambito degli elenchi">
        {MODES.map(([m, l]) => (
          <button key={m} type="button" role="radio" aria-checked={mode === m} disabled={m === 'project' && !projectId}
            title={m === 'project' && !projectId ? 'Scegli prima un progetto' : undefined}
            onClick={() => setMode(m)}
            className={`rounded px-2 py-0.5 disabled:opacity-40 ${mode === m ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:text-paper'}`}>{l}</button>
        ))}
      </div>
    </div>
  );
}
