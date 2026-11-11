/** Runtime JSX di NEXUS: come quello di React, ma in inglese traduce testo e attributi visibili degli elementi HTML. */
import * as R from 'react/jsx-runtime';
import { lang, tr } from './index';

export type { JSX } from 'react/jsx-runtime';
export const Fragment = R.Fragment;

const ATTRS = ['placeholder', 'title', 'aria-label', 'alt', 'aria-description'] as const;

function child(c: unknown): unknown {
  if (typeof c === 'string') return tr(c);
  if (Array.isArray(c)) return c.map(child);
  return c;
}

export function translateProps(_type: unknown, props: Record<string, unknown>): Record<string, unknown> {
  // Anche per i componenti (es. <Link> di react-router, che crea il suo <a> con un altro runtime): i testi passati
  // come figli o come attributi visibili vengono tradotti qui. Una seconda traduzione non cambia un testo già inglese.
  if (lang() !== 'en' || !props || typeof props !== 'object') return props;
  let out: Record<string, unknown> | null = null;
  const set = (k: string, v: unknown) => { if (!out) out = { ...props }; out[k] = v; };
  if (props.children !== undefined) {
    const c = child(props.children);
    if (c !== props.children) set('children', c);
  }
  for (const a of ATTRS) {
    const v = props[a];
    if (typeof v === 'string') { const t = tr(v); if (t !== v) set(a, t); }
  }
  return out ?? props;
}

export function jsx(type: React.ElementType, props: Record<string, unknown>, key?: React.Key) {
  return R.jsx(type, translateProps(type, props), key);
}

export function jsxs(type: React.ElementType, props: Record<string, unknown>, key?: React.Key) {
  return R.jsxs(type, translateProps(type, props), key);
}
