import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { authErrorText, EMAIL_RX, passwordProblems, useAuth } from '../lib/auth';
import { getSupabase } from '../lib/supabase';
import { usePageMeta } from '../lib/meta';
import { useI18n } from '../lib/i18n';

const input = 'w-full rounded-xl border border-line bg-void px-4 py-3 text-[15px] text-ivory placeholder:text-mute focus:border-copper focus:outline-none';

function Shell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="grain relative flex min-h-[100svh] items-center justify-center bg-void px-5 pb-16 pt-28">
      <div className="w-full max-w-md">
        <h1 className="font-serif text-5xl leading-none">{title}</h1>
        <p className="mt-3 text-sm text-mute-2">{subtitle}</p>
        <div className="mt-8 rounded-2xl border border-line bg-coal p-6 sm:p-8">{children}</div>
      </div>
    </section>
  );
}

function NotConfigured() {
  const { t, p } = useI18n();
  return (
    <div role="status" className="space-y-4 text-sm leading-relaxed text-mute-2">
      <p><strong className="text-ivory">{t.auth.notActive}</strong> {t.auth.notActiveText}</p>
      <p>{t.auth.useLocal} <Link to={p('/#access')} className="text-copper underline-offset-4 hover:underline">{t.auth.seeHow}</Link>.</p>
    </div>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs text-mute-2">{label}</span>
      {children}
      {error && <span className="mt-1.5 block text-xs text-[#e8846a]">{error}</span>}
    </label>
  );
}

function Submit({ busy, children }: { busy: boolean; children: ReactNode }) {
  const { t } = useI18n();
  return <button type="submit" disabled={busy} className="w-full rounded-full bg-ivory py-3 text-sm font-medium text-void transition hover:bg-copper disabled:opacity-60">{busy ? t.auth.wait : children}</button>;
}

export function SignIn() {
  const { t, p } = useI18n();
  const a = t.auth;
  usePageMeta(a.signInTitle);
  const { configured, session } = useAuth();
  const nav = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? p('/account');
  const [f, setF] = useState({ email: '', password: '' });
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  if (session) return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const v: Record<string, string> = {};
    if (!EMAIL_RX.test(f.email.trim())) v.email = a.badEmail;
    if (!f.password) v.password = a.noPassword;
    setErr(v);
    const supabase = await getSupabase();
    if (Object.keys(v).length || !supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.signInWithPassword({ email: f.email.trim(), password: f.password });
    setBusy(false);
    if (error) setErr({ form: authErrorText(error.message, a.errors) });
    else nav(from, { replace: true });
  }

  return (
    <Shell title={a.signInTitle} subtitle={a.signInSub}>
      {!configured ? <NotConfigured /> : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label={a.email} error={err.email}><input className={input} type="email" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label={a.password} error={err.password}><input className={input} type="password" autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          {err.form && <p role="alert" className="text-sm text-[#e8846a]">{err.form}</p>}
          <Submit busy={busy}>{a.signInTitle}</Submit>
          <div className="flex justify-between text-xs">
            <Link to={p('/forgot-password')} className="text-mute-2 hover:text-ivory">{a.forgot}</Link>
            <Link to={p('/signup')} className="text-copper hover:underline">{a.createAccount}</Link>
          </div>
        </form>
      )}
    </Shell>
  );
}

export function SignUp() {
  const { t, p } = useI18n();
  const a = t.auth;
  usePageMeta(a.createAccount);
  const { configured, session } = useAuth();
  const [f, setF] = useState({ email: '', password: '', confirm: '' });
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  if (session) return <Navigate to={p('/account')} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const v: Record<string, string> = {};
    if (!EMAIL_RX.test(f.email.trim())) v.email = a.badEmail;
    const probs = passwordProblems(f.password, a.pwProblems);
    if (probs.length) v.password = a.pwNeeds(probs);
    if (f.confirm !== f.password) v.confirm = a.mismatch;
    setErr(v);
    const supabase = await getSupabase();
    if (Object.keys(v).length || !supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.signUp({ email: f.email.trim(), password: f.password, options: { emailRedirectTo: `${window.location.origin}${p('/account')}` } });
    setBusy(false);
    if (error) setErr({ form: authErrorText(error.message, a.errors) });
    else setDone(true);
  }

  return (
    <Shell title={a.createAccount} subtitle={a.signUpSub}>
      {!configured ? <NotConfigured /> : done ? (
        <p role="status" className="text-sm leading-relaxed text-mute-2"><strong className="block text-ivory">{a.inbox}</strong> {a.inboxText(f.email)}</p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label={a.email} error={err.email}><input className={input} type="email" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label={a.pwHint} error={err.password}><input className={input} type="password" autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          <Field label={a.confirm} error={err.confirm}><input className={input} type="password" autoComplete="new-password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></Field>
          {err.form && <p role="alert" className="text-sm text-[#e8846a]">{err.form}</p>}
          <Submit busy={busy}>{a.createAccount}</Submit>
          <p className="text-center text-xs text-mute-2">{a.already} <Link to={p('/signin')} className="text-copper hover:underline">{a.signInTitle}</Link></p>
        </form>
      )}
    </Shell>
  );
}

