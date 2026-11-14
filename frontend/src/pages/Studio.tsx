import { locale } from '../i18n';
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, FileDown, Plus, Quote, Trash2 } from 'lucide-react';
import { DownloadButton } from '../components/ui/DownloadButton';
import { api } from '../api/client';
import type { CitationStyle, Embed, Report, ReportCheck, ReportSection, ReportTemplate } from '../api/types';
import { VERIFICATION } from '../components/research';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field, Input, Select, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

export function StudioPage() {
  const reports = useAsync(() => api.reports(), []);
  const notes = useAsync(() => api.notes(), []);
  const runs = useAsync(() => api.runs(), []);
  const projects = useAsync(() => api.projects('active'), []);
  const [form, setForm] = useState({ title: '', author: '', project_id: '' });
  const [note, setNote] = useState({ title: '', body: '' });
  const [err, setErr] = useState<string>();
  const navigate = useNavigate();
  const approvedRuns = runs.data?.filter((r) => r.status === 'approved') ?? [];

  return (
    <>
      <PageHeader eyebrow="Modulo G" title="Research Studio" description="Rapporti professionali con citazioni verificabili, grafici, tabelle ed esportazione PDF/DOCX." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card title="Nuovo rapporto">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field label="Titolo" className="sm:col-span-3"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
              <Field label="Autore"><Input value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} /></Field>
              <Field label="Progetto"><Select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })}><option value="">—</option>{projects.data?.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}</Select></Field>
              <div className="flex items-end"><Button variant="primary" disabled={!form.title.trim()} onClick={async () => {
                setErr(undefined);
                try { const r = await api.createReport({ title: form.title.trim(), author: form.author.trim(), project_id: form.project_id ? Number(form.project_id) : null }); navigate(`/studio/reports/${r.id}`); } catch (e) { setErr(errorText(e)); }
              }}><Plus className="size-4" aria-hidden /> Crea</Button></div>
            </div>
            {approvedRuns.length > 0 && (
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <Field label="Oppure parti da una ricerca approvata" className="min-w-64 flex-1">
                  <Select id="from-run" defaultValue=""><option value="">Seleziona…</option>{approvedRuns.map((r) => <option key={r.id} value={r.id}>#{r.id} {r.question.slice(0, 90)}</option>)}</Select>
                </Field>
                <Button onClick={async () => {
                  const v = (document.getElementById('from-run') as HTMLSelectElement).value;
                  if (!v) return;
                  try { const r = await api.reportFromRun(Number(v)); navigate(`/studio/reports/${r.id}`); } catch (e) { setErr(errorText(e)); }
                }}>Genera bozza</Button>
              </div>
            )}
            {err && <p role="alert" className="mt-2 text-sm text-bad">{err}</p>}
          </Card>
          <Card title="Rapporti">
            {reports.loading && !reports.data && <Loading />}
            {reports.data?.length === 0 && <EmptyState>Nessun rapporto.</EmptyState>}
            <ul className="space-y-2">
              {reports.data?.map((r) => (
                <li key={r.id}><Link to={`/studio/reports/${r.id}`} className="flex flex-wrap items-center gap-2 rounded-md border border-ink-700 p-3 hover:border-gold-500/60">
                  <span className="min-w-0 flex-1 truncate text-paper">{r.title}</span>
                  <Badge tone={r.status === 'approved' ? 'ok' : 'warn'}>{r.status === 'approved' ? 'Approvato' : 'Bozza'}</Badge>
                  <span className="text-[11px] text-steel-500">{formatDateTime(r.updated_at)}</span>
                </Link></li>
              ))}
            </ul>
          </Card>
        </div>
        <Card title="Appunti">
          <div className="space-y-2">
            <Input aria-label="Titolo appunto" placeholder="Titolo" value={note.title} onChange={(e) => setNote({ ...note, title: e.target.value })} />
            <Textarea aria-label="Testo appunto" placeholder="Appunto…" value={note.body} onChange={(e) => setNote({ ...note, body: e.target.value })} />
            <Button disabled={!note.title.trim()} onClick={async () => { await api.createNote(note); setNote({ title: '', body: '' }); await notes.reload(); }}>Salva appunto</Button>
          </div>
          <ul className="mt-4 space-y-3">
            {notes.data?.map((n) => (
              <li key={n.id} className="border-l border-ink-600 pl-3 text-sm">
                <p className="font-medium text-paper">{n.title} <button className="ml-1 text-[11px] text-steel-500 hover:text-bad" onClick={async () => { await api.deleteNote(n.id); await notes.reload(); }} aria-label={`Elimina ${n.title}`}>elimina</button></p>
                <p className="whitespace-pre-line text-steel-300">{n.body}</p>
                <p className="text-[11px] text-steel-500">{formatDateTime(n.updated_at)}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}

const yearOrNull = (v: string) => (v.trim() === '' || Number.isNaN(Number(v)) ? null : Math.trunc(Number(v)));

function EmbedRow({ e, onChange, onRemove, label }: { e: Embed; onChange: (e: Embed) => void; onRemove: () => void; label: string }) {
  const kind = e.type === 'series' ? 'Grafico serie' : e.type === 'compare' ? 'Confronto' : e.type === 'simulation' ? 'Simulazione' : 'Tabella';
  return (
    <div className="space-y-1 rounded border border-ink-800 p-2 text-xs text-steel-300">
      <div className="flex items-center gap-2">
        <Badge>{kind}</Badge>
        <span className="min-w-0 flex-1 truncate">{label}</span>
        <button className="text-steel-500 hover:text-bad" onClick={onRemove} aria-label="Rimuovi">rimuovi</button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Input aria-label="Didascalia" className="min-w-48 flex-1 py-1 text-xs" placeholder="Didascalia (es. «Aiuti ERP per paese, 1948–1952»)" value={e.caption} onChange={(x) => onChange({ ...e, caption: x.target.value })} />
        {(e.type === 'series' || e.type === 'compare') && <>
          <Input aria-label="Dall'anno" className="!w-24 py-1 text-xs" inputMode="numeric" placeholder="dal" value={e.start_year ?? ''} onChange={(x) => onChange({ ...e, start_year: yearOrNull(x.target.value) })} />
          <Input aria-label="All'anno" className="!w-24 py-1 text-xs" inputMode="numeric" placeholder="al" value={e.end_year ?? ''} onChange={(x) => onChange({ ...e, end_year: yearOrNull(x.target.value) })} />
        </>}
        {e.type === 'compare' && <label className="flex items-center gap-1"><input type="checkbox" checked={!!e.rebase} onChange={(x) => onChange({ ...e, rebase: x.target.checked })} />Base 100</label>}
      </div>
      {e.type === 'table' && e.source_note && <p className="text-[11px] text-steel-500">{e.source_note}</p>}
    </div>
  );
}

function EmbedEditor({ embeds, onChange, projectId }: { embeds: Embed[]; onChange: (e: Embed[]) => void; projectId: number | null }) {
  const series = useAsync(() => api.seriesList(), []);
  const sims = useAsync(() => api.simulations(), []);
  const docs = useAsync(() => api.documents(), []);
  const [tableCsv, setTableCsv] = useState('');
  const [cmp, setCmp] = useState<{ ids: number[]; from: string; to: string; rebase: boolean }>({ ids: [], from: '', to: '', rebase: false });
  const [openCmp, setOpenCmp] = useState(false);
  const [err, setErr] = useState<string>();
  const tableDocs = (docs.data ?? []).filter((d) => d.kind === 'csv' || d.kind === 'xlsx')
    .sort((x, y) => Number(y.project_id === projectId) - Number(x.project_id === projectId));
  const name = (id: number) => series.data?.find((s) => s.id === id)?.name ?? `serie ${id}`;
  const label = (e: Embed) => e.type === 'series' ? name(e.series_id) : e.type === 'compare' ? e.series_ids.map(name).join(' · ')
    : e.type === 'simulation' ? sims.data?.find((s) => s.id === e.simulation_id)?.title ?? `simulazione ${e.simulation_id}` : `${e.columns.join(', ')} (${e.rows.length} righe)`;
  return (
    <div className="mt-2 space-y-2 rounded-md border border-ink-700 p-2">
      <p className="text-[11px] text-steel-500">Grafici e tabelle della sezione: nell'export sono numerati (Figura 1, Tabella 1) con didascalia e fonte.</p>
      {embeds.map((e, i) => <EmbedRow key={i} e={e} label={label(e)} onChange={(x) => onChange(embeds.map((y, j) => (j === i ? x : y)))} onRemove={() => onChange(embeds.filter((_, j) => j !== i))} />)}
      <div className="flex flex-wrap gap-2">
        <Select aria-label="Aggiungi grafico di una serie" className="!w-auto py-1 text-xs" value="" onChange={(e) => e.target.value && onChange([...embeds, { type: 'series', series_id: Number(e.target.value), caption: '' }])}>
          <option value="">+ grafico serie…</option>{series.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>
        <Button className="py-1 text-xs" onClick={() => setOpenCmp((v) => !v)}>+ confronto tra serie</Button>
        <Select aria-label="Aggiungi tabella da documento" className="!w-auto py-1 text-xs" value="" onChange={async (e) => {
          const id = Number(e.target.value); if (!id) return; setErr(undefined);
          try { const t = await api.documentTable(id); onChange([...embeds, { type: 'table', caption: t.caption, columns: t.columns, rows: t.rows, source_note: t.source_note, document_id: id }]); if (t.truncated) setErr('Tabella troncata a 12 colonne e 200 righe.'); }
          catch (x) { setErr(errorText(x)); }
        }}>
          <option value="">+ tabella da documento CSV/XLSX…</option>{tableDocs.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
        </Select>
        <Select aria-label="Aggiungi grafico di una simulazione" className="!w-auto py-1 text-xs" value="" onChange={(e) => e.target.value && onChange([...embeds, { type: 'simulation', simulation_id: Number(e.target.value), caption: '' }])}>
          <option value="">+ simulazione…</option>{sims.data?.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </Select>
      </div>
      {openCmp && (
        <div className="space-y-2 rounded border border-ink-800 p-2 text-xs" data-testid="compare-form">
          <p className="text-steel-400">Scegli da 1 a 8 serie: compariranno nello stesso grafico, sul periodo indicato.</p>
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
            {series.data?.map((s) => (
              <label key={s.id} className="flex items-center gap-1.5 text-steel-300">
                <input type="checkbox" checked={cmp.ids.includes(s.id)} disabled={!cmp.ids.includes(s.id) && cmp.ids.length >= 8}
                  onChange={() => setCmp({ ...cmp, ids: cmp.ids.includes(s.id) ? cmp.ids.filter((x) => x !== s.id) : [...cmp.ids, s.id] })} />
                <span className="truncate">{s.name}</span>
              </label>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Input aria-label="Confronto dall'anno" className="!w-24 py-1 text-xs" inputMode="numeric" placeholder="dal" value={cmp.from} onChange={(e) => setCmp({ ...cmp, from: e.target.value })} />
            <Input aria-label="Confronto all'anno" className="!w-24 py-1 text-xs" inputMode="numeric" placeholder="al" value={cmp.to} onChange={(e) => setCmp({ ...cmp, to: e.target.value })} />
            <label className="flex items-center gap-1 text-steel-300"><input type="checkbox" checked={cmp.rebase} onChange={(e) => setCmp({ ...cmp, rebase: e.target.checked })} />Ribasa a 100 sul primo anno comune</label>
            <Button className="py-1 text-xs" variant="primary" disabled={cmp.ids.length === 0} onClick={() => {
              onChange([...embeds, { type: 'compare', series_ids: cmp.ids, caption: '', start_year: yearOrNull(cmp.from), end_year: yearOrNull(cmp.to), rebase: cmp.rebase }]);
              setCmp({ ids: [], from: '', to: '', rebase: false }); setOpenCmp(false);
            }}>Aggiungi confronto</Button>
          </div>
        </div>
      )}
      {err && <p className="text-xs text-warn">{err}</p>}
      <details className="text-xs text-steel-400">
        <summary className="cursor-pointer">Tabella scritta a mano</summary>
        <Textarea aria-label="Tabella CSV" className="mt-1 text-xs" placeholder={'Tabella CSV (prima riga intestazione, separatore ;)\nAnno;Valore\n2020;155'} value={tableCsv} onChange={(e) => setTableCsv(e.target.value)} />
        <Button className="mt-1 text-xs" disabled={!tableCsv.trim()} onClick={() => {
          const lines = tableCsv.trim().split('\n').map((l) => l.split(';').map((c) => c.trim()));
          onChange([...embeds, { type: 'table', caption: '', columns: lines[0], rows: lines.slice(1) }]);
          setTableCsv('');
        }}>+ tabella</Button>
      </details>
    </div>
  );
}

function CiteInserter({ onInsert }: { onInsert: (code: string) => void }) {
  const sources = useAsync(() => api.sources(), []);
  const [src, setSrc] = useState('');
  const [loc, setLoc] = useState('');
  return (
    <div className="flex flex-wrap items-center gap-1.5" data-testid="cite-inserter">
      <Select aria-label="Fonte da citare" className="!w-auto max-w-72 py-1 text-xs" value={src} onChange={(e) => setSrc(e.target.value)}>
        <option value="">Cita una fonte…</option>
        {sources.data?.map((s) => <option key={s.id} value={s.id}>{s.citation.slice(0, 90)}</option>)}
      </Select>
      <Input aria-label="Pagina" className="!w-24 py-1 text-xs" placeholder="p. 12" value={loc} onChange={(e) => setLoc(e.target.value)} />
      <Button className="py-1 text-xs" disabled={!src} onClick={() => { onInsert(`[@${src}${loc.trim() ? `, ${loc.trim()}` : ''}]`); setLoc(''); }}><Quote className="size-3" aria-hidden /> Inserisci</Button>
    </div>
  );
}

function SectionEditor({ report, section, onSaved, onError }: { report: Report; section: ReportSection; onSaved: (r: Report) => void; onError: (e: string) => void }) {
  const [body, setBody] = useState(section.body);
  const [title, setTitle] = useState(section.title);
  const [embeds, setEmbeds] = useState<Embed[]>(section.embeds);
  const [showEmbeds, setShowEmbeds] = useState(section.embeds.length > 0);
  const [cite, setCite] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  const caret = useRef<number | null>(null);
  const dirty = body !== section.body || title !== section.title || JSON.stringify(embeds) !== JSON.stringify(section.embeds);
  useEffect(() => { setBody(section.body); setTitle(section.title); setEmbeds(section.embeds); }, [section]);
  const chapter = section.key === 'chapter';
  const words = body.trim() ? body.trim().split(/\s+/).length : 0;
  const cites = (body.match(/\[@\d+/g) ?? []).length;
  const insert = (code: string) => {
    const pos = caret.current ?? body.length;
    const before = body.slice(0, pos).replace(/\s+$/, ''); const after = body.slice(pos);
    setBody(`${before} ${code}${after}`);
    caret.current = before.length + code.length + 1;
  };
  return (
    <section className="rounded-lg border border-ink-700 bg-ink-900 p-4" data-testid={`section-${section.key}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {chapter ? <Input aria-label="Titolo capitolo" className="max-w-md py-1" value={title} onChange={(e) => setTitle(e.target.value)} /> : <h2 className="font-medium text-paper">{section.title}</h2>}
        {chapter && <Badge>Capitolo</Badge>}
        {!section.body.trim() && !chapter && <Badge tone="warn">Da compilare</Badge>}
        <span className="text-[11px] text-steel-500">{`${words} parole · ${cites} citazioni`}</span>
        <span className="flex-1" />
        {chapter && <>
          <Button variant="ghost" className="px-1.5" aria-label="Sposta su" onClick={async () => onSaved(await api.moveChapter(report.id, section.id, -1))}><ArrowUp className="size-4" /></Button>
          <Button variant="ghost" className="px-1.5" aria-label="Sposta giù" onClick={async () => onSaved(await api.moveChapter(report.id, section.id, 1))}><ArrowDown className="size-4" /></Button>
          <Button variant="ghost" className="px-1.5 hover:text-bad" aria-label="Elimina capitolo" onClick={async () => onSaved(await api.deleteChapter(report.id, section.id))}><Trash2 className="size-4" /></Button>
        </>}
      </div>
      <Textarea ref={ref} onSelect={(e) => { caret.current = e.currentTarget.selectionStart; }} aria-label={`Testo: ${section.title}`} className="min-h-32" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Paragrafi separati da una riga vuota; elenchi con «- ». Citazioni: [@id, p. 12]" />
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <button className="text-xs text-gold-300 hover:underline" onClick={() => setShowEmbeds((v) => !v)}>{showEmbeds ? 'Nascondi grafici e tabelle' : `Grafici e tabelle (${embeds.length})`}</button>
        <button className="text-xs text-gold-300 hover:underline" onClick={() => setCite((v) => !v)}>{cite ? 'Chiudi citazione' : 'Inserisci citazione'}</button>
        <span className="flex-1" />
        {dirty && <Button variant="primary" className="text-xs" onClick={async () => {
          try { onSaved(await api.updateSection(report.id, section.id, { body, embeds, ...(chapter ? { title } : {}) })); } catch (e) { onError(errorText(e)); }
        }}>Salva sezione</Button>}
      </div>
      {cite && <div className="mt-2"><CiteInserter onInsert={insert} /></div>}
      {showEmbeds && <EmbedEditor embeds={embeds} onChange={setEmbeds} projectId={report.project_id} />}
    </section>
  );
}

function Checklist({ check }: { check?: ReportCheck }) {
  if (!check) return <Loading />;
  const done = check.checklist.filter((c) => c.ok).length;
  return (
    <Card title={`Prima della consegna · ${done}/${check.checklist.length}`} className="mb-4">
      <ul className="grid grid-cols-1 gap-x-6 gap-y-1.5 text-sm md:grid-cols-2" data-testid="checklist">
        {check.checklist.map((c) => (
          <li key={c.key} className="flex items-start gap-2">
            {c.ok ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-ok" aria-label="ok" /> : <AlertTriangle className={`mt-0.5 size-4 shrink-0 ${c.blocking ? 'text-bad' : 'text-warn'}`} aria-label="da sistemare" />}
            <span><span className={c.ok ? 'text-steel-300' : 'text-paper'}>{c.label}</span>{c.detail && <span className="block text-[11px] text-steel-500">{c.detail}</span>}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[11px] text-steel-500">In rosso i punti che impediscono l'approvazione; in giallo quelli consigliati per un lavoro accademico.</p>
    </Card>
  );
}

function CheckPanel({ check }: { check?: ReportCheck }) {
  if (!check) return <Loading />;
  return (
    <div className="space-y-2 text-steel-300">
      <p className={`flex items-center gap-1.5 ${check.ready ? 'text-ok' : 'text-warn'}`}>{check.ready ? <CheckCircle2 className="size-4" /> : <AlertTriangle className="size-4" />}{check.ready ? 'Pronto per l\'approvazione' : 'Non ancora approvabile'}</p>
      <p>Bibliografia: {check.bibliography_size} fonti ({check.cited_sources} citate nel testo)</p>
      {check.unverified_sources.length > 0 && <div><p className="text-warn">Fonti non verificate (segnalate nell'export):</p><ul className="list-disc pl-5 text-xs">{check.unverified_sources.map((s) => <li key={s.id}>{s.citation}</li>)}</ul></div>}
      {check.warnings.map((w) => <p key={w} className="text-xs text-warn">{w}</p>)}
    </div>
  );
}

const STYLE_HELP: Record<CitationStyle, string> = {
  numeric: 'Numeri tra parentesi [1, p. 5], bibliografia numerata.',
  footnotes: 'Note a piè di pagina (uso delle tesi di storia): citazione completa la prima volta, poi forma breve e «Ivi».',
  author_date: 'Autore e anno nel testo (Tarnoff 2018, p. 5), bibliografia in ordine alfabetico.',
};

function LayoutSettings({ r, onSaved }: { r: Report; onSaved: (r: Report) => void }) {
  return (
    <Card className="mb-4">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Modello" className="min-w-48"><Select value={r.template} onChange={async (e) => onSaved(await api.updateReport(r.id, { template: e.target.value as ReportTemplate }))}>
          <option value="standard">Rapporto</option>
          <option value="thesis">Tesi / tesina</option>
        </Select></Field>
        <Field label="Stile delle citazioni" className="min-w-56"><Select value={r.citation_style} onChange={async (e) => onSaved(await api.updateReport(r.id, { citation_style: e.target.value as CitationStyle }))}>
          <option value="footnotes">Note a piè di pagina</option>
          <option value="author_date">Autore-data</option>
          <option value="numeric">Numerico [1]</option>
        </Select></Field>
        <p className="min-w-60 flex-1 text-xs text-steel-500">
          {STYLE_HELP[r.citation_style]} {r.template === 'thesis' ? 'Il modello tesi aggiunge frontespizio, indice, capitoli numerati, elenco di figure e tabelle e due appendici: cronologia degli eventi collegati alle fonti e nota sulle fonti.' : ''}
          {r.citation_style === 'footnotes' ? ' Nel PDF le note sono in fondo a ogni capitolo; in Word e LaTeX a piè di pagina.' : ''}
        </p>
      </div>
    </Card>
  );
}

export function ReportEditorPage() {
  const id = Number(useParams().reportId);
  const rep = useAsync(() => api.report(id), [id]);
  const check = useAsync(() => api.checkReport(id), [id, rep.data?.updated_at]);
  const sources = useAsync(() => api.sources(), []);
  const [err, setErr] = useState<string>();
  const [chapter, setChapter] = useState('');
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();
  useContextPanel(
    <div className="space-y-4">
      <div><h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Verifica</h3><CheckPanel check={check.data} /></div>
      <div>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Fonti da citare</h3>
        <p className="mb-2 text-xs text-steel-500">Copia il codice nel testo: <span className="font-mono">[@id]</span> o <span className="font-mono">[@id, p. 12]</span>.</p>
        <ul className="space-y-1.5 text-xs">
          {sources.data?.map((s) => (
            <li key={s.id} className="flex items-start gap-2">
              <button className="shrink-0 font-mono text-gold-300 hover:underline" onClick={() => navigator.clipboard?.writeText(`[@${s.id}]`)} title="Copia codice"><Quote className="inline size-3" /> @{s.id}</button>
              <span className="text-steel-300">{s.citation.slice(0, 120)} <Badge tone={VERIFICATION[s.verification_status].tone}>{VERIFICATION[s.verification_status].label}</Badge></span>
            </li>
          ))}
          {sources.data?.length === 0 && <li className="text-steel-500">Nessuna fonte: aggiungile in <Link to="/bibliography" className="text-gold-300">Bibliography</Link>.</li>}
        </ul>
      </div>
    </div>,
    [check.data, sources.data],
  );
  if (rep.loading && !rep.data) return <Loading />;
  if (rep.error) return <ErrorBox error={rep.error} onRetry={rep.reload} />;
  const r = rep.data!;
  const saved = (x: Report) => { setErr(undefined); rep.setData(x); };
  return (
    <>
      <PageHeader eyebrow={<Link to="/studio" className="hover:underline">Research Studio</Link>} title={r.title}
        description={`${r.status === 'approved' ? 'Approvato' : 'Bozza'} · aggiornato ${formatDateTime(r.updated_at)}${r.origin.startsWith('research_run') ? ' · da ricerca della War Room' : ''}`}
        actions={<>
          <DownloadButton path={api.exportPath(r.id, 'pdf')} className="inline-flex items-center gap-1 rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800"><FileDown className="size-4" aria-hidden /> PDF</DownloadButton>
          <DownloadButton path={api.exportPath(r.id, 'docx')} className="inline-flex items-center gap-1 rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800"><FileDown className="size-4" aria-hidden /> DOCX</DownloadButton>
          <DownloadButton path={api.exportPath(r.id, 'latex')} title="ZIP con main.tex, references.bib e figure (compilabile su Overleaf)" className="inline-flex items-center gap-1 rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800"><FileDown className="size-4" aria-hidden /> LaTeX</DownloadButton>
          {r.status === 'draft'
            ? <Button variant="primary" onClick={async () => { try { saved(await api.setReportStatus(r.id, 'approved')); } catch (e) { setErr(errorText(e)); } }}>Approva</Button>
            : <Button onClick={async () => saved(await api.setReportStatus(r.id, 'draft'))}>Riporta in bozza</Button>}
          <Button onClick={() => setDeleting(true)} aria-label="Elimina rapporto"><Trash2 className="size-4" /></Button>
        </>} />
      <LayoutSettings r={r} onSaved={saved} />
      <Checklist check={check.data} />
      {r.contains_ai_text && <p className="mb-3 text-sm text-warn">Contiene testo generato o estratto automaticamente: rivedilo prima di approvare.</p>}
      {err && <div className="mb-3"><ErrorBox error={new Error(err)} /></div>}
      <div className="space-y-3">
        {[...r.sections].sort((a, b) => a.ordinal - b.ordinal).map((s) => <SectionEditor key={s.id} report={r} section={s} onSaved={saved} onError={setErr} />)}
      </div>
      <Card className="mt-4">
        <div className="flex flex-wrap items-end gap-2">
          <Field label="Nuovo capitolo (inserito dopo «Analisi»)" className="min-w-64 flex-1"><Input value={chapter} onChange={(e) => setChapter(e.target.value)} /></Field>
          <Button disabled={!chapter.trim()} onClick={async () => { saved(await api.addChapter(r.id, chapter.trim(), 'analysis')); setChapter(''); }}><Plus className="size-4" aria-hidden /> Aggiungi capitolo</Button>
        </div>
        <p className="mt-2 text-xs text-steel-500">La bibliografia è generata automaticamente dalle fonti citate, con lo stato di verifica di ciascuna.</p>
      </Card>
      <ConfirmDialog open={deleting} title="Eliminare il rapporto?" message="Il rapporto e tutte le sue sezioni verranno eliminati." confirmLabel="Elimina definitivamente"
        onCancel={() => setDeleting(false)} onConfirm={async () => { await api.deleteReport(r.id); navigate('/studio'); }} />
    </>
  );
}

export function BriefingPage() {
  const list = useAsync(() => api.briefings(), []);
  const [selected, setSelected] = useState<number>();
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(false);
  const [err, setErr] = useState<string>();
  const b = list.data?.find((x) => x.id === selected) ?? list.data?.[0];
  return (
    <>
      <PageHeader eyebrow="Research Studio" title="Daily Briefing" description="Rapporto periodico sui tuoi dati: ogni voce con data e fonte. Nessuna notizia in tempo reale."
        actions={<>
          <label className="flex items-center gap-1.5 text-sm text-steel-300"><input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} />Aggiorna prima le serie</label>
          <Button variant="primary" disabled={busy} onClick={async () => { setBusy(true); setErr(undefined); try { const n = await api.generateBriefing(refresh); await list.reload(); setSelected(n.id); } catch (e) { setErr(errorText(e)); } finally { setBusy(false); } }}>{busy ? 'Generazione…' : 'Genera ora'}</Button>
        </>} />
      <p className="mb-4 text-xs text-steel-500">Programmazione: <span className="font-mono">scripts/generate_briefing.py --refresh</span> con cron (vedi documentazione).</p>
      {err && <ErrorBox error={new Error(err)} />}
      {list.loading && !list.data && <Loading />}
      {list.data?.length === 0 && <EmptyState>Nessun briefing generato.</EmptyState>}
      {list.data && list.data.length > 1 && (
        <Select aria-label="Briefing" className="mb-4 max-w-xs" value={b?.id} onChange={(e) => setSelected(Number(e.target.value))}>
          {list.data.map((x) => <option key={x.id} value={x.id}>{x.content.date} · {x.trigger === 'scheduled' ? 'programmato' : 'manuale'} · #{x.id}</option>)}
        </Select>
      )}
      {b && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2" data-testid="briefing">
          {b.content.sections.map((s, i) => (
            <Card key={s.key} title={`${i + 1}. ${s.title}`}>
              {s.items.length === 0 ? <p className="text-sm text-steel-400">{s.empty_reason}</p> : (
                <ul className="space-y-2 text-sm">
                  {s.items.map((it, j) => (
                    <li key={j}>
                      <p className="text-paper">{it.url ? <Link to={it.url} className="hover:text-gold-300">{it.title}</Link> : it.title}
                        {it.value !== undefined && it.value !== null && <span className="ml-2 text-gold-300">{it.value.toLocaleString(locale(), { maximumSignificantDigits: 6 })} {it.unit}</span>}</p>
                      {it.detail && <p className="text-steel-300">{it.detail}</p>}
                      <p className="text-[11px] text-steel-500">{[it.date && `Data: ${it.date}`, it.source && `Fonte: ${it.source}`, it.kind, it.reason].filter(Boolean).join(' · ')}</p>
                      {it.flags?.map((f) => <p key={f} className="text-[11px] text-warn">{f}</p>)}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>
      )}
      {b?.content.refresh && b.content.refresh.length > 0 && <Card title="Aggiornamento delle fonti" className="mt-4"><ul className="text-xs text-steel-300">{b.content.refresh.map((x) => <li key={x.series}>{x.series}: {x.status}</li>)}</ul></Card>}
    </>
  );
}
