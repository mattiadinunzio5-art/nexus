import { useState } from 'react';
import { FolderPlus, FolderCheck } from 'lucide-react';
import { api, type ProjectItemType } from '../api/client';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useScope } from '../state/Scope';
import { Button } from './ui/Button';

/** Collega (o scollega) un elemento al progetto attivo; funziona anche con gli elementi della Biblioteca. */
export function ProjectLinkButton({ type, id, onChange }: { type: ProjectItemType; id: number; onChange?: () => void }) {
  const { projectId, projectTitle } = useScope();
  const linked = useAsync(() => (projectId ? api.linkedProjects(type, id) : Promise.resolve([])), [projectId, type, id]);
  const [err, setErr] = useState<string>();
  if (!projectId) return null;
  const isIn = (linked.data ?? []).includes(projectId);
  return (
    <span className="inline-flex flex-col">
      <Button variant="ghost" className="text-xs" aria-pressed={isIn}
        title={isIn ? `Togli da «${projectTitle}»` : `Aggiungi a «${projectTitle}»`}
        onClick={async () => {
          setErr(undefined);
          try {
            if (isIn) await api.removeProjectItem(projectId, type, id); else await api.addProjectItem(projectId, type, id);
            await linked.reload(); onChange?.();
          } catch (e) { setErr(errorText(e)); }
        }}>
        {isIn ? <FolderCheck className="size-4 text-ok" aria-hidden /> : <FolderPlus className="size-4" aria-hidden />}
        {isIn ? 'Nel progetto' : 'Aggiungi al progetto'}
      </Button>
      {err && <span role="alert" className="text-[11px] text-bad">{err}</span>}
    </span>
  );
}

/** Dopo aver creato un elemento: se c'è un progetto attivo, lo collega subito (senza bloccare in caso di errore). */
export async function linkToActiveProject(projectId: number | null, type: ProjectItemType, id: number) {
  if (!projectId) return;
  try { await api.addProjectItem(projectId, type, id); } catch { /* il collegamento si può rifare a mano */ }
}