export function ForgotPassword() {
  const { t, p } = useI18n();
  const a = t.auth;
  usePageMeta(a.resetTitle);
  const { configured } = useAuth();
  const [email, setEmail] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!EMAIL_RX.test(email.trim())) return setErr(a.badEmail);
    const supabase = await getSupabase();
    if (!supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: `${window.location.origin}${p('/reset-password')}` });
    setBusy(false);
    if (error) setErr(authErrorText(error.message, a.errors));
    else setSent(true);
  }

  return (
    <Shell title={a.resetTitle} subtitle={a.resetSub}>
      {!configured ? <NotConfigured /> : sent ? (
        <p role="status" className="text-sm leading-relaxed text-mute-2">{a.resetSent(email)}</p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label={a.email} error={err}><input className={input} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Submit busy={busy}>{a.sendLink}</Submit>
          <p className="text-center text-xs"><Link to={p('/signin')} className="text-mute-2 hover:text-ivory">{a.backSignIn}</Link></p>
        </form>
      )}
    </Shell>
  );
}

export function ResetPassword() {
  const { t, p } = useI18n();
  const a = t.auth;
  usePageMeta(a.newMeta);
  const { configured, session, loading } = useAuth();
  const nav = useNavigate();
  const [pw, setPw] = useState({ a: '', b: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const probs = passwordProblems(pw.a, a.pwProblems);
    if (probs.length) return setErr(a.pwNeeds(probs));
    if (pw.a !== pw.b) return setErr(a.mismatch);
    const supabase = await getSupabase();
    if (!supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password: pw.a });
    setBusy(false);
    if (error) setErr(authErrorText(error.message, a.errors));
    else nav(p('/account'), { replace: true });
  }

  return (
    <Shell title={a.newTitle} subtitle={a.newSub}>
      {!configured ? <NotConfigured /> : loading ? <p className="text-sm text-mute-2">{a.checking}</p> : !session ? (
        <p role="alert" className="text-sm leading-relaxed text-mute-2">{a.invalidLink} <Link to={p('/forgot-password')} className="text-copper hover:underline">{a.requestNew}</Link>.</p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label={a.newPw}><input className={input} type="password" autoComplete="new-password" value={pw.a} onChange={(e) => setPw({ ...pw, a: e.target.value })} /></Field>
          <Field label={a.confirmNew}><input className={input} type="password" autoComplete="new-password" value={pw.b} onChange={(e) => setPw({ ...pw, b: e.target.value })} /></Field>
          {err && <p role="alert" className="text-sm text-[#e8846a]">{err}</p>}
          <Submit busy={busy}>{a.save}</Submit>
        </form>
      )}
    </Shell>
  );
}

/** Protegge le pagine riservate: senza sessione rimanda all'accesso. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { configured, session, loading } = useAuth();
  const { pathname } = useLocation();
  const { t, p } = useI18n();
  if (!configured) return <Navigate to={p('/signin')} replace />;
  if (loading) return <div className="min-h-[100svh] bg-void pt-40 text-center text-sm text-mute">{t.auth.loading}</div>;
  if (!session) return <Navigate to={p('/signin')} replace state={{ from: pathname }} />;
  return <>{children}</>;
}

export function Account() {
  const { t, p } = useI18n();
  const a = t.auth;
  usePageMeta(a.accountTitle);
  const { session } = useAuth();
  const nav = useNavigate();
  return (
    <Shell title={a.accountTitle} subtitle={session?.user.email ?? ''}>
      <div className="space-y-5 text-sm leading-relaxed text-mute-2">
        <p>{a.accountText}</p>
        <Link to={p('/#access')} className="block rounded-full border border-line py-3 text-center text-ivory hover:border-ivory">{a.howRun}</Link>
        <button onClick={async () => { await (await getSupabase())?.auth.signOut(); nav(p('/'), { replace: true }); }} className="w-full rounded-full bg-ivory py-3 font-medium text-void hover:bg-copper">{a.signOut}</button>
      </div>
    </Shell>
  );
}
