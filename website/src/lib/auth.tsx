import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { authConfigured, getSupabase } from './supabase';

interface AuthState {
  configured: boolean;
  loading: boolean;
  session: Session | null;
}

const Ctx = createContext<AuthState>({ configured: false, loading: false, session: null });
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ configured: authConfigured, loading: authConfigured, session: null });
  useEffect(() => {
    const pending = getSupabase();
    if (!pending) return;
    let unsubscribe = () => {};
    let alive = true;
    pending.then((sb) => {
      if (!alive) return;
      sb.auth.getSession().then(({ data }) => alive && setState({ configured: true, loading: false, session: data.session }));
      const { data } = sb.auth.onAuthStateChange((_event, session) => setState({ configured: true, loading: false, session }));
      unsubscribe = () => data.subscription.unsubscribe();
    });
    return () => { alive = false; unsubscribe(); };
  }, []);
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}

export const EMAIL_RX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function passwordProblems(pw: string): string[] {
  const p: string[] = [];
  if (pw.length < 10) p.push('at least 10 characters');
  if (!/[A-Za-z]/.test(pw) || !/[^A-Za-z]/.test(pw)) p.push('letters and at least one number or symbol');
  return p;
}

/** Messaggi d'errore di Supabase resi comprensibili. */
export function authErrorText(message: string): string {
  const m = message.toLowerCase();
  if (m.includes('invalid login credentials')) return 'Email or password is incorrect.';
  if (m.includes('email not confirmed')) return 'Please confirm your email address first — check your inbox.';
  if (m.includes('already registered')) return 'An account with this email already exists. Try signing in.';
  if (m.includes('rate limit') || m.includes('too many')) return 'Too many attempts. Please wait a minute and try again.';
  if (m.includes('fetch') || m.includes('network')) return 'The authentication service could not be reached. Check your connection.';
  return message;
}
