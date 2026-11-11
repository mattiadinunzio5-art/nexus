/** Versione di sviluppo del runtime JSX di NEXUS (vedi jsx-runtime.ts). */
import * as R from 'react/jsx-dev-runtime';
import { translateProps } from './jsx-runtime';

export type { JSX } from 'react/jsx-dev-runtime';
export const Fragment = R.Fragment;

export function jsxDEV(type: React.ElementType, props: Record<string, unknown>, key: React.Key | undefined, isStatic: boolean, source?: unknown, self?: unknown) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (R as any).jsxDEV(type, translateProps(type, props), key, isStatic, source, self);
}
