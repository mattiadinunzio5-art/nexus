import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowRight, Download, GraduationCap, Play } from 'lucide-react';
import { api } from '../api/client';
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
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Obiettivi">
          <ul className="list-disc space-y-1 pl-5 text-sm text-steel-300">{d.goals.map((g) => <li key={g}>{g}</li>)}</ul>
        </Card>
        <Card title="Date chiave">
          <p className="mb-2 text-xs text-steel-500">Da inserire nella cronologia, ognuna con una fonte.</p>
          <ul className="space-y-1 text-sm">{d.key_dates.map((k) => <li key={k.date}><span className="mr-2 font-mono text-xs text-gold-300">{k.date}</span><span className="text-steel-300">{k.event}</span></li>)}</ul>
        </Card>
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
        <Card title="Serie da importare">
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
        </Card>
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
