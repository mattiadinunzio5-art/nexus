import { api } from '../api/client';
import { CredentialsPanel } from '../components/Credentials';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useState } from 'react';
import { errorText } from '../lib/forms';
import { Button } from '../components/ui/Button';
import { Input, Select } from '../components/ui/Form';
import { useAuth } from '../state/Auth';

export function SettingsPage() {
  const status = useAsync(() => api.systemStatus(), []);
  const ai = useAsync(() => api.aiStatus(), []);
  const { user } = useAuth();
  const s = status.data;
  return (
    <>
      <PageHeader eyebrow="Workspace" title="System" description="Stato del backend, del database e dei provider AI." />
      {status.loading && !s && <Loading />}
      {status.error && <ErrorBox error={status.error} onRetry={status.reload} />}
      {s && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card title="Backend e database">
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-steel-500">Versione</dt>
              <dd className="text-paper">{s.version}</dd>
              <dt className="text-steel-500">Ambiente</dt>
              <dd className="text-paper">{s.environment}</dd>
              <dt className="text-steel-500">Database</dt>
              <dd className="text-paper">
                {s.database} <Badge tone={s.database_ok ? 'ok' : 'bad'}>{s.database_ok ? 'operativo' : 'errore'}</Badge>
              </dd>
              <dt className="text-steel-500">Ora del server</dt>
              <dd className="text-paper">{formatDateTime(s.server_time)}</dd>
            </dl>
          </Card>
          <Card title="Provider AI">
            <p className="mb-3 text-sm text-steel-300">
              Provider attivo: <span className="text-paper">{s.ai_provider.name}</span>. I provider esterni vengono usati solo
              se configurati da te nelle credenziali qui sotto.
            </p>
            {ai.data?.shared && (
              <p role="status" className="mb-3 rounded-md border border-gold-500/40 bg-gold-500/5 p-2 text-sm text-steel-300">
                Stai usando l'<span className="text-paper">AI condivisa della piattaforma</span>: {ai.data.used_today ?? 0} richieste su {ai.data.daily_limit} oggi.
                Se scegli un tuo provider qui sotto, userai quello.
              </p>
            )}
            <ProviderSelector key={ai.data?.shared ? 'platform' : s.ai_provider.id} current={ai.data?.shared ? 'platform' : s.ai_provider.id} shared={!!ai.data?.shared_available} onChange={() => { status.reload(); ai.reload(); }} />
            <ul className="divide-y divide-ink-700">
              {s.ai_providers.map((p) => (
                <li key={p.id} className="flex flex-wrap items-start gap-2 py-2 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="text-paper">{p.name}</p>
                    <p className="text-xs text-steel-500">{p.notes}</p>
                  </div>
                  <Badge tone={p.id === s.ai_provider.id ? 'ok' : 'neutral'}>{p.id === s.ai_provider.id ? 'In uso' : p.requires_credentials ? 'Richiede credenziali' : 'Disponibile'}</Badge>
                </li>
              ))}
            </ul>
          </Card>
          {user?.role === 'admin' && <PlatformAI onChange={() => { status.reload(); ai.reload(); }} />}
          <Card title="Credenziali dei servizi esterni" className="lg:col-span-2">
            <CredentialsPanel />
          </Card>
        </div>
      )}
    </>
  );
}

function PlatformAI({ onChange }: { onChange: () => void }) {
  const cfg = useAsync(() => api.aiPlatform(), []);
  const [form, setForm] = useState<{ enabled: boolean; provider: string; daily_limit: string }>();
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const f = form ?? (cfg.data ? { ...cfg.data, daily_limit: String(cfg.data.daily_limit) } : undefined);
  return (
    <Card title="AI per tutti gli utenti (amministratore)" className="lg:col-span-2">
      <p className="mb-3 text-sm text-steel-300">
        Condividi il tuo provider AI: chi non ne ha configurato uno userà il tuo, con un limite giornaliero di richieste a testa.
        La chiave resta sul server e non viene mai mostrata agli utenti; i costi del provider sono a tuo carico.
      </p>
      {!f ? <Loading /> : (
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex items-center gap-2 text-sm text-steel-300">
            <input type="checkbox" checked={f.enabled} onChange={(e) => setForm({ ...f, enabled: e.target.checked })} /> Attiva per tutti
          </label>
          <Select aria-label="Provider condiviso" className="w-auto" value={f.provider} onChange={(e) => setForm({ ...f, provider: e.target.value })}>
            <option value="anthropic">Anthropic API</option>
            <option value="openai-compatible">Endpoint compatibile OpenAI</option>
            <option value="ollama">Ollama</option>
          </Select>
          <label className="text-sm text-steel-300">Richieste al giorno per utente
            <Input aria-label="Richieste al giorno per utente" inputMode="numeric" className="mt-1 w-28" value={f.daily_limit} onChange={(e) => setForm({ ...f, daily_limit: e.target.value })} />
          </label>
          <Button variant="primary" onClick={async () => {
            setMsg(undefined);
            const n = Number(f.daily_limit);
            if (!Number.isInteger(n) || n < 1) return setMsg({ ok: false, text: 'Indica un numero intero di richieste (almeno 1).' });
            try {
              const r = await api.setAiPlatform({ enabled: f.enabled, provider: f.provider, daily_limit: n });
              setMsg({ ok: true, text: r.enabled ? 'AI condivisa attiva per tutti gli utenti.' : 'AI condivisa disattivata.' });
              onChange();
            } catch (e) { setMsg({ ok: false, text: errorText(e) }); }
          }}>Salva</Button>
          {msg && <p role={msg.ok ? 'status' : 'alert'} className={`w-full text-sm ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
        </div>
      )}
    </Card>
  );
}

function ProviderSelector({ current, shared, onChange }: { current: string; shared: boolean; onChange: () => void }) {
  const [provider, setProvider] = useState(current);
  const [effort, setEffort] = useState('medium');
  const [err, setErr] = useState<string>();
  return (
    <div className="mb-3 flex flex-wrap items-end gap-2">
      <Select aria-label="Provider AI" className="w-auto" value={provider} onChange={(e) => setProvider(e.target.value)}>
        {shared && <option value="platform">AI condivisa della piattaforma</option>}
        <option value="none">Nessuno (modalità locale)</option>
        <option value="ollama">Ollama (locale)</option>
        <option value="openai-compatible">Endpoint compatibile OpenAI</option>
        <option value="anthropic">Anthropic API</option>
      </Select>
      {provider === 'anthropic' && (
        <Select aria-label="Effort" className="w-auto" value={effort} onChange={(e) => setEffort(e.target.value)}>
          {['low', 'medium', 'high', 'xhigh', 'max'].map((x) => <option key={x}>{x}</option>)}
        </Select>
      )}
      <Button onClick={async () => { setErr(undefined); try { if (provider === 'platform') await api.usePlatformAI(); else await api.selectProvider(provider, effort); onChange(); } catch (e) { setErr(errorText(e)); } }}>Usa</Button>
      {err && <p role="alert" className="w-full text-sm text-bad">{err}</p>}
    </div>
  );
}
