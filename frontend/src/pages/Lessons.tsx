import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowRight, Download, ExternalLink, GraduationCap, Play } from 'lucide-react';
import { api } from '../api/client';
import type { LessonTable } from '../api/types';
import { LicenseBox } from '../components/License';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

const panel = (
  <div className="space-y-2 text-steel-300">
    <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Guided Lessons</h3>
    <p>Percorsi pronti per studenti e docenti. Ogni lezione crea un progetto con una guida passo passo.</p>
    <p>I dati si scaricano dalle fonti ufficiali quando li importi. Le letture consigliate entrano in bibliografia come <strong className="text-paper">non verificate</strong>.</p>
  </div>
);

export function LessonsPage() {
  const list = useAsync(() => api.lessons(), []);
  useContextPanel(panel, []);
  return (
    <>
      <PageHeader eyebrow="Guided Lessons" title="Guided Lessons" description="Percorsi di ricerca su grandi episodi della storia economica, con dati reali e fonti da verificare." />
      {list.loading && <Loading />}
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {list.data?.map((l) => (
          <li key={l.id}>
            <Link to={`/lessons/${l.id}`} className="block h-full rounded-lg border border-ink-700 bg-ink-900 p-4 transition hover:border-gold-500">
              <GraduationCap className="mb-3 size-5 text-gold-300" aria-hidden />
              <h2 className="font-medium text-paper">{l.title}</h2>
              <p className="mt-1 text-sm text-steel-400">{l.summary}</p>
              <p className="mt-3 flex flex-wrap gap-2"><Badge>{l.level}</Badge><Badge>{l.duration}</Badge></p>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

function csvOf(t: LessonTable): string {
  const q = (v: string) => (/[",;\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const lines = [t.columns, ...t.rows].map((r) => r.map(q).join(';'));
  return [...lines, '', `Fonte;${q(t.source)}`, `URL;${t.source_url}`].join('\n');
}

/** Tabella di dati di una lezione: con fonte, licenza e CSV scaricabile (separatore ; per Excel in italiano). */
function DataTableCard({ t }: { t: LessonTable }) {
  const href = `data:text/csv;charset=utf-8,${encodeURIComponent('\ufeff' + csvOf(t))}`;
  const file = t.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) + '.csv';
  return (
    <Card title={t.title} className="lg:col-span-2">
      {t.unit && <p className="mb-2 text-xs text-steel-500">Unità: {t.unit}</p>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[28rem] text-sm">
          <thead><tr className="border-b border-ink-700 text-left text-xs text-steel-500">{t.columns.map((c) => <th key={c} className="px-2 py-1.5 font-medium">{c}</th>)}</tr></thead>
          <tbody>
            {t.rows.map((r) => (
              <tr key={r.join('|')} className="border-b border-ink-800 last:border-0">
                {r.map((v, i) => <td key={i} className={`px-2 py-1.5 ${i === 0 ? 'text-paper' : 'text-steel-300'} ${i > 0 && /^[\d.,]+$/.test(v) ? 'text-right font-mono' : ''}`}>{v}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-steel-400">Fonte: {t.source_url ? <a href={t.source_url} target="_blank" rel="noreferrer noopener" className="text-gold-300 hover:underline">{t.source}</a> : t.source}</p>
      {t.notes && <p className="mt-1 text-xs text-steel-500">{t.notes}</p>}
      <a href={href} download={file} className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-ink-700 px-3 py-1.5 text-sm text-paper hover:border-gold-500"><Download className="size-4" aria-hidden /> Scarica CSV</a>
      <LicenseBox ids={[t.license_id]} />
    </Card>
  );
}

/** Video guidati delle lezioni (file statici in public/lessons). */
const LESSON_VIDEOS: Record<string, { src: string; poster: string }> = {
  'crisi-1929': { src: '/lessons/crisi-1929.mp4', poster: '/lessons/crisi-1929.jpg' },
};

export function LessonDetailPage() {
  const { lessonId = '' } = useParams();
  const l = useAsync(() => api.lesson(lessonId), [lessonId]);
  const [started, setStarted] = useState<{ project_id: number; sources_added: number }>();
  const [status, setStatus] = useState<Record<number, { ok: boolean; text: string }>>({});
  const [busy, setBusy] = useState<number | 'start'>();
  const [err, setErr] = useState<string>();
  useContextPanel(panel, []);

  if (l.loading) return <Loading />;
  if (l.error) return <ErrorBox error={l.error} onRetry={l.reload} />;
  const d = l.data!;

  async function importSeries(i: number) {
    setBusy(i);
    try {
      const s = d.series[i];
      const out = await api.importSeries({ category: s.category, ...s.params });
      setStatus((x) => ({ ...x, [i]: { ok: true, text: `Importata: ${out.observation_count} osservazioni.` } }));
    } catch (e) {
      setStatus((x) => ({ ...x, [i]: { ok: false, text: errorText(e) } }));
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <>
      <PageHeader eyebrow={<Link to="/lessons" className="hover:underline">Guided Lessons</Link>} title={d.title} description={`${d.level} · ${d.duration}`}
        actions={!started && <Button variant="primary" disabled={busy === 'start'} onClick={async () => {
          setBusy('start');
          setErr(undefined);
          try { setStarted(await api.startLesson(d.id)); } catch (e) { setErr(errorText(e)); } finally { setBusy(undefined); }
        }}><Play className="size-4" aria-hidden /> Inizia la lezione</Button>} />
      <p className="mb-4 max-w-3xl text-steel-300">{d.summary}</p>
      {err && <p role="alert" className="mb-4 text-sm text-bad">{err}</p>}
      {started && (
        <p role="status" className="mb-4 rounded-md border border-ok/40 bg-ok/10 p-3 text-sm text-ok">
          Lezione iniziata: creato il progetto con la guida{started.sources_added ? ` e ${started.sources_added} letture da verificare in bibliografia` : ''}.{' '}
          <Link to="/projects" className="underline">Apri i progetti</Link>
        </p>
      )}
      {LESSON_VIDEOS[d.id] && (
        <Card title="Video: la lezione passo per passo" className="mb-4">
          <video controls preload="metadata" poster={LESSON_VIDEOS[d.id].poster} className="w-full max-w-4xl rounded-md border border-ink-700 bg-black"
            aria-label={`Video della lezione: ${d.title}`}>
            <source src={LESSON_VIDEOS[d.id].src} type="video/mp4" />
          </video>
          <p className="mt-2 text-xs text-steel-500">Circa 2 minuti, in italiano: come usare Historical Intelligence, Financial Intelligence, Time Machine e Discovery su questo caso. Poi segui i passi qui sotto.</p>
        </Card>
      )}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Obiettivi">
          <ul className="list-disc space-y-1 pl-5 text-sm text-steel-300">{d.goals.map((g) => <li key={g}>{g}</li>)}</ul>
        </Card>
        <Card title="Date chiave">
          <p className="mb-2 text-xs text-steel-500">Da inserire nella cronologia, ognuna con una fonte.</p>
          <ul className="space-y-1.5 text-sm">{d.key_dates.map((k) => (
            <li key={k.date + k.event}>
              <span className="mr-2 font-mono text-xs text-gold-300">{k.date}</span><span className="text-steel-300">{k.event}</span>
              {k.source && <span className="block pl-0 text-[11px] text-steel-500">Fonte: {k.source}</span>}
            </li>
          ))}</ul>
        </Card>
        {d.tables?.map((t) => <DataTableCard key={t.title} t={t} />)}
        {!!d.gaps?.length && (
          <Card title="Cosa manca e dove cercarlo" className="lg:col-span-2">
            <p className="mb-3 text-sm text-steel-300">Questi dati non sono disponibili in rete in forma aperta. NEXUS non li stima né li inventa: indica dove si trovano.</p>
            <ul className="space-y-3 text-sm">
              {d.gaps.map((g) => (
                <li key={g.what} className="rounded-md border border-ink-700 bg-ink-850 p-3">
                  <p className="font-medium text-paper">{g.what}</p>
                  <p className="text-steel-400">Dove: {g.where}</p>
                  {g.url && <a href={g.url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-xs text-gold-300 hover:underline">{g.url.replace(/^https?:\/\//, '')} <ExternalLink className="size-3" aria-hidden /></a>}
                </li>
              ))}
            </ul>
          </Card>
        )}
        <Card title="Passi" className="lg:col-span-2">
          <ol className="space-y-3">
            {d.steps.map((s, i) => (
              <li key={s.title} className="flex flex-wrap items-start gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-ink-600 text-xs text-steel-300">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-paper">{s.title}</p>
                  <p className="text-sm text-steel-400">{s.detail}</p>
                </div>
                <Link to={s.module} className="inline-flex items-center gap-1 text-sm text-gold-300 hover:underline">Apri <ArrowRight className="size-3" aria-hidden /></Link>
              </li>
            ))}
          </ol>
        </Card>
        {d.series.length > 0 && <Card title="Serie da importare">
          <ul className="space-y-3">
            {d.series.map((s, i) => (
              <li key={s.label} className="text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="min-w-0 flex-1 text-steel-300">{s.label}</span>
                  <Button disabled={busy !== undefined || status[i]?.ok} onClick={() => importSeries(i)}><Download className="size-4" aria-hidden /> Importa</Button>
                </div>
                {status[i] && <p role="status" className={`mt-1 text-xs ${status[i].ok ? 'text-ok' : 'text-bad'}`}>{status[i].text}</p>}
              </li>
            ))}
          </ul>
        </Card>}
        <Card title="Letture consigliate">
          <ul className="space-y-2 text-sm text-steel-300">
            {d.readings.map((r) => <li key={r.title}>{r.authors.join('; ')} ({r.year}). <em>{r.title}</em>. {r.publisher}.</li>)}
          </ul>
          <p className="mt-3 text-xs text-steel-500">Riferimenti da verificare sull'originale prima di citarli.</p>
        </Card>
      </div>
    </>
  );
}
