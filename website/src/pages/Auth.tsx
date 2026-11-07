import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { authErrorText, EMAIL_RX, passwordProblems, useAuth } from '../lib/auth';
import { getSupabase } from '../lib/supabase';
import { usePageMeta } from '../lib/meta';

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
  return (
    <div role="status" className="space-y-4 text-sm leading-relaxed text-mute-2">
      <p><strong className="text-ivory">Online accounts are not active yet.</strong> The authentication service has not been configured for this site, so no sign-in can take place here.</p>
      <p>You can already use NEXUS on your own computer — <Link to="/#access" className="text-copper underline-offset-4 hover:underline">see how</Link>.</p>
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
  return <button type="submit" disabled={busy} className="w-full rounded-full bg-ivory py-3 text-sm font-medium text-void transition hover:bg-copper disabled:opacity-60">{busy ? 'Please wait…' : children}</button>;
}

export function SignIn() {
  usePageMeta('Sign in');
  const { configured, session } = useAuth();
  const nav = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/account';
  const [f, setF] = useState({ email: '', password: '' });
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  if (session) return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const v: Record<string, string> = {};
    if (!EMAIL_RX.test(f.email.trim())) v.email = 'Enter a valid email address.';
    if (!f.password) v.password = 'Enter your password.';
    setErr(v);
    const supabase = await getSupabase();
    if (Object.keys(v).length || !supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.signInWithPassword({ email: f.email.trim(), password: f.password });
    setBusy(false);
    if (error) setErr({ form: authErrorText(error.message) });
    else nav(from, { replace: true });
  }

  return (
    <Shell title="Sign in" subtitle="Welcome back to NEXUS.">
      {!configured ? <NotConfigured /> : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label="Email" error={err.email}><input className={input} type="email" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Password" error={err.password}><input className={input} type="password" autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          {err.form && <p role="alert" className="text-sm text-[#e8846a]">{err.form}</p>}
          <Submit busy={busy}>Sign in</Submit>
          <div className="flex justify-between text-xs">
            <Link to="/forgot-password" className="text-mute-2 hover:text-ivory">Forgot password?</Link>
            <Link to="/signup" className="text-copper hover:underline">Create account</Link>
          </div>
        </form>
      )}
    </Shell>
  );
}

export function SignUp() {
  usePageMeta('Create account');
  const { configured, session } = useAuth();
  const [f, setF] = useState({ email: '', password: '', confirm: '' });
  const [err, setErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  if (session) return <Navigate to="/account" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    const v: Record<string, string> = {};
    if (!EMAIL_RX.test(f.email.trim())) v.email = 'Enter a valid email address.';
    const p = passwordProblems(f.password);
    if (p.length) v.password = `Password needs ${p.join(' and ')}.`;
    if (f.confirm !== f.password) v.confirm = 'Passwords do not match.';
    setErr(v);
    const supabase = await getSupabase();
    if (Object.keys(v).length || !supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.signUp({ email: f.email.trim(), password: f.password, options: { emailRedirectTo: `${window.location.origin}/account` } });
    setBusy(false);
    if (error) setErr({ form: authErrorText(error.message) });
    else setDone(true);
  }

  return (
    <Shell title="Create account" subtitle="Join NEXUS.">
      {!configured ? <NotConfigured /> : done ? (
        <p role="status" className="text-sm leading-relaxed text-mute-2"><strong className="block text-ivory">Check your inbox.</strong> If email confirmation is enabled, we sent a link to <span className="text-ivory">{f.email}</span>. Open it to activate your account, then sign in.</p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label="Email" error={err.email}><input className={input} type="email" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label="Password (min. 10 characters, letters and numbers or symbols)" error={err.password}><input className={input} type="password" autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          <Field label="Confirm password" error={err.confirm}><input className={input} type="password" autoComplete="new-password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></Field>
          {err.form && <p role="alert" className="text-sm text-[#e8846a]">{err.form}</p>}
          <Submit busy={busy}>Create account</Submit>
          <p className="text-center text-xs text-mute-2">Already registered? <Link to="/signin" className="text-copper hover:underline">Sign in</Link></p>
        </form>
      )}
    </Shell>
  );
}

export function ForgotPassword() {
  usePageMeta('Reset password');
  const { configured } = useAuth();
  const [email, setEmail] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!EMAIL_RX.test(email.trim())) return setErr('Enter a valid email address.');
    const supabase = await getSupabase();
    if (!supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: `${window.location.origin}/reset-password` });
    setBusy(false);
    if (error) setErr(authErrorText(error.message));
    else setSent(true);
  }

  return (
    <Shell title="Reset password" subtitle="We will email you a link to choose a new password.">
      {!configured ? <NotConfigured /> : sent ? (
        <p role="status" className="text-sm leading-relaxed text-mute-2">If an account exists for <span className="text-ivory">{email}</span>, a reset link is on its way.</p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label="Email" error={err}><input className={input} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Submit busy={busy}>Send reset link</Submit>
          <p className="text-center text-xs"><Link to="/signin" className="text-mute-2 hover:text-ivory">Back to sign in</Link></p>
        </form>
      )}
    </Shell>
  );
}

