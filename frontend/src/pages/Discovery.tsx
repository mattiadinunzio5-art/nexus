import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { Link, NavLink, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Archive, ArrowRight, Check, GitBranch, Pause, Play, Search, Square, X } from 'lucide-react';
import { api } from '../api/client';
import type {
  CausalChainResult, DiscoveryAnalysis, DiscoveryConnection, DiscoveryElement, DiscoveryHypothesis, DiscoveryLevel,
  DiscoverySession, ForesightResult, HypothesisStatus, TransmissionStep,
} from '../api/types';
import { formatNumber, TimeChart } from '../components/charts';
import { Badge, LibraryBadge, type BadgeTone } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Field, Input, Select, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';
import { GraphPage } from './Graph';

// --- Elementi comuni ------------------------------------------------------------------------------

const TABS = [
  ['/discovery', 'Dashboard'], ['/discovery/search', 'Discovery Search'], ['/discovery/connections', 'Connections'],
  ['/discovery/hypotheses', 'Hypotheses'], ['/discovery/anomalies', 'Anomalies'], ['/discovery/causal', 'Causal Intelligence'],
  ['/discovery/foresight', 'Strategic Foresight'], ['/discovery/graph', 'Knowledge Graph'],
] as const;

function Tabs() {
  return (
    <nav aria-label="Sezioni di Discovery Intelligence" className="-mx-1 mb-5 flex gap-1 overflow-x-auto border-b border-ink-700 px-1 pb-2">
      {TABS.map(([to, label]) => (
        <NavLink key={to} to={to} end={to === '/discovery'}
          className={({ isActive }) => `shrink-0 rounded-md px-3 py-1.5 text-sm ${isActive ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:text-paper'}`}>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

const PRINCIPLES = (
  <div className="space-y-2 text-steel-300">
    <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Discovery Intelligence</h3>
    <p>Collega le conoscenze del tuo archivio, propone ipotesi e segnala anomalie, sempre con evidenze e fonti.</p>
    <p><strong className="text-paper">Connessioni e ipotesi sono candidate da verificare</strong>, mai scoperte dimostrate. Una coincidenza temporale non è una causa; una correlazione non è una causa.</p>
    <p>I rilevatori sono deterministici e ripetibili. L'AI, se configurata, interpreta la domanda e scrive la sintesi, entro un limite di chiamate.</p>
  </div>
);

function Shell({ title, description, actions, children }: { title: string; description?: ReactNode; actions?: ReactNode; children: ReactNode }) {
  useContextPanel(PRINCIPLES, []);
  return (
    <>
      <PageHeader eyebrow="Discovery Intelligence" title={title} description={description} actions={actions} />
      <Tabs />
      {children}
    </>
  );
}

// --- Biblioteca NEXUS ------------------------------------------------------------------------------
// I risultati della Discovery eseguita sulla Biblioteca (dati aperti condivisi) si consultano a parte, in sola lettura.

type Origin = 'mine' | 'library';

function useOrigin(): [Origin, (o: Origin) => void] {
  const [params, setParams] = useSearchParams();
  const origin: Origin = params.get('origin') === 'library' ? 'library' : 'mine';
  const set = (o: Origin) => { const p = new URLSearchParams(params); if (o === 'library') p.set('origin', 'library'); else p.delete('origin'); setParams(p); };
  return [origin, set];
}

function OriginSwitch({ origin, onChange }: { origin: Origin; onChange: (o: Origin) => void }) {
  return (
    <div role="group" aria-label="Archivio" className="inline-flex self-end rounded-md border border-ink-700 bg-ink-900 p-0.5 text-sm">
      {([['mine', 'Il mio archivio'], ['library', 'Biblioteca NEXUS']] as const).map(([o, label]) => (
        <button key={o} type="button" aria-pressed={origin === o} onClick={() => onChange(o)}
          className={`rounded px-3 py-1.5 ${origin === o ? 'bg-ink-700 text-paper' : 'text-steel-400 hover:text-paper'}`}>{label}</button>
      ))}
    </div>
  );
}

const LIBRARY_NOTE = 'Risultato della Discovery sulla Biblioteca NEXUS (dati aperti con fonte): è in sola lettura. Rilevatori deterministici, nessuna AI: ogni elemento è una pista da verificare.';

function LibraryNote() {
  return <p className="mb-4 rounded-md border border-gold-500/40 bg-gold-500/10 p-3 text-sm text-gold-300">{LIBRARY_NOTE}</p>;
}

const LEVEL: Record<DiscoveryLevel, { label: string; tone: BadgeTone }> = {
  high: { label: 'affidabilità alta', tone: 'ok' }, medium: { label: 'affidabilità media', tone: 'gold' }, low: { label: 'affidabilità bassa', tone: 'warn' },
};
export function LevelBadge({ level, prefix }: { level: DiscoveryLevel; prefix?: string }) {
  const l = LEVEL[level];
  return <Badge tone={l.tone}>{prefix ? `${prefix} ${level === 'high' ? 'alta' : level === 'medium' ? 'media' : 'bassa'}` : l.label}</Badge>;
}

export const H_STATUS: Record<HypothesisStatus, { label: string; tone: BadgeTone }> = {
  to_verify: { label: 'Da verificare', tone: 'neutral' }, verifying: { label: 'In verifica', tone: 'gold' },
  confirmed: { label: 'Confermata', tone: 'ok' }, rejected: { label: 'Respinta', tone: 'bad' }, inconclusive: { label: 'Inconcludente', tone: 'warn' },
};

function ElementLink({ el }: { el: DiscoveryElement }) {
  const to = el.type === 'event' ? `/history/events/${el.id}` : el.type === 'series' ? `/financial/series/${el.id}` : `/graph?focus=${el.id}`;
  const kind = el.type === 'event' ? 'Evento' : el.type === 'series' ? 'Serie' : 'Entità';
  return <Link to={to} className="inline-flex items-baseline gap-1 rounded border border-ink-600 px-2 py-0.5 text-xs text-steel-200 hover:border-gold-500"><span className="text-steel-500">{kind}</span> {el.label}</Link>;
}

function useAction() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  async function run(fn: () => Promise<unknown>, ok?: string) {
    setBusy(true);
    setMsg(undefined);
    try {
      await fn();
      if (ok) setMsg({ ok: true, text: ok });
    } catch (e) {
      setMsg({ ok: false, text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }
  const view = msg ? <p role={msg.ok ? 'status' : 'alert'} className={`text-sm ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p> : null;
  return { busy, run, view };
}

function List({ items }: { items: string[] }) {
  if (!items.length) return <EmptyState>Nessun elemento.</EmptyState>;
  return <ul className="list-disc space-y-1 pl-5 text-sm text-steel-300">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>;
}

// --- Panoramica ------------------------------------------------------------------------------------

export function DiscoveryDashboardPage() {
  const o = useAsync(() => api.discoveryOverview(), []);
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const { busy, run, view } = useAction();
  return (
    <Shell title="Discovery Intelligence" description="Connessioni, ipotesi, anomalie, catene causali e scenari costruiti sul tuo archivio, con evidenze e fonti.">
      <form className="mb-5 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (q.trim()) nav(`/discovery/search?q=${encodeURIComponent(q.trim())}`); }}>
        <Input aria-label="Domanda di discovery" value={q} onChange={(e) => setQ(e.target.value)} className="min-w-64 flex-1"
          placeholder="Es. connessioni tra le crisi finanziarie del Novecento e il sistema monetario internazionale" />
        <Button type="submit" variant="primary" disabled={!q.trim()}><Search className="size-4" aria-hidden /> Analizza</Button>
        <Button disabled={busy} onClick={() => run(async () => { const s = await api.startDiscovery('autonomous'); nav(`/discovery/search?session=${s.id}`); })}>
          <Play className="size-4" aria-hidden /> Discovery autonoma
        </Button>
      </form>
      {view}
      {o.loading && <Loading />}
      {o.error && <ErrorBox error={o.error} onRetry={o.reload} />}
      {o.data && (
        <>
          {o.data.archive.events + o.data.archive.series + o.data.archive.entities === 0 && (
            <p className="mb-4 rounded-md border border-warn/40 bg-warn/10 p-3 text-sm text-warn">
              L'archivio è vuoto: Discovery lavora su eventi, serie, documenti ed entità che inserisci. Senza materiale non produce risultati (e non ne inventa).
            </p>
          )}
          <dl className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              ['Connections', o.data.connections, `${o.data.connections_new} da esaminare`, '/discovery/connections'],
              ['Hypotheses', o.data.hypotheses, `${o.data.hypotheses_by_status.to_verify} da verificare · ${o.data.hypotheses_by_status.verifying} in verifica`, '/discovery/hypotheses'],
              ['Open anomalies', o.data.anomalies_open, 'ordinate per rilevanza', '/discovery/anomalies'],
              ['Analisi in corso', o.data.running.length, o.data.running.length ? o.data.running.map((r) => `#${r.id} ${r.status}`).join(', ') : 'nessuna', '/discovery/search'],
            ].map(([label, value, hint, to]) => (
              <Link key={label as string} to={to as string} className="rounded-lg border border-ink-700 bg-ink-900 p-4 hover:border-gold-500">
                <dt className="text-[11px] uppercase tracking-[0.14em] text-steel-500">{label}</dt>
                <dd className="mt-1 text-2xl text-paper">{value}</dd>
                <dd className="mt-1 text-xs text-steel-400">{hint}</dd>
              </Link>
            ))}
          </dl>
          {o.data.library && o.data.library.connections + o.data.library.anomalies + o.data.library.hypotheses > 0 && (
            <section aria-labelledby="disc-library" className="mb-5 rounded-lg border border-gold-500/40 bg-ink-900 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <LibraryBadge /><h2 id="disc-library" className="text-sm font-medium text-paper">Discovery sulla Biblioteca NEXUS</h2>
                {o.data.library.last_run && <span className="text-xs text-steel-500">aggiornata il {formatDateTime(o.data.library.last_run)}</span>}
              </div>
              <p className="mt-1 text-sm text-steel-400">Piste trovate sui dati aperti condivisi (eventi, serie ufficiali, grafo): da consultare e verificare, in sola lettura.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link to="/discovery/connections?origin=library" className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-paper hover:border-gold-500">{o.data.library.connections} connessioni</Link>
                <Link to="/discovery/hypotheses?origin=library" className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-paper hover:border-gold-500">{o.data.library.hypotheses} ipotesi</Link>
                <Link to="/discovery/anomalies?origin=library" className="rounded-md border border-ink-700 px-3 py-1.5 text-sm text-paper hover:border-gold-500">{o.data.library.anomalies} anomalie</Link>
              </div>
            </section>
          )}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Card title="Ultime connessioni">
              {o.data.latest_connections.length ? <ul className="space-y-2">{o.data.latest_connections.map((c) => (
                <li key={c.id}><Link to={`/discovery/connections/${c.id}`} className="text-sm text-paper hover:text-gold-300">{c.title}</Link>
                  <p className="text-xs text-steel-500">{c.kind_label} · {c.period}</p></li>))}</ul> : <EmptyState>Ancora nessuna connessione: avvia un'analisi.</EmptyState>}
            </Card>
            <Card title="Ultime ipotesi">
              {o.data.latest_hypotheses.length ? <ul className="space-y-2">{o.data.latest_hypotheses.map((h) => (
                <li key={h.id}><Link to={`/discovery/hypotheses/${h.id}`} className="text-sm text-paper hover:text-gold-300">{h.title}</Link>
                  <p className="mt-0.5"><Badge tone={H_STATUS[h.status].tone}>{H_STATUS[h.status].label}</Badge></p></li>))}</ul> : <EmptyState>Nessuna ipotesi.</EmptyState>}
            </Card>
            <Card title="Anomalie principali">
              {o.data.latest_anomalies.length ? <ul className="space-y-2">{o.data.latest_anomalies.map((a) => (
                <li key={a.id}><Link to={`/discovery/anomalies#a${a.id}`} className="text-sm text-paper hover:text-gold-300">{a.title}</Link>
                  <p className="text-xs text-steel-500">{a.period}</p></li>))}</ul> : <EmptyState>Nessuna anomalia aperta.</EmptyState>}
            </Card>
          </div>
        </>
      )}
    </Shell>
  );
}

// --- Discovery Search e sessioni ---------------------------------------------------------------------

const S_STATUS: Record<DiscoverySession['status'], { label: string; tone: BadgeTone }> = {
  queued: { label: 'In coda', tone: 'neutral' }, running: { label: 'In corso', tone: 'gold' }, paused: { label: 'In pausa', tone: 'warn' },
  stopped: { label: 'Fermata', tone: 'warn' }, completed: { label: 'Completata', tone: 'ok' }, failed: { label: 'Non riuscita', tone: 'bad' },
};

function SessionView({ id, onChange }: { id: number; onChange: () => void }) {
  const s = useAsync(() => api.discoverySession(id), [id]);
  const { busy, run, view } = useAction();
  const active = s.data && ['queued', 'running'].includes(s.data.status);
  useEffect(() => {
    if (!active) return;
    const t = window.setInterval(() => void s.reload(), 1500);
    return () => window.clearInterval(t);
  }, [active, s.reload]);
  if (s.loading && !s.data) return <Loading />;
  if (s.error) return <ErrorBox error={s.error} onRetry={s.reload} />;
  const d = s.data!;
  const act = (a: 'pause' | 'resume' | 'stop') => run(async () => { s.setData(await api.controlDiscovery(d.id, a)); onChange(); });
  const synth = d.result.synthesis;
  return (
    <Card title={`Sessione #${d.id} · ${d.mode === 'guided' ? 'guidata' : 'autonoma'}`} action={<Badge tone={S_STATUS[d.status].tone}>{S_STATUS[d.status].label}</Badge>}>
      {d.query && <p className="mb-3 text-paper">«{d.query}»</p>}
      <div className="mb-3 flex flex-wrap gap-2">
        {['queued', 'running'].includes(d.status) && <Button disabled={busy} onClick={() => act('pause')}><Pause className="size-4" aria-hidden /> Pausa</Button>}
        {d.status === 'paused' && <Button disabled={busy} variant="primary" onClick={() => act('resume')}><Play className="size-4" aria-hidden /> Riprendi</Button>}
        {['queued', 'running', 'paused'].includes(d.status) && <Button disabled={busy} onClick={() => act('stop')}><Square className="size-4" aria-hidden /> Ferma</Button>}
        <span className="self-center text-xs text-steel-500">
          Limiti: {d.limits.max_seconds} s · {d.limits.max_items} risultati per tipo · chiamate AI {d.llm_calls}/{d.limits.max_llm_calls}
          {d.limits.provider && d.limits.provider !== 'none' ? ` (${d.limits.provider})` : ' (AI non configurata: sintesi locale)'} · tempo usato {(d.elapsed_ms / 1000).toFixed(1)} s
        </span>
      </div>
      {view}
      {d.error && <p role="alert" className="mb-3 text-sm text-warn">{d.error}</p>}
      <ol className="mb-4 space-y-2" aria-label="Passi della sessione">
        {d.plan.map((label, i) => {
          const st = d.steps.filter((x) => x.label === label).at(-1);
          const done = i < d.cursor;
          return (
            <li key={label} className="flex gap-3 text-sm">
              <span className={`mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border text-[10px] ${done ? 'border-ok text-ok' : i === d.cursor && active ? 'border-gold-400 text-gold-300' : 'border-ink-600 text-steel-500'}`}>
                {done ? <Check className="size-3" aria-hidden /> : i + 1}
              </span>
              <div className="min-w-0">
                <p className={done ? 'text-paper' : 'text-steel-400'}>{label}{st && <span className="ml-2 text-[11px] text-steel-500">{st.executor === 'ai' ? `AI${st.model ? ` · ${st.model}` : ''}` : 'motore locale'} · {(st.duration_ms / 1000).toFixed(1)} s{st.status !== 'executed' ? ` · ${st.status}` : ''}</span>}</p>
                {st && <p className="text-xs text-steel-400">{st.summary}</p>}
              </div>
            </li>
          );
        })}
      </ol>
      {synth && (
        <div className="mb-4 rounded-md border border-ink-700 bg-ink-950 p-3">
          <p className="mb-1 text-[11px] uppercase tracking-[0.14em] text-steel-500">Sintesi · {synth.executor === 'ai' ? 'scritta dall’AI sugli elementi trovati' : 'locale'}</p>
          <p className="whitespace-pre-line text-sm text-steel-200">{synth.text}</p>
          {synth.note && <p className="mt-2 text-xs text-warn">{synth.note}</p>}
        </div>
      )}
      {!!d.result.leads?.length && (
        <div className="mb-4">
          <p className="mb-1 text-[11px] uppercase tracking-[0.14em] text-steel-500">Piste di approfondimento</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-steel-300">{d.result.leads.map((l, i) => (
            <li key={i}>{l.ref.hypothesis_id ? <Link className="hover:text-gold-300" to={`/discovery/hypotheses/${l.ref.hypothesis_id}`}>{l.text}</Link>
              : l.ref.event_id ? <Link className="hover:text-gold-300" to={`/history/events/${l.ref.event_id}`}>{l.text}</Link> : l.text}</li>))}</ul>
        </div>
      )}
      {['completed', 'stopped', 'failed'].includes(d.status) && (
        <div className="flex flex-wrap gap-3 text-sm">
          <Link className="text-gold-300 hover:underline" to={`/discovery/connections?session=${d.id}`}>Connections della sessione</Link>
          <Link className="text-gold-300 hover:underline" to="/discovery/hypotheses">Hypotheses</Link>
          <Link className="text-gold-300 hover:underline" to="/discovery/anomalies">Anomalies</Link>
          <Link className="text-gold-300 hover:underline" to="/discovery/causal">Causal Intelligence</Link>
        </div>
      )}
    </Card>
  );
}

export function DiscoverySearchPage() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get('q') ?? '');
  const sessions = useAsync(() => api.discoverySessions(), []);
  const selected = Number(params.get('session')) || sessions.data?.[0]?.id;
  const { busy, run, view } = useAction();
  function start(e: FormEvent) {
    e.preventDefault();
    void run(async () => { const s = await api.startDiscovery('guided', q); setParams({ session: String(s.id) }); await sessions.reload(); });
  }
  return (
    <Shell title="Discovery Search" description="Fai una domanda complessa: NEXUS individua l'ambito nel tuo archivio, cerca connessioni, anomalie e catene causali, genera ipotesi e scrive una sintesi.">
      <form onSubmit={start} className="mb-4 space-y-2">
        <Textarea aria-label="Domanda" rows={3} value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Individua le connessioni tra le crisi finanziarie del Novecento e le trasformazioni del sistema monetario internazionale" />
        <div className="flex flex-wrap gap-2">
          <Button type="submit" variant="primary" disabled={busy || !q.trim()}><Search className="size-4" aria-hidden /> Avvia l'analisi guidata</Button>
          <Button disabled={busy} onClick={() => run(async () => { const s = await api.startDiscovery('autonomous'); setParams({ session: String(s.id) }); await sessions.reload(); })}>
            <Play className="size-4" aria-hidden /> Avvia la discovery autonoma
          </Button>
        </div>
        {view}
      </form>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_280px]">
        <div>{selected ? <SessionView key={selected} id={selected} onChange={() => void sessions.reload()} /> : <EmptyState>Nessuna sessione: scrivi una domanda o avvia la discovery autonoma.</EmptyState>}</div>
        <Card title="Sessioni">
          {sessions.error && <ErrorBox error={sessions.error} onRetry={sessions.reload} />}
          <ul className="space-y-1">{sessions.data?.map((s) => (
            <li key={s.id}>
              <button onClick={() => setParams({ session: String(s.id) })} className={`w-full rounded-md px-2 py-1.5 text-left text-sm ${s.id === selected ? 'bg-ink-800 text-paper' : 'text-steel-300 hover:bg-ink-800'}`}>
                <span className="block truncate">#{s.id} {s.query || 'Discovery autonoma'}</span>
                <span className="text-[11px] text-steel-500">{S_STATUS[s.status].label} · {formatDateTime(s.created_at)}</span>
              </button>
            </li>))}</ul>
        </Card>
      </div>
    </Shell>
  );
}

