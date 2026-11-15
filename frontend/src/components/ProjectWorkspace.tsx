import { useState } from 'react';
import { CheckCircle2, Circle, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api, type ProjectItemType } from '../api/client';
import { RELATION_TYPES } from '../api/types';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Field, Select } from './ui/Form';
import { SearchPicker } from './ui/SearchPicker';
import { ErrorBox, Loading } from './ui/States';

const TYPES: [ProjectItemType, string, (id: number) => string][] = [
  ['document', 'Documenti', (id) => `/documents/${id}`], ['source', 'Fonti', () => '/bibliography'],
  ['event', 'Eventi', (id) => `/history/events/${id}`], ['entity', 'Entità', (id) => `/graph?focus=${id}`],
  ['series', 'Serie', (id) => `/financial/series/${id}`], ['relation', 'Relazioni', () => '/graph'],
];

/** Centro operativo del progetto: stato della ricerca, elementi collegati, nuove relazioni. */
export function ProjectWorkspace({ projectId, canEdit }: { projectId: number; canEdit: boolean }) {
  const ov = useAsync(() => api.projectOverview(projectId), [projectId]);
  const [tab, setTab] = useState<ProjectItemType>('document');
  const items = useAsync(() => api.projectItems(projectId, tab), [projectId, tab]);
  const [rel, setRel] = useState({ a: '', b: '', type: 'influenced' });
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const reload = async () => { await Promise.all([ov.reload(), items.reload()]); };
  if (ov.loading && !ov.data) return <Loading />;
  if (ov.error) return <ErrorBox error={ov.error} onRetry={ov.reload} />;
  const o = ov.data!;
  return (
    <div className="space-y-4 rounded-md border border-ink-700 bg-ink-950/60 p-3" data-testid="project-workspace">
      <div>
        <div className="mb-2 flex items-center gap-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Stato della ricerca</h3>
          <div className="h-1.5 w-32 overflow-hidden rounded bg-ink-800" aria-hidden><div className="h-full bg-gold-500" style={{ width: `${Math.round(o.progress * 100)}%` }} /></div>
          <span className="text-xs text-steel-400">{Math.round(o.progress * 100)}%</span>
        </div>
        <ul className="grid grid-cols-1 gap-1 text-sm sm:grid-cols-2">
          {o.checks.map((c) => (
            <li key={c.key} className="flex items-start gap-1.5">
              {c.ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-ok" aria-label="Fatto" /> : <Circle className="mt-0.5 size-4 shrink-0 text-steel-600" aria-label="Da fare" />}
              <span className={c.ok ? 'text-steel-300' : 'text-paper'}>{c.label}{c.detail && <span className="text-[11px] text-steel-500"> · {c.detail}</span>}</span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[11px] text-steel-500">
          {o.from_library > 0 && `${o.from_library} elementi dalla Biblioteca · `}{o.research_runs} ricerche nella War Room
          {o.reports.length > 0 && <> · Rapporti: {o.reports.map((r) => <Link key={r.id} to={`/studio/reports/${r.id}`} className="ml-1 text-gold-300 hover:underline">{r.title}</Link>)}</>}
        </p>
      </div>
      <div>
        <div className="mb-2 flex flex-wrap gap-1" role="tablist" aria-label="Elementi del progetto">
          {TYPES.map(([t, l]) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              className={`rounded px-2 py-1 text-xs ${tab === t ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:text-paper'}`}>{l} ({o.counts[t] ?? 0})</button>
          ))}
        </div>
        {items.loading && !items.data ? <Loading /> : (
          <ul className="max-h-64 space-y-1 overflow-auto text-sm">
            {items.data?.length === 0 && <li className="text-xs text-steel-500">Nessun elemento: aprilo nel suo modulo e usa «Aggiungi al progetto» (con questo progetto attivo nella barra in alto).</li>}
            {items.data?.map((it) => (
              <li key={it.id} className="flex items-center gap-2">
                <Link to={TYPES.find((x) => x[0] === tab)![2](it.id)} className="min-w-0 flex-1 truncate text-steel-300 hover:text-paper">{it.label}</Link>
                {it.library && <Badge>Biblioteca</Badge>}
                {canEdit && <button className="text-steel-500 hover:text-bad" aria-label={`Scollega ${it.label}`}
                  onClick={async () => { await api.removeProjectItem(projectId, tab, it.id); await reload(); }}><Trash2 className="size-3.5" /></button>}
              </li>
            ))}
          </ul>
        )}
      </div>
      {canEdit && (
        <div>
          <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Nuova relazione nel progetto</h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_12rem_1fr_auto] sm:items-end">
            <Field label="Da"><SearchPicker kind="entity" ariaLabel="Relazione: da" value={rel.a} onChange={(v) => setRel({ ...rel, a: v })} /></Field>
            <Field label="Relazione"><Select value={rel.type} onChange={(e) => setRel({ ...rel, type: e.target.value })}>{Object.entries(RELATION_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
            <Field label="A"><SearchPicker kind="entity" ariaLabel="Relazione: a" value={rel.b} onChange={(v) => setRel({ ...rel, b: v })} /></Field>
            <Button disabled={!rel.a || !rel.b} onClick={async () => {
              setMsg(undefined);
              try {
                const r = await api.createRelation({ source_entity_id: Number(rel.a), target_entity_id: Number(rel.b), relation_type: rel.type, provenance: 'user_hypothesis', evidence_note: 'Ipotesi creata dal progetto' });
                await api.addProjectItem(projectId, 'relation', r.id);
                setRel({ a: '', b: '', type: rel.type }); setMsg({ ok: true, text: 'Relazione creata come ipotesi e collegata al progetto. Aggiungi una fonte dal Knowledge Graph per documentarla.' });
                await reload();
              } catch (e) { setMsg({ ok: false, text: errorText(e) }); }
            }}>Crea</Button>
          </div>
          {msg && <p role={msg.ok ? 'status' : 'alert'} className={`mt-1 text-xs ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
        </div>
      )}
    </div>
  );
}