export function ResetPassword() {
  usePageMeta('Choose a new password');
  const { configured, session, loading } = useAuth();
  const nav = useNavigate();
  const [pw, setPw] = useState({ a: '', b: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const p = passwordProblems(pw.a);
    if (p.length) return setErr(`Password needs ${p.join(' and ')}.`);
    if (pw.a !== pw.b) return setErr('Passwords do not match.');
    const supabase = await getSupabase();
    if (!supabase) return;
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password: pw.a });
    setBusy(false);
    if (error) setErr(authErrorText(error.message));
    else nav('/account', { replace: true });
  }

  return (
    <Shell title="New password" subtitle="Choose a new password for your account.">
      {!configured ? <NotConfigured /> : loading ? <p className="text-sm text-mute-2">Checking your reset link…</p> : !session ? (
        <p role="alert" className="text-sm leading-relaxed text-mute-2">This reset link is invalid or has expired. <Link to="/forgot-password" className="text-copper hover:underline">Request a new one</Link>.</p>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5">
          <Field label="New password"><input className={input} type="password" autoComplete="new-password" value={pw.a} onChange={(e) => setPw({ ...pw, a: e.target.value })} /></Field>
          <Field label="Confirm new password"><input className={input} type="password" autoComplete="new-password" value={pw.b} onChange={(e) => setPw({ ...pw, b: e.target.value })} /></Field>
          {err && <p role="alert" className="text-sm text-[#e8846a]">{err}</p>}
          <Submit busy={busy}>Save password</Submit>
        </form>
      )}
    </Shell>
  );
}

/** Protegge le pagine riservate: senza sessione rimanda all'accesso. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { configured, session, loading } = useAuth();
  const { pathname } = useLocation();
  if (!configured) return <Navigate to="/signin" replace />;
  if (loading) return <div className="min-h-[100svh] bg-void pt-40 text-center text-sm text-mute">Loading…</div>;
  if (!session) return <Navigate to="/signin" replace state={{ from: pathname }} />;
  return <>{children}</>;
}

export function Account() {
  usePageMeta('Your account');
  const { session } = useAuth();
  const nav = useNavigate();
  return (
    <Shell title="Your account" subtitle={session?.user.email ?? ''}>
      <div className="space-y-5 text-sm leading-relaxed text-mute-2">
        <p>Your NEXUS account is active. The hosted platform is not online yet: today NEXUS runs on your own computer, free and open-source.</p>
        <Link to="/#access" className="block rounded-full border border-line py-3 text-center text-ivory hover:border-ivory">How to run NEXUS</Link>
        <button onClick={async () => { await (await getSupabase())?.auth.signOut(); nav('/', { replace: true }); }} className="w-full rounded-full bg-ivory py-3 font-medium text-void hover:bg-copper">Sign out</button>
      </div>
    </Shell>
  );
}
