import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { api } from '../api/client';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Field, Input, Select } from './ui/Form';

/** Collega il proprio account Gemini, ChatGPT, Grok o Claude con una chiave API, in tre passi. */
export function AIAccountCard({ onChange }: { onChange: () => void }) {
  const services = useAsync(() => api.aiAccounts(), []);
  const creds = useAsync(() => api.credentials(), []);
  const [sid, setSid] = useState('');
  const [key, setKey] = useState('');
  const [models, setModels] = useState<string[]>();
  const [model, setModel] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  const svc = services.data?.find((s) => s.id === sid);
  const linked = creds.data?.find((c) => c.configured && c.config.service);
  const linkedName = linked && services.data?.find((s) => s.id === linked.config.service)?.name;
  const reset = (id: string) => { setSid(id); setKey(''); setModels(undefined); setModel(''); setMsg(undefined); };

  return (
    <Card title="Collega il tuo account AI" className="lg:col-span-2">
      <p className="mb-3 text-sm text-steel-300">
        Usa il tuo account Gemini, ChatGPT, Grok o Claude per le funzioni AI di NEXUS. Serve una <span className="text-paper">chiave API</span> dalla
        console sviluppatori del servizio: gli abbonamenti delle app (ChatGPT Plus, Claude Pro, Gemini, SuperGrok) non si possono collegare ad altre applicazioni.
      </p>
      {linked && <p role="status" className="mb-3 text-sm text-ok">Collegato: {linkedName ?? linked.config.service} · {linked.config.model} <Badge>{linked.hint}</Badge></p>}
      <div className="mb-3 flex flex-wrap gap-2" role="radiogroup" aria-label="Servizio AI">
        {services.data?.map((s) => (
          <button key={s.id} type="button" role="radio" aria-checked={sid === s.id} onClick={() => reset(s.id)}
            className={`rounded-md border px-3 py-1.5 text-sm ${sid === s.id ? 'border-gold-500 bg-ink-800 text-paper' : 'border-ink-600 text-steel-300 hover:text-paper'}`}>{s.name}</button>
        ))}
      </div>
      {svc && (
        <ol className="space-y-3 text-sm">
          <li>
            <span className="text-steel-400">1.</span> Crea una chiave su{' '}
            <a href={svc.key_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-gold-300 hover:underline">{svc.key_url.replace('https://', '')} <ExternalLink className="size-3" aria-hidden /></a>
            <span className="block text-[11px] text-steel-500">{svc.free}</span>
          </li>
          <li className="flex flex-wrap items-end gap-2">
            <Field label="2. Incolla la chiave API" className="min-w-64 flex-1">
              <Input type="password" autoComplete="off" value={key} onChange={(e) => { setKey(e.target.value); setModels(undefined); }} />
            </Field>
            <Button disabled={!key.trim() || busy} onClick={async () => {
              setBusy(true); setMsg(undefined);
              try {
                const m = await api.aiAccountModels(svc.id, key);
                setModels(m); setModel(m[0] ?? '');
                if (!m.length) setMsg({ ok: false, text: 'La chiave funziona, ma non risultano modelli di testo disponibili per il tuo account.' });
              } catch (e) { setMsg({ ok: false, text: errorText(e) }); } finally { setBusy(false); }
            }}>{busy && !models ? 'Verifica…' : 'Verifica la chiave'}</Button>
          </li>
          {models && models.length > 0 && (
            <li className="flex flex-wrap items-end gap-2">
              <Field label="3. Scegli il modello" className="min-w-64">
                <Select value={model} onChange={(e) => setModel(e.target.value)}>{models.map((m) => <option key={m} value={m}>{m}</option>)}</Select>
              </Field>
              <Button variant="primary" disabled={!model || busy} onClick={async () => {
                setBusy(true); setMsg(undefined);
                try {
                  const r = await api.connectAiAccount(svc.id, key, model);
                  setMsg({ ok: true, text: `${r.name} collegato: le funzioni AI useranno ${r.model}.` });
                  setKey(''); setModels(undefined); creds.reload(); onChange();
                } catch (e) { setMsg({ ok: false, text: errorText(e) }); } finally { setBusy(false); }
              }}>Collega e usa</Button>
            </li>
          )}
        </ol>
      )}
      {msg && <p role={msg.ok ? 'status' : 'alert'} className={`mt-3 text-sm ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
      <p className="mt-3 text-[11px] text-steel-500">La chiave è cifrata sul server e non viene più mostrata. I costi d'uso li addebita il servizio sul tuo account. Puoi scollegarla in «Credenziali».</p>
    </Card>
  );
}
