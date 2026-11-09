import { createContext, useCallback, useContext, useEffect, useState, type FormEvent, type ReactNode } from 'react';
import type { SupabaseClient } from '@supabase/supabase-js';
import { api, setTokenProvider, type AuthConfig } from '../api/client';
import type { User } from '../api/types';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/Form';
import { errorText } from '../lib/forms';

interface AuthState {
  mode: AuthConfig['mode'];
  user: User | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  siteUrl?: string | null;
  /** Sessione della demo pubblica in sola lettura. */
  isDemo?: boolean;
  demoLang?: 'it' | 'en';
}
const Ctx = createContext<AuthState>({ mode: 'local', user: null, refresh: async () => {}, logout: async () => {} });
export const useAuth = () => useContext(Ctx);

// --- Demo pubblica (senza account): token firmato dal server, valido alcune ore ---------------
const DEMO_KEY = 'nexus.demo';

export function readDemoToken(): string | null {
  try {
    const raw = localStorage.getItem(DEMO_KEY);
    if (!raw) return null;
    const { token, expires_at } = JSON.parse(raw) as { token: string; expires_at: string };
    if (!token || Date.parse(expires_at) <= Date.now()) {
      localStorage.removeItem(DEMO_KEY);
      return null;
    }
    return token;
  } catch {
    return null;
  }
}

export function readDemoLang(): 'it' | 'en' {
  try {
    const raw = localStorage.getItem(DEMO_KEY);
    return raw && (JSON.parse(raw) as { lang?: string }).lang === 'en' ? 'en' : 'it';
  } catch {
    return 'it';
  }
}

function saveDemoToken(v: { token: string; expires_at: string; lang?: 'it' | 'en' } | null) {
  try {
    if (v) localStorage.setItem(DEMO_KEY, JSON.stringify(v));
    else localStorage.removeItem(DEMO_KEY);
  } catch {
    /* storage non disponibile: la demo dura finché la pagina resta aperta */
  }
}

/** ?demo=1 (o ?demo=it) apre la demo italiana, ?demo=en quella inglese. */
function wantsDemo(): 'it' | 'en' | null {
  if (typeof window === 'undefined') return null;
  const v = new URLSearchParams(window.location.search).get('demo');
  return v === 'en' ? 'en' : v === '1' || v === 'it' ? 'it' : null;
}

function DemoButton({ onStart }: { onStart: (lang?: 'it' | 'en') => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  return (
    <div className="space-y-2 border-t border-ink-700 pt-4">
      <Button type="button" className="w-full" disabled={busy} onClick={async () => {
        setBusy(true);
        setErr(undefined);
        try {
          await onStart();
        } catch (x) {
          setErr(errorText(x));
        } finally {
          setBusy(false);
        }
      }}>
        {busy ? 'Apertura della demo…' : 'Prova la demo senza account'}
      </Button>
      <p className="text-center text-[11px] text-steel-500">
        Un progetto di esempio sulla Grande Depressione 1929–1933, in sola lettura. ·{' '}
        <button type="button" className="text-gold-300 hover:underline" disabled={busy} onClick={() => { setBusy(true); onStart('en').catch((x) => setErr(errorText(x))).finally(() => setBusy(false)); }}>English demo</button>
      </p>
      {err && <p role="alert" className="text-sm text-bad">{err}</p>}
    </div>
  );
}

/** Mostrato mentre il server si avvia: sul piano gratuito il primo accesso può richiedere fino a un minuto. */
function StartingScreen() {
  const en = wantsDemo() === 'en' || readDemoLang() === 'en' && readDemoToken() !== null;
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setSlow(true), 2500);
    return () => clearTimeout(t);
  }, []);
  return (
    <div className="flex min-h-full items-center justify-center p-4" role="status" aria-live="polite">
      <div className="max-w-sm text-center">
        <p className="text-lg font-semibold tracking-[0.3em] text-gold-400">NEXUS</p>
        <div className="mx-auto mt-4 size-6 animate-spin rounded-full border-2 border-ink-700 border-t-gold-400" aria-hidden />
        <p className="mt-4 text-sm text-steel-300">{slow ? (en ? 'Starting the server…' : 'Avvio del server in corso…') : en ? 'Loading…' : 'Caricamento…'}</p>
        {slow && <p className="mt-1 text-xs text-steel-500">{en
          ? "If NEXUS hasn't been used for a while, the first start can take up to a minute. Please keep this page open."
          : "Se NEXUS non veniva usato da un po', il primo avvio può richiedere fino a un minuto. Non chiudere la pagina."}</p>}
      </div>
    </div>
  );
}

