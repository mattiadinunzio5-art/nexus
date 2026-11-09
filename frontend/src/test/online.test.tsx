import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { dashboard, mockApi } from './fixtures';
import { renderApp } from './render';

let session: { access_token: string } | null = null;
const signIn = vi.fn(async ({ password }: { email: string; password: string }) => {
  if (password !== 'Password-giusta-1') return { error: { message: 'Invalid login credentials' } };
  session = { access_token: 'jwt-di-prova' };
  return { error: null };
});
vi.mock('@supabase/supabase-js', () => ({
  createClient: () => ({
    auth: {
      getSession: async () => ({ data: { session } }),
      signInWithPassword: signIn,
      signOut: async () => { session = null; return { error: null }; },
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }),
    },
  }),
}));

const user = { id: 3, email: 'mattia@example.org', display_name: 'mattia', role: 'user', plan: 'free', is_local: false };

describe('online version (Supabase accounts)', () => {
  it('signs in with the website account and sends the token to the server', async () => {
    const { fetchMock } = mockApi({
      'GET /api/auth/config': { mode: 'supabase', allow_registration: false, supabase_url: 'https://x.supabase.co', supabase_anon_key: 'sb_publishable_x', site_url: 'https://nexus.example' },
      'GET /api/me': (_u: string, init?: RequestInit) => ((init?.headers as Record<string, string>)?.Authorization === 'Bearer jwt-di-prova'
        ? user : new Response(JSON.stringify({ error: { code: 'unauthorized', message: 'Accesso richiesto.' } }), { status: 401 })),
      'GET /api/dashboard': dashboard,
      'GET /api/notifications': [],
    });
    renderApp('/');
    expect(await screen.findByRole('heading', { name: 'Accedi con il tuo account NEXUS' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Crea un account' })).toHaveAttribute('href', 'https://nexus.example/signup');
    await userEvent.type(screen.getByLabelText('Email'), 'mattia@example.org');
    await userEvent.type(screen.getByLabelText('Password'), 'sbagliata');
    await userEvent.click(screen.getByRole('button', { name: 'Accedi' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Email o password non corretti.');
    await userEvent.clear(screen.getByLabelText('Password'));
    await userEvent.type(screen.getByLabelText('Password'), 'Password-giusta-1');
    await userEvent.click(screen.getByRole('button', { name: 'Accedi' }));
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
    const dash = fetchMock.mock.calls.find(([u]) => String(u) === '/api/dashboard');
    expect((dash?.[1]?.headers as Record<string, string>).Authorization).toBe('Bearer jwt-di-prova');
  });
});

describe('public demo (no account)', () => {
  it('opens the read-only demo from the login screen and sends the demo token', async () => {
    session = null;
    localStorage.clear();
    const demoUser = { id: 9, email: 'demo@nexus-demo.invalid', display_name: 'Visitatore demo', role: 'user', plan: 'free', is_local: false };
    const { fetchMock } = mockApi({
      'GET /api/auth/config': { mode: 'supabase', allow_registration: false, demo: true, supabase_url: 'https://x.supabase.co', supabase_anon_key: 'sb_publishable_x', site_url: 'https://nexus.example' },
      'POST /api/auth/demo?lang=it': { token: 'demo.123.firma', expires_at: new Date(Date.now() + 3600_000).toISOString() },
      'GET /api/me': (_u: string, init?: RequestInit) => ((init?.headers as Record<string, string>)?.Authorization === 'Bearer demo.123.firma'
        ? demoUser : new Response(JSON.stringify({ error: { code: 'unauthorized', message: 'Accesso richiesto.' } }), { status: 401 })),
      'GET /api/dashboard': dashboard,
      'GET /api/notifications': [],
    });
    renderApp('/');
    await userEvent.click(await screen.findByRole('button', { name: 'Prova la demo senza account' }));
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent('Demo in sola lettura');
    expect(screen.getByRole('link', { name: 'Crea un account gratuito' })).toHaveAttribute('href', 'https://nexus.example/it/signup');
    const dash = fetchMock.mock.calls.find(([u]) => String(u) === '/api/dashboard');
    expect((dash?.[1]?.headers as Record<string, string>).Authorization).toBe('Bearer demo.123.firma');
    await userEvent.click(screen.getByRole('button', { name: 'Esci dalla demo' }));
    expect(await screen.findByRole('heading', { name: 'Accedi con il tuo account NEXUS' })).toBeInTheDocument();
  });
});
