import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import type { ScopeParams } from '../api/client';

/** Ambito delle schermate: solo il progetto attivo, solo i miei dati, solo la Biblioteca, oppure tutto. */
export type ScopeMode = 'project' | 'mine' | 'library' | 'all';
const KEY = 'nexus.scope';

interface ScopeState {
  projectId: number | null;
  projectTitle: string;
  mode: ScopeMode;
  setProject: (id: number | null, title?: string) => void;
  setMode: (m: ScopeMode) => void;
  /** Parametri da passare agli elenchi del backend. */
  params: ScopeParams;
}

function load(): { projectId: number | null; projectTitle: string; mode: ScopeMode } {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? 'null');
    if (v && typeof v === 'object') return { projectId: v.projectId ?? null, projectTitle: v.projectTitle ?? '', mode: v.mode ?? 'all' };
  } catch { /* storage non disponibile */ }
  return { projectId: null, projectTitle: '', mode: 'all' };
}

const Ctx = createContext<ScopeState | null>(null);

export function ScopeProvider({ children }: { children: ReactNode }) {
  const [st, setSt] = useState(load);
  const save = useCallback((next: typeof st) => {
    setSt(next);
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* ignora */ }
  }, []);
  const value = useMemo<ScopeState>(() => {
    const mode: ScopeMode = st.mode === 'project' && !st.projectId ? 'all' : st.mode;
    const params: ScopeParams = mode === 'project' && st.projectId ? { project_id: st.projectId }
      : mode === 'mine' ? { origin: 'mine' } : mode === 'library' ? { origin: 'library' } : {};
    return {
      ...st, mode, params,
      // Scegliendo un progetto si lavora «solo progetto» per impostazione predefinita.
      setProject: (id, title = '') => save({ projectId: id, projectTitle: title, mode: id ? 'project' : (st.mode === 'project' ? 'all' : st.mode) }),
      setMode: (m) => save({ ...st, mode: m }),
    };
  }, [st, save]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

const FALLBACK: ScopeState = { projectId: null, projectTitle: '', mode: 'all', setProject: () => {}, setMode: () => {}, params: {} };

export function useScope(): ScopeState {
  return useContext(Ctx) ?? FALLBACK;
}

/** Chiave stabile per ricaricare gli elenchi quando cambia l'ambito. */
export function scopeKey(p: ScopeParams): string {
  return `${p.project_id ?? ''}|${p.origin ?? ''}`;
}