function LoginScreen({ allowRegistration, onDone }: { allowRegistration: boolean; onDone: () => Promise<void> }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [f, setF] = useState({ email: '', password: '', name: '' });
  const [err, setErr] = useState<string>();
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(undefined);
    try {
      if (mode === 'login') await api.login(f.email, f.password);
      else await api.register(f.email, f.password, f.name);
      await onDone();
    } catch (x) {
      setErr(errorText(x));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-lg border border-ink-700 bg-ink-900 p-6">
        <div>
          <p className="text-lg font-semibold tracking-[0.3em] text-gold-400">NEXUS</p>
          <h1 className="mt-1 text-sm text-steel-300">{mode === 'login' ? 'Accedi al tuo account' : 'Crea un account'}</h1>
        </div>
        {mode === 'register' && <Field label="Nome"><Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} autoComplete="name" /></Field>}
        <Field label="Email"><Input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} autoComplete="email" required /></Field>
        <Field label="Password" hint={mode === 'register' ? 'Almeno 10 caratteri, con lettere e numeri o simboli.' : undefined}>
          <Input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required />
        </Field>
        {err && <p role="alert" className="text-sm text-bad">{err}</p>}
        <Button type="submit" variant="primary" className="w-full" disabled={busy}>{mode === 'login' ? 'Accedi' : 'Registrati'}</Button>
        {allowRegistration && (
          <button type="button" className="w-full text-xs text-gold-300 hover:underline" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
            {mode === 'login' ? 'Non hai un account? Registrati' : 'Hai già un account? Accedi'}
          </button>
        )}
      </form>
    </div>
  );
}