// --- Connessioni -----------------------------------------------------------------------------------

const KINDS: Record<string, string> = {
  shared_actors: 'Attori condivisi', textual_reference: 'Riferimento testuale', graph_proximity: 'Vicinanza nel grafo',
  event_data_change: 'Coincidenza evento–dati', statistical_association: 'Associazione statistica',
};

export function ConnectionsPage() {
  const [params, setParams] = useSearchParams();
  const kind = params.get('kind') ?? '';
  const status = params.get('status') ?? '';
  const session = Number(params.get('session')) || undefined;
  const [origin, setOrigin] = useOrigin();
  const list = useAsync(() => api.discoveryConnections({ kind: kind || undefined, status: status || undefined, session_id: session, origin }), [kind, status, session, origin]);
  const set = (k: string, v: string) => { const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); setParams(p); };
  return (
    <Shell title="Connections" description="Collegamenti candidati tra eventi, serie ed entità. Ognuno ha elementi, tipo di relazione, periodo, evidenze, fonti e affidabilità motivata.">
      <div className="mb-4 flex flex-wrap gap-3">
        <Field label="Tipo"><Select value={kind} onChange={(e) => set('kind', e.target.value)}><option value="">Tutti</option>{Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
        <Field label="Stato"><Select value={status} onChange={(e) => set('status', e.target.value)}><option value="">Tutti</option><option value="new">Da esaminare</option><option value="accepted">Accettate</option><option value="dismissed">Scartate</option></Select></Field>
        {session && <button className="self-end pb-2 text-xs text-gold-300 hover:underline" onClick={() => set('session', '')}>Solo sessione #{session} ✕</button>}
        <OriginSwitch origin={origin} onChange={setOrigin} />
      </div>
      {origin === 'library' && <LibraryNote />}
      {list.loading && <Loading />}
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {list.data?.length === 0 && <EmptyState>Nessuna connessione con questi filtri.</EmptyState>}
      <ul className="space-y-3">{list.data?.map((c) => (
        <li key={c.id}>
          <Link to={`/discovery/connections/${c.id}`} className="block rounded-lg border border-ink-700 bg-ink-900 p-4 hover:border-gold-500">
            <div className="flex flex-wrap items-center gap-2">
              {c.library && <LibraryBadge />}<Badge tone="neutral">{c.kind_label}</Badge><LevelBadge level={c.reliability} />
              {c.status !== 'new' && <Badge tone={c.status === 'accepted' ? 'ok' : 'neutral'}>{c.status === 'accepted' ? 'accettata' : 'scartata'}</Badge>}
              <span className="text-xs text-steel-500">{c.period}</span>
            </div>
            <p className="mt-2 font-medium text-paper">{c.title}</p>
            <p className="mt-1 line-clamp-2 text-sm text-steel-400">{c.explanation}</p>
          </Link>
        </li>))}</ul>
    </Shell>
  );
}

export function ConnectionDetailPage() {
  const id = Number(useParams().connectionId);
  const c = useAsync(() => api.discoveryConnection(id), [id]);
  const nav = useNavigate();
  const { busy, run, view } = useAction();
  if (c.loading && !c.data) return <Shell title="Connection"><Loading /></Shell>;
  if (c.error) return <Shell title="Connection"><ErrorBox error={c.error} onRetry={c.reload} /></Shell>;
  const d = c.data as DiscoveryConnection;
  return (
    <Shell title={d.title} description={<span className="flex flex-wrap items-center gap-2">{d.library && <LibraryBadge />}{d.kind_label} · {d.period}</span>}
      actions={d.library ? undefined : <>
        {d.status !== 'accepted' && <Button variant="primary" disabled={busy} onClick={() => run(async () => c.setData(await api.setConnectionStatus(d.id, 'accepted')), 'Salvata nel Knowledge Graph come ipotesi (non come relazione documentata).')}><Check className="size-4" aria-hidden /> Accetta</Button>}
        {d.status !== 'dismissed' && <Button disabled={busy} onClick={() => run(async () => c.setData(await api.setConnectionStatus(d.id, 'dismissed')))}><X className="size-4" aria-hidden /> Scarta</Button>}
        <Button disabled={busy} onClick={() => run(async () => { const h = await api.hypothesisFromConnection(d.id); nav(`/discovery/hypotheses/${h.id}`); })}>Genera l'ipotesi</Button>
      </>}>
      {view}
      {d.library && <LibraryNote />}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Elementi e spiegazione" className="lg:col-span-2">
          <div className="mb-3 flex flex-wrap gap-2">{d.elements.map((e) => <ElementLink key={`${e.type}${e.id}`} el={e} />)}</div>
          <p className="text-sm text-steel-200">{d.explanation}</p>
          {d.graph_relation_id && <p className="mt-2 text-xs text-ok">Salvata nel grafo come ipotesi (relazione #{d.graph_relation_id}).</p>}
        </Card>
        <Card title="Evidenze">
          <ul className="space-y-2">{d.evidence.map((e, i) => <li key={i} className="text-sm"><p className="text-steel-300">{e.label}</p><p className="text-steel-400">{e.detail}</p></li>)}</ul>
        </Card>
        <Card title="Affidabilità">
          <p className="mb-2"><LevelBadge level={d.reliability} /></p>
          <List items={d.reliability_reasons} />
          <p className="mt-3 text-xs text-steel-500">Fonti collegate: {d.sources.length ? d.sources.map((s) => <Link key={s} to="/bibliography" className="mr-1 text-gold-300 hover:underline">#{s}</Link>) : 'nessuna'}</p>
        </Card>
        <Card title="Cautele" className="lg:col-span-2"><List items={d.caveats} /></Card>
      </div>
    </Shell>
  );
}

// --- Ipotesi ---------------------------------------------------------------------------------------

export function HypothesesPage() {
  const [status, setStatus] = useState('');
  const [archived, setArchived] = useState(false);
  const [origin, setOrigin] = useOrigin();
  const list = useAsync(() => api.discoveryHypotheses({ status: status || undefined, archived, origin }), [status, archived, origin]);
  const [compare, setCompare] = useState<number[]>([]);
  const chosen = useMemo(() => list.data?.filter((h) => compare.includes(h.id)) ?? [], [list.data, compare]);
  return (
    <Shell title="Hypotheses" description="Ipotesi generate dalle connessioni. Nessuna è una scoperta dimostrata: la verifica automatica raccoglie elementi, l'esito lo decidi tu.">
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Stato"><Select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tutti</option>{Object.entries(H_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</Select></Field>
        <label className="flex items-center gap-2 pb-2 text-sm text-steel-300"><input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /> Archiviate</label>
        {compare.length > 0 && <span className="pb-2 text-xs text-steel-400">{compare.length} selezionate per il confronto (max 3) · <button className="text-gold-300 hover:underline" onClick={() => setCompare([])}>azzera</button></span>}
        <OriginSwitch origin={origin} onChange={(o) => { setCompare([]); setOrigin(o); }} />
      </div>
      {origin === 'library' && <LibraryNote />}
      {list.loading && <Loading />}
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {list.data?.length === 0 && <EmptyState>Nessuna ipotesi.</EmptyState>}
      {chosen.length >= 2 && (
        <Card title="Confronto" className="mb-4">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <tbody>
                {([['Stato', (h: DiscoveryHypothesis) => H_STATUS[h.status].label], ['Confidenza', (h: DiscoveryHypothesis) => h.confidence],
                  ['Fenomeni', (h: DiscoveryHypothesis) => h.phenomena.join(', ')], ['A favore', (h: DiscoveryHypothesis) => String(h.supporting.length)],
                  ['Contro', (h: DiscoveryHypothesis) => String(h.contrary.length)], ['Mancano', (h: DiscoveryHypothesis) => h.missing.join('; ')],
                  ['Ultima verifica', (h: DiscoveryHypothesis) => h.verification.at(-1)?.checks.map((c) => `${c.check}: ${c.outcome}`).join('; ') ?? '—']] as const).map(([label, get]) => (
                  <tr key={label} className="border-t border-ink-700 align-top">
                    <th className="w-32 py-2 pr-3 text-xs font-medium text-steel-500">{label}</th>
                    {chosen.map((h) => <td key={h.id} className="py-2 pr-3 text-steel-300">{get(h)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      <ul className="space-y-3">{list.data?.map((h) => (
        <li key={h.id} className="flex gap-3 rounded-lg border border-ink-700 bg-ink-900 p-4">
          <input type="checkbox" aria-label={`Confronta: ${h.title}`} className="mt-1" checked={compare.includes(h.id)} disabled={!compare.includes(h.id) && compare.length >= 3}
            onChange={(e) => setCompare((c) => e.target.checked ? [...c, h.id] : c.filter((x) => x !== h.id))} />
          <Link to={`/discovery/hypotheses/${h.id}`} className="min-w-0 flex-1">
            <div className="flex flex-wrap gap-2">{h.library && <LibraryBadge />}<Badge tone={H_STATUS[h.status].tone}>{H_STATUS[h.status].label}</Badge><LevelBadge level={h.confidence} prefix="confidenza" /></div>
            <p className="mt-2 font-medium text-paper hover:text-gold-300">{h.title}</p>
            <p className="mt-1 text-xs text-steel-500">{h.phenomena.join(' · ')}</p>
          </Link>
        </li>))}</ul>
    </Shell>
  );
}

export function HypothesisDetailPage() {
  const id = Number(useParams().hypothesisId);
  const h = useAsync(() => api.discoveryHypothesis(id), [id]);
  const { busy, run, view } = useAction();
  const [decision, setDecision] = useState<HypothesisStatus>('inconclusive');
  const [note, setNote] = useState('');
  if (h.loading && !h.data) return <Shell title="Hypotheses"><Loading /></Shell>;
  if (h.error) return <Shell title="Hypotheses"><ErrorBox error={h.error} onRetry={h.reload} /></Shell>;
  const d = h.data as DiscoveryHypothesis;
  const last = d.verification.at(-1);
  const decided = ['confirmed', 'rejected', 'inconclusive'].includes(d.status);
  return (
    <Shell title={d.title}
      description={<span className="flex flex-wrap items-center gap-2">{d.library && <LibraryBadge />}<Badge tone={H_STATUS[d.status].tone}>{H_STATUS[d.status].label}</Badge><LevelBadge level={d.confidence} prefix="confidenza" />{d.archived && <Badge>archiviata</Badge>}</span>}
      actions={d.library ? undefined : <>
        {!decided && <Button variant="primary" disabled={busy} onClick={() => run(async () => h.setData(await api.verifyHypothesis(d.id)), 'Verifica eseguita: leggi i controlli e decidi l’esito.')}>Verifica</Button>}
        {!d.graph_entity_id && <Button disabled={busy} onClick={() => run(async () => h.setData(await api.hypothesisToGraph(d.id)), 'Aggiunta al Knowledge Graph come nodo «ipotesi».')}><GitBranch className="size-4" aria-hidden /> Nel grafo</Button>}
        <Button disabled={busy} onClick={() => run(async () => h.setData(await api.archiveHypothesis(d.id, !d.archived)))}><Archive className="size-4" aria-hidden /> {d.archived ? 'Ripristina' : 'Archivia'}</Button>
      </>}>
      {view}
      {d.library && <LibraryNote />}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Descrizione" className="lg:col-span-2">
          <p className="whitespace-pre-line text-sm text-steel-200">{d.description}</p>
          <p className="mt-3 text-xs text-steel-500">Fenomeni: {d.phenomena.join(' · ')} · {d.motivation}{d.connection_id && <> · <Link className="text-gold-300 hover:underline" to={`/discovery/connections/${d.connection_id}`}>connessione di origine</Link></>}{d.graph_entity_id && <> · <Link className="text-gold-300 hover:underline" to={`/graph?focus=${d.graph_entity_id}`}>nodo nel grafo</Link></>}</p>
        </Card>
        <Card title="Evidenze a supporto"><List items={d.supporting} /></Card>
        <Card title="Evidenze contrarie e cautele"><List items={d.contrary} /></Card>
        <Card title="Informazioni mancanti"><List items={d.missing} /></Card>
        <Card title="Metodo di verifica"><List items={d.method} /></Card>
        <Card title="Verifica" className="lg:col-span-2">
          {!last ? <EmptyState>Non ancora verificata. «Verifica» controlla stabilità statistica, passaggi nei documenti, fonti indipendenti e relazioni nel grafo.</EmptyState> : (
            <>
              <p className="mb-2 text-xs text-steel-500">Ultima verifica: {formatDateTime(last.at)} · esito suggerito: <strong className="text-steel-300">{H_STATUS[last.suggested as HypothesisStatus]?.label ?? last.suggested}</strong> (solo un suggerimento)</p>
              <ul className="space-y-3">{last.checks.map((c, i) => (
                <li key={i} className="text-sm">
                  <p className="text-paper">{c.check} <Badge tone={c.outcome === 'supports' ? 'ok' : c.outcome === 'contradicts' ? 'bad' : 'neutral'}>{({ supports: 'a favore', contradicts: 'contro', weak: 'debole', nothing_found: 'nessun elemento', insufficient_data: 'dati insufficienti', not_possible: 'non eseguibile' } as Record<string, string>)[c.outcome] ?? c.outcome}</Badge></p>
                  <p className="text-steel-400">{c.detail}</p>
                  {c.passages?.map((p, k) => <blockquote key={k} className="mt-1 border-l-2 border-ink-600 pl-3 text-xs text-steel-400"><Link className="text-gold-300 hover:underline" to={`/documents/${p.document_id}`}>{p.label}</Link>: {p.text}</blockquote>)}
                </li>))}</ul>
            </>
          )}
        </Card>
        {!d.library && <Card title="Esito (deciso da te)" className="lg:col-span-2">
          {d.decision_note && <p className="mb-3 text-sm text-steel-300"><strong className="text-paper">{H_STATUS[d.status].label}</strong>{d.decided_at && ` il ${formatDateTime(d.decided_at)}`}: {d.decision_note}</p>}
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); void run(async () => { h.setData(await api.decideHypothesis(d.id, decision, note)); setNote(''); }, 'Esito registrato.'); }}>
            <Field label="Esito"><Select value={decision} onChange={(e) => setDecision(e.target.value as HypothesisStatus)}>
              <option value="confirmed">Confermata</option><option value="rejected">Respinta</option><option value="inconclusive">Inconcludente</option><option value="to_verify">Riporta «da verificare»</option>
            </Select></Field>
            <Field label="Motivazione (obbligatoria)"><Input value={note} onChange={(e) => setNote(e.target.value)} className="min-w-64" placeholder="Su quali evidenze ti basi?" /></Field>
            <Button type="submit" disabled={busy}>Registra</Button>
          </form>
        </Card>}
      </div>
    </Shell>
  );
}

// --- Anomalie --------------------------------------------------------------------------------------

export function AnomaliesPage() {
  const [status, setStatus] = useState('open');
  const [origin, setOrigin] = useOrigin();
  const list = useAsync(() => api.discoveryAnomalies(status || undefined, origin), [status, origin]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const { busy, run, view } = useAction();
  const KIND: Record<string, string> = { series_change: 'Variazione anomala', trend_deviation: 'Deviazione dal trend', source_discrepancy: 'Discrepanza tra fonti', chronology: 'Incongruenza cronologica' };
  return (
    <Shell title="Anomalies" description="Variazioni insolite, deviazioni dal trend, fonti in disaccordo e incongruenze cronologiche, ordinate per rilevanza e verificabilità. Con dati insufficienti non viene segnalato nulla.">
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Stato"><Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-auto"><option value="open">Aperte</option><option value="explained">Spiegate</option><option value="dismissed">Scartate</option><option value="">Tutte</option></Select></Field>
        <OriginSwitch origin={origin} onChange={setOrigin} />
      </div>
      {origin === 'library' && <LibraryNote />}
      {view}
      {list.loading && <Loading />}
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {list.data?.length === 0 && <EmptyState>Nessuna anomalia.</EmptyState>}
      <ul className="space-y-3">{list.data?.map((a) => (
        <li key={a.id} id={`a${a.id}`} className="rounded-lg border border-ink-700 bg-ink-900 p-4">
          <div className="flex flex-wrap gap-2">{a.library && <LibraryBadge />}<Badge>{KIND[a.kind] ?? a.kind}</Badge><Badge tone={a.verifiability === 'high' ? 'ok' : 'neutral'}>verificabilità {a.verifiability === 'high' ? 'alta' : a.verifiability === 'medium' ? 'media' : 'bassa'}</Badge><span className="text-xs text-steel-500">rilevanza {formatNumber(a.relevance, 3)} · {a.period}</span></div>
          <p className="mt-2 font-medium text-paper">{a.title}</p>
          <dl className="mt-2 grid gap-2 text-sm md:grid-cols-2">
            <div><dt className="text-xs text-steel-500">Cosa è cambiato</dt><dd className="text-steel-300">{a.what_changed}</dd></div>
            <div><dt className="text-xs text-steel-500">Rispetto a quale riferimento</dt><dd className="text-steel-300">{a.reference}</dd></div>
          </dl>
          <p className="mt-2 text-xs text-steel-500">Spiegazioni alternative</p>
          <List items={a.alternatives} />
          <div className="mt-2 flex flex-wrap gap-3 text-xs">
            {a.refs.series_id && <Link className="text-gold-300 hover:underline" to={`/financial/series/${a.refs.series_id}`}>Apri la serie</Link>}
            {a.refs.series_ids?.map((s) => <Link key={s} className="text-gold-300 hover:underline" to={`/financial/series/${s}`}>Serie #{s}</Link>)}
            {a.refs.event_ids?.map((e) => <Link key={e} className="text-gold-300 hover:underline" to={`/history/events/${e}`}>Evento #{e}</Link>)}
          </div>
          {a.library ? null : a.status === 'open' ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <Input aria-label="Spiegazione o motivo" placeholder="Spiegazione o motivo" value={notes[a.id] ?? ''} onChange={(e) => setNotes({ ...notes, [a.id]: e.target.value })} className="min-w-56 flex-1" />
              <Button disabled={busy} onClick={() => run(async () => { await api.updateAnomaly(a.id, 'explained', notes[a.id] ?? ''); await list.reload(); })}>Spiegata</Button>
              <Button disabled={busy} onClick={() => run(async () => { await api.updateAnomaly(a.id, 'dismissed', notes[a.id] ?? ''); await list.reload(); })}>Scarta</Button>
            </div>
          ) : <p className="mt-2 text-xs text-steel-400">{a.status === 'explained' ? 'Spiegata' : 'Scartata'}: {a.note}</p>}
        </li>))}</ul>
    </Shell>
  );
}

// --- Catene causali ----------------------------------------------------------------------------------

const CLASS_TONE: Record<string, BadgeTone> = { causal_documented: 'ok', influence_documented: 'ok', causal_hypothesized: 'gold', influence_hypothesized: 'gold', association: 'neutral', correlation: 'neutral' };

function ChainView({ r }: { r: CausalChainResult }) {
  return (
    <div className="space-y-4">
      {r.notes.map((n) => <p key={n} className="text-sm text-warn">{n}</p>)}
      {r.paths.map((p, i) => (
        <div key={i} className="rounded-md border border-ink-700 p-3">
          <p className="mb-2 text-xs text-steel-500">Catena {i + 1} · forza: <Badge tone={CLASS_TONE[p.strength]}>{p.strength_label}</Badge> (l'anello più debole)</p>
          <ol className="space-y-2">{p.links.map((l, k) => (
            <li key={k} className="text-sm">
              <p className="text-paper">{l.from} <ArrowRight className="inline size-3" aria-hidden /> {l.to} <Badge tone={CLASS_TONE[l.class]}>{l.label}</Badge></p>
              <p className="text-xs text-steel-400">Evidenza: {l.evidence || '—'}</p>
              {!!l.alternatives.length && <p className="text-xs text-steel-500">Altre cause note di «{l.to}»: {l.alternatives.join(', ')}</p>}
            </li>))}</ol>
        </div>
      ))}
      {!!r.common_causes.length && <p className="text-sm text-steel-400">Cause comuni ai due estremi (possibili fattori confondenti): {r.common_causes.join(', ')}</p>}
    </div>
  );
}

function TransmissionView({ steps, notes }: { steps: TransmissionStep[]; notes: string[] }) {
  return (
    <div className="space-y-3">
      <ol className="space-y-3">{steps.map((s, i) => (
        <li key={i} className="rounded-md border border-ink-700 p-3 text-sm">
          <p className="text-paper">{s.from} <ArrowRight className="inline size-3" aria-hidden /> {s.to} <Badge tone={CLASS_TONE[s.class]}>{s.label}</Badge></p>
          {s.statistic && <p className="text-xs text-steel-400">r = {formatNumber(s.statistic.r, 3)}, ritardo {s.statistic.lag}, n = {s.statistic.n}, p corretto = {formatNumber(s.statistic.p_adj, 2)} ({s.statistic.freq})</p>}
          {s.evidence && <p className="text-xs text-steel-400">Evidenza: {s.evidence}</p>}
          <p className="text-xs text-steel-400">Incertezza: {s.uncertainty}</p>
          <p className="text-xs text-steel-500">Variabili: {s.variables.join(' · ')}</p>
          <p className="text-xs text-steel-500">Spiegazioni alternative: {s.alternatives.join('; ')}</p>
        </li>))}</ol>
      {notes.map((n) => <p key={n} className="text-xs text-steel-500">{n}</p>)}
    </div>
  );
}

export function CausalPage() {
  const entities = useAsync(() => api.entities(), []);
  const series = useAsync(() => api.seriesList(), []);
  const templates = useAsync(() => api.causalTemplates(), []);
  const saved = useAsync(() => api.discoveryAnalyses(), []);
  const [a, setA] = useState('');
  const [b, setB] = useState('');
  const [chain, setChain] = useState<CausalChainResult>();
  const [rows, setRows] = useState<{ id: string; label: string }[]>([{ id: '', label: '' }, { id: '', label: '' }]);
  const [trans, setTrans] = useState<{ steps: TransmissionStep[]; notes: string[] }>();
  const [imp, setImp] = useState<Record<string, string>>({});
  const { busy, run, view } = useAction();
  const opts = entities.data?.map((e) => <option key={e.id} value={e.id}>{e.name}</option>);
  const sopts = series.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>);
  return (
    <Shell title="Causal Intelligence" description="Causal Intelligence distingue relazioni causali documentate, relazioni causali ipotizzate e semplici correlazioni, con evidenze, alternative e incertezza.">
      {view}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Catena tra due elementi del grafo">
          <form className="mb-3 flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); void run(async () => { setChain((await api.causalChains(Number(a), Number(b))).result); await saved.reload(); }); }}>
            <Field label="Da (causa)"><Select value={a} onChange={(e) => setA(e.target.value)}><option value="">—</option>{opts}</Select></Field>
            <Field label="A (effetto)"><Select value={b} onChange={(e) => setB(e.target.value)}><option value="">—</option>{opts}</Select></Field>
            <Button type="submit" variant="primary" disabled={busy || !a || !b}>Ricostruisci</Button>
          </form>
          {entities.data?.length === 0 && <EmptyState>Il grafo è vuoto: aggiungi entità e relazioni nel Knowledge Graph.</EmptyState>}
          {chain && <ChainView r={chain} />}
        </Card>
        <Card title="Catena di trasmissione tra serie">
          <p className="mb-3 text-xs text-steel-400">Metti le serie nell'ordine della catena (es. tassi → credito → investimenti → PIL → disoccupazione). Per ogni passaggio NEXUS calcola la correlazione ritardata delle variazioni.</p>
          <div className="space-y-2">{rows.map((r, i) => (
            <div key={i} className="flex flex-wrap gap-2">
              <Select aria-label={`Serie ${i + 1}`} value={r.id} onChange={(e) => setRows(rows.map((x, k) => k === i ? { ...x, id: e.target.value } : x))} className="min-w-48 flex-1"><option value="">— serie {i + 1} —</option>{sopts}</Select>
              <Input aria-label={`Etichetta ${i + 1}`} placeholder="Etichetta (facoltativa)" value={r.label} onChange={(e) => setRows(rows.map((x, k) => k === i ? { ...x, label: e.target.value } : x))} className="w-44" />
            </div>))}</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button disabled={rows.length >= 8} onClick={() => setRows([...rows, { id: '', label: '' }])}>+ Passaggio</Button>
            <Button variant="primary" disabled={busy || rows.filter((r) => r.id).length < 2} onClick={() => run(async () => {
              const used = rows.filter((r) => r.id);
              const res = await api.transmission(used.map((r) => Number(r.id)), used.map((r) => r.label));
              setTrans(res.result);
              await saved.reload();
            })}>Analizza la catena</Button>
          </div>
          {templates.data?.map((t) => (
            <div key={t.id} className="mt-4 rounded-md border border-ink-700 p-3">
              <p className="text-sm text-paper">Modello: {t.title}</p>
              <p className="mb-2 text-xs text-steel-500">Serie reali da importare (richiedono la chiave FRED gratuita):</p>
              <ul className="space-y-1 text-xs">{t.steps.map((s) => (
                <li key={s.series_id} className="flex flex-wrap items-center gap-2 text-steel-300">{s.label} — FRED {s.series_id}
                  <button className="text-gold-300 hover:underline" onClick={() => run(async () => {
                    try { await api.importSeries({ connector: s.connector, series_id: s.series_id, category: 'other' }); setImp((x) => ({ ...x, [s.series_id]: 'importata' })); }
                    catch (e) { setImp((x) => ({ ...x, [s.series_id]: errorText(e) })); }
                    await series.reload();
                  })}>importa</button>{imp[s.series_id] && <span className="text-steel-500">{imp[s.series_id]}</span>}</li>))}</ul>
            </div>))}
          {trans && <div className="mt-4"><TransmissionView steps={trans.steps} notes={trans.notes} /></div>}
        </Card>
      </div>
      <SavedAnalyses list={saved.data?.filter((x) => x.kind !== 'foresight')} onOpen={(x) => x.kind === 'causal_chain' ? setChain(x.result as CausalChainResult) : setTrans(x.result as { steps: TransmissionStep[]; notes: string[] })} />
    </Shell>
  );
}

function SavedAnalyses({ list, onOpen }: { list?: DiscoveryAnalysis[]; onOpen: (a: DiscoveryAnalysis) => void }) {
  if (!list?.length) return null;
  return (
    <Card title="Analisi salvate" className="mt-4">
      <ul className="space-y-1">{list.slice(0, 20).map((x) => (
        <li key={x.id}><button className="text-left text-sm text-steel-300 hover:text-gold-300" onClick={() => onOpen(x)}>{x.title} <span className="text-xs text-steel-500">· {formatDateTime(x.created_at)}</span></button></li>))}</ul>
    </Card>
  );
}

// --- Strategic Foresight --------------------------------------------------------------------------

export function ForesightPage() {
  const series = useAsync(() => api.seriesList(), []);
  const saved = useAsync(() => api.discoveryAnalyses('foresight'), []);
  const [vars, setVars] = useState<{ id: string; favorable: 'up' | 'down' }[]>([{ id: '', favorable: 'up' }]);
  const [horizon, setHorizon] = useState('2');
  const [triggers, setTriggers] = useState('');
  const [res, setRes] = useState<ForesightResult>();
  const { busy, run, view } = useAction();
  const sopts = series.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>);
  return (
    <Shell title="Strategic Foresight" description="Tre scenari — ottimistico, centrale, avverso — dalle variazioni storiche delle serie scelte. Le bande sono percentili di un modello dichiarato, non probabilità degli scenari.">
      {view}
      <Card title="Variabili e orizzonte" className="mb-4">
        <div className="space-y-2">{vars.map((v, i) => (
          <div key={i} className="flex flex-wrap gap-2">
            <Select aria-label={`Variabile ${i + 1}`} value={v.id} onChange={(e) => setVars(vars.map((x, k) => k === i ? { ...x, id: e.target.value } : x))} className="min-w-56 flex-1"><option value="">— serie —</option>{sopts}</Select>
            <Select aria-label={`Direzione favorevole ${i + 1}`} value={v.favorable} onChange={(e) => setVars(vars.map((x, k) => k === i ? { ...x, favorable: e.target.value as 'up' | 'down' } : x))} className="w-auto">
              <option value="up">meglio se sale</option><option value="down">meglio se scende</option>
            </Select>
          </div>))}</div>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <Button disabled={vars.length >= 6} onClick={() => setVars([...vars, { id: '', favorable: 'up' }])}>+ Variabile</Button>
          <Field label="Orizzonte (anni)"><Input type="number" min={0.25} max={10} step={0.25} value={horizon} onChange={(e) => setHorizon(e.target.value)} className="w-28" /></Field>
          <Field label="Possibili eventi scatenanti (uno per riga, facoltativi)"><Textarea rows={2} value={triggers} onChange={(e) => setTriggers(e.target.value)} className="min-w-64" /></Field>
          <Button variant="primary" disabled={busy || !vars.some((v) => v.id)} onClick={() => run(async () => {
            const r = await api.foresight(vars.filter((v) => v.id).map((v) => ({ series_id: Number(v.id), favorable: v.favorable })), Number(horizon), triggers.split('\n').map((x) => x.trim()).filter(Boolean));
            setRes(r.result);
            await saved.reload();
          })}>Costruisci gli scenari</Button>
        </div>
        {series.data?.length === 0 && <EmptyState>Nessuna serie: importane almeno una (con 20 o più osservazioni) in Financial Intelligence.</EmptyState>}
      </Card>
      {res && <ForesightView r={res} />}
      <SavedAnalyses list={saved.data} onOpen={(x) => setRes(x.result as ForesightResult)} />
    </Shell>
  );
}

function ForesightView({ r }: { r: ForesightResult }) {
  const { busy, run, view } = useAction();
  const tone: Record<string, string> = { optimistic: 'border-ok/50', central: 'border-gold-500/60', adverse: 'border-bad/50' };
  return (
    <div className="space-y-4">
      {r.excluded.map((x) => <p key={x} className="text-sm text-warn">Esclusa: {x}</p>)}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {(['optimistic', 'central', 'adverse'] as const).map((k) => (
          <div key={k} className={`rounded-lg border bg-ink-900 p-4 ${tone[k]}`}>
            <p className="font-medium text-paper">{r.scenarios[k].title}</p>
            <p className="mb-2 text-xs text-steel-500">{r.scenarios[k].definition} · orizzonte {r.horizon_years} anni</p>
            <ul className="space-y-1 text-sm text-steel-300">{r.scenarios[k].values.map((v) => <li key={v}>{v}</li>)}</ul>
          </div>
        ))}
      </div>
      <Card title="Confronto delle variabili">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead><tr className="text-left text-xs text-steel-500 [&>th]:px-2"><th className="py-1 !pl-0">Variabile</th><th>Oggi</th><th>Ottimistico</th><th>Centrale</th><th>Avverso</th></tr></thead>
            <tbody>{r.variables.map((v) => (
              <tr key={v.series_id} className="border-t border-ink-700 text-steel-300 [&>td]:px-2 [&>td]:tabular-nums">
                <td className="py-1.5 !pl-0">{v.name} <span className="text-xs text-steel-500">({v.favorable === 'up' ? 'meglio se sale' : 'meglio se scende'})</span></td>
                <td>{formatNumber(v.initial.value)}</td><td>{formatNumber(v.optimistic)}</td><td>{formatNumber(v.central)}</td><td>{formatNumber(v.adverse)}</td>
              </tr>))}</tbody>
          </table>
        </div>
      </Card>
      {r.variables.map((v) => (
        <Card key={v.series_id} title={`${v.name} — ventaglio del modello`}>
          <TimeChart data={v.fan.map((f) => ({ date: `+${f.step}`, p10: f.p10, p50: f.p50, p90: f.p90 }))} unit={v.unit}
            series={[{ key: 'p90', label: '90° percentile', dashed: true }, { key: 'p50', label: 'Mediana' }, { key: 'p10', label: '10° percentile', dashed: true }]}
            ariaLabel={`Ventaglio degli scenari per ${v.name}`} />
          <p className="mt-1 text-xs text-steel-500">Asse orizzontale: periodi dopo l'ultimo dato ({v.initial.date}). Fonte dei dati storici: {v.source}.</p>
        </Card>
      ))}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Condizioni iniziali"><List items={r.initial_conditions} /></Card>
        <Card title="Possibili eventi scatenanti"><List items={r.triggers} /></Card>
        <Card title="Conseguenze (dal Knowledge Graph)">
          {r.consequences.length ? <ul className="space-y-1 text-sm text-steel-300">{r.consequences.map((c, i) => <li key={i}>{c.from} → {c.to} <Badge tone={c.documented ? 'ok' : 'gold'}>{c.documented ? 'documentata' : 'ipotesi'}</Badge></li>)}</ul>
            : <EmptyState>Nessuna relazione nel grafo parte da questi indicatori.</EmptyState>}
        </Card>
        <Card title="Indicatori da monitorare">
          <ul className="space-y-2 text-sm">{r.indicators_to_monitor.map((x) => {
            const v = r.variables.find((y) => y.series_id === x.series_id)!;
            const kind = v.favorable === 'up' ? 'below' : 'above';
            return (
              <li key={x.series_id} className="flex flex-wrap items-center justify-between gap-2 text-steel-300">
                <Link to={`/financial/series/${x.series_id}`} className="hover:text-gold-300">{x.name}</Link>
                <Button disabled={busy} onClick={() => run(() => api.createAlert({ series_id: x.series_id, kind, threshold: x.adverse_threshold }), `Avviso creato: notifica se «${x.name}» va ${kind === 'below' ? 'sotto' : 'sopra'} ${formatNumber(x.adverse_threshold)}.`)}>
                  Avvisami allo scenario avverso
                </Button>
              </li>);
          })}</ul>
          {view}
        </Card>
        <Card title="Incertezze e metodo" className="lg:col-span-2">
          <List items={r.uncertainties} />
          <p className="mt-2 text-xs text-steel-500">{r.method} {r.probability_note}</p>
        </Card>
      </div>
    </div>
  );
}

// --- Knowledge Graph --------------------------------------------------------------------------------

export function DiscoveryGraphPage() {
  return (
    <>
      <Tabs />
      <GraphPage />
    </>
  );
}
