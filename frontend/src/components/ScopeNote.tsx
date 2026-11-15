import { useScope } from '../state/Scope';

/** Ricorda quale ambito è attivo sopra un elenco (si cambia dalla barra in alto). */
export function ScopeNote() {
  const { mode, projectTitle } = useScope();
  const text = mode === 'project' ? `Solo il progetto «${projectTitle}»` : mode === 'mine' ? 'Solo i tuoi dati' : mode === 'library' ? 'Solo la Biblioteca NEXUS' : 'Tuoi dati e Biblioteca (i tuoi prima)';
  return <span className="text-[11px] text-steel-500" data-testid="scope-note">Ambito: {text} · si cambia dalla barra in alto</span>;
}