/** Versione online: accesso con l'account del sito NEXUS (Supabase). Registrazione e recupero password sul sito. */
function SupabaseLoginScreen({ client, siteUrl, onDone, onDemo }: { client: SupabaseClient; siteUrl?: string | null; onDone: () => Promise<void>; onDemo?: (lang?: 'it' | 'en') => Promise<void> }) {
  const [f, setF] = useState({ email: '', password: '' });
  const [err, setErr] = useState<string>();
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(undefined);
    const { error } = await client.auth.signInWithPassword({ email: f.email.trim(), password: f.password });
    if (error) {
      const m = error.message.toLowerCase();
      setErr(m.includes('invalid login') ? 'Email o password non corretti.' : m.includes('not confirmed') ? 'Conferma prima il tuo indirizzo email.' : error.message);
      setBusy(false);
      return;
    }
    saveDemoToken(null);
    await onDone();
    setBusy(false);
  }
  const site = siteUrl?.replace(/\/+$/, '');
  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-lg border border-ink-700 bg-ink-900 p-6">
        <div>
          <p className="text-lg font-semibold tracking-[0.3em] text-gold-400">NEXUS</p>
          <h1 className="mt-1 text-sm text-steel-300">Accedi con il tuo account NEXUS</h1>
          <p className="mt-1 text-xs text-steel-500">Lo stesso account del sito.</p>
        </div>
        <Field label="Email"><Input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} autoComplete="email" required /></Field>
        <Field label="Password"><Input type="password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} autoComplete="current-password" required /></Field>
        {err && <p role="alert" className="text-sm text-bad">{err}</p>}
        <Button type="submit" variant="primary" className="w-full" disabled={busy}>Accedi</Button>
        {site && (
          <div className="flex justify-between text-xs">
            <a className="text-steel-400 hover:text-paper" href={`${site}/forgot-password`}>Password dimenticata?</a>
            <a className="text-gold-300 hover:underline" href={`${site}/signup`}>Crea un account</a>
          </div>
        )}
        {onDemo && <DemoButton onStart={onDemo} />}
        {site && <p className="text-center text-[11px] text-steel-500"><a className="hover:text-paper hover:underline" href={`${site}/it/privacy`}>Informativa privacy</a></p>}
      </form>
    </div>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AuthConfig>();
  const [supa, setSupa] = useState<SupabaseClient>();
  const [user, setUser] = useState<User | null>(null);
  const [checked, setChecked] = useState(false);
  const [isDemo, setIsDemo] = useState(() => readDemoToken() !== null);
  const [demoLang, setDemoLang] = useState<'it' | 'en'>(readDemoLang);

  const refresh = useCallback(async () => {
    try {
      setUser(await api.me());
    } catch {
      setUser(null);
    } finally {
      setChecked(true);
    }
  }, []);

  useEffect(() => {
    api.authConfig().then(async (cfg) => {
      let signedIn = false;
      if (cfg.mode === 'supabase' && cfg.supabase_url && cfg.supabase_anon_key) {
        const { createClient } = await import('@supabase/supabase-js');
        const client = createClient(cfg.supabase_url, cfg.supabase_anon_key, { auth: { persistSession: true, autoRefreshToken: true } });
        setTokenProvider(async () => readDemoToken() ?? (await client.auth.getSession()).data.session?.access_token ?? null);
        client.auth.onAuthStateChange((event) => {
          if (event === 'SIGNED_OUT') setUser(null);
        });
        setSupa(client);
        signedIn = !!(await client.auth.getSession()).data.session;
      } else if (cfg.mode === 'multi') {
        setTokenProvider(async () => readDemoToken());
      }
      setConfig(cfg);
      const want = wantsDemo();
      if (cfg.demo && want && !signedIn && (!readDemoToken() || readDemoLang() !== want)) {
        try {
          saveDemoToken(await api.openDemo(want));
        } catch {
          /* se la demo non si apre resta la schermata di accesso */
        }
      }
      if (wantsDemo()) {
        const url = new URL(window.location.href);
        url.searchParams.delete('demo');
        window.history.replaceState(null, '', url.pathname + url.search + url.hash);
      }
      setIsDemo(readDemoToken() !== null);
      setDemoLang(readDemoLang());
      await refresh();
    }).catch(() => {
      setConfig({ mode: 'local', allow_registration: false });
      void refresh();
    });
    const onUnauthorized = () => setUser(null);
    window.addEventListener('nexus:unauthorized', onUnauthorized);
    return () => window.removeEventListener('nexus:unauthorized', onUnauthorized);
  }, [refresh]);

  const startDemo = useCallback(async (lang: 'it' | 'en' = 'it') => {
    saveDemoToken(await api.openDemo(lang));
    setIsDemo(true);
    setDemoLang(lang);
    await refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    if (readDemoToken()) {
      saveDemoToken(null);
      setIsDemo(false);
      setUser(null);
      return;
    }
    if (supa) await supa.auth.signOut();
    else await api.logout().catch(() => undefined);
    setUser(null);
  }, [supa]);

  const mode = config?.mode ?? 'local';
  // Prima di conoscere la modalità non si chiede nulla al server (online servirebbe già il token).
  if (!config || (mode !== 'local' && !checked)) return <StartingScreen />;
  if (mode === 'supabase' && checked && !user) {
    if (!supa) return <div className="p-6 text-sm text-bad">Accesso online non configurato sul server.</div>;
    return <SupabaseLoginScreen client={supa} siteUrl={config?.site_url} onDone={refresh} onDemo={config.demo ? startDemo : undefined} />;
  }
  if (mode === 'multi' && checked && !user) return <LoginScreen allowRegistration={config?.allow_registration ?? false} onDone={refresh} />;
  return <Ctx.Provider value={{ mode, user, refresh, logout, siteUrl: config?.site_url, isDemo: isDemo && !!user, demoLang }}>{children}</Ctx.Provider>;
}
