import type { SupabaseClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** True solo se le variabili d'ambiente sono presenti: altrimenti l'accesso è dichiarato non attivo. */
export const authConfigured = Boolean(url && anonKey);

let client: Promise<SupabaseClient> | null = null;

/** Client Supabase caricato su richiesta (la libreria non pesa sulla prima schermata). */
export function getSupabase(): Promise<SupabaseClient> | null {
  if (!authConfigured) return null;
  client ??= import('@supabase/supabase-js').then(({ createClient }) =>
    createClient(url!, anonKey!, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }),
  );
  return client;
}

/** Indirizzo della piattaforma online (Vercel): se assente, la piattaforma si usa solo in locale. */
export const appUrl = (import.meta.env.VITE_APP_URL as string | undefined)?.replace(/\/+$/, '') || null;

/** Demo pubblica in sola lettura della piattaforma (nessun account richiesto). */
export const demoUrl = appUrl ? `${appUrl}/?demo=1` : null;
