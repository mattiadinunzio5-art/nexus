/**
 * Lingua dell'interfaccia: italiano (testi nel codice) o inglese (dizionario `en.ts`).
 *
 * I testi restano scritti in italiano nei componenti. In inglese il runtime JSX di NEXUS (`jsx-runtime.ts`)
 * traduce al volo il testo e gli attributi visibili (placeholder, title, aria-label, alt) degli elementi HTML:
 * prima per corrispondenza esatta, poi con i modelli che contengono parti variabili ({0}, {1}…).
 * I dati dell'utente non sono nel dizionario e restano come sono.
 */
import { EN } from './en';
import { EN_SERVER_1 } from './en-server-1';
import { EN_SERVER_2 } from './en-server-2';
import { EN_SERVER_3 } from './en-server-3';

export type Lang = 'it' | 'en';
const KEY = 'nexus.lang';

function detect(): Lang {
  if (typeof window === 'undefined') return 'it';
  const q = new URLSearchParams(window.location.search);
  const fromUrl = q.get('lang') ?? (q.get('demo') === 'en' ? 'en' : q.get('demo') ? 'it' : null);
  if (fromUrl === 'en' || fromUrl === 'it') {
    try { localStorage.setItem(KEY, fromUrl); } catch { /* storage non disponibile */ }
    return fromUrl;
  }
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === 'en' || saved === 'it') return saved;
  } catch { /* storage non disponibile */ }
  const nav = (navigator.languages?.[0] ?? navigator.language ?? 'it').toLowerCase();
  return nav.startsWith('it') ? 'it' : 'en';
}

let current: Lang = detect();

export function lang(): Lang {
  return current;
}

/** Cambia lingua e ricarica la pagina (il dizionario si applica a tutto, senza stati a metà). */
export function setLang(l: Lang): void {
  try { localStorage.setItem(KEY, l); } catch { /* storage non disponibile */ }
  current = l;
  if (typeof window !== 'undefined') {
    const u = new URL(window.location.href);
    u.searchParams.delete('lang');
    window.location.replace(u.toString());
  }
}

/** Solo per i test. */
export function _setLangForTests(l: Lang): void {
  current = l;
}

/** Locale per numeri e date. */
export function locale(): string {
  return current === 'en' ? 'en-GB' : 'it-IT';
}

// --- traduzione ------------------------------------------------------------------------------------

const norm = (s: string) => s.replace(/\s+/g, ' ').trim();
const exact = new Map<string, string>();
const patterns: { re: RegExp; out: string }[] = [];
// Testi del server (messaggi, etichette, metodi) e dell'interfaccia: un unico dizionario.
for (const [k, v] of Object.entries({ ...EN_SERVER_1, ...EN_SERVER_2, ...EN_SERVER_3, ...EN })) {
  const key = norm(k);
  if (/\{\d+\}/.test(key)) {
    const re = new RegExp('^' + key.replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace(/\{(\d+)\}/g, '(?<g$1>[\\s\\S]+?)') + '$');
    patterns.push({ re, out: v });
  } else {
    exact.set(key, v);
  }
}

function translateCore(s: string): string | null {
  const hit = exact.get(s);
  if (hit !== undefined) return hit;
  for (const { re, out } of patterns) {
    const m = re.exec(s);
    if (m?.groups) {
      return out.replace(/\{(\d+)\}/g, (_, i: string) => {
        const part = m.groups![`g${i}`] ?? '';
        return translateCore(part.trim()) ?? part;
      });
    }
  }
  return null;
}

/** Traduce un testo dell'interfaccia (mantiene gli spazi iniziali e finali). Invariato se non è nel dizionario. */
export function tr(s: string): string {
  if (current !== 'en' || !s || !/[A-Za-zÀ-ÿ]/.test(s)) return s;
  const core = norm(s);
  const t = translateCore(core);
  if (t === null) return s;
  const lead = /^\s/.test(s) ? ' ' : '';
  const trail = /\s$/.test(s) ? ' ' : '';
  return lead + t + trail;
}
