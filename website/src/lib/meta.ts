import { useEffect } from 'react';

export const SITE_NAME = 'NEXUS';
export const DEFAULT_DESCRIPTION =
  'NEXUS is an integrated research environment to collect, connect, analyze and simulate complex historical, economic and financial knowledge — with verifiable sources.';

function setMeta(selector: string, attr: string, value: string) {
  let el = document.head.querySelector<HTMLMetaElement | HTMLLinkElement>(selector);
  if (!el) {
    el = selector.startsWith('link') ? document.createElement('link') : document.createElement('meta');
    const m = selector.match(/\[(name|property|rel)="([^"]+)"\]/);
    if (m) el.setAttribute(m[1], m[2]);
    document.head.appendChild(el);
  }
  el.setAttribute(attr, value);
}

/** Titolo, descrizione, canonical e Open Graph per pagina (anche pre-generati in build: seo.config.ts). */
export function usePageMeta(title: string | null, description = DEFAULT_DESCRIPTION) {
  useEffect(() => {
    const full = title ? `${title} — ${SITE_NAME}` : `${SITE_NAME} — Research. Intelligence. Knowledge.`;
    document.title = full;
    setMeta('meta[name="description"]', 'content', description);
    setMeta('meta[property="og:title"]', 'content', full);
    setMeta('meta[property="og:description"]', 'content', description);
    setMeta('link[rel="canonical"]', 'href', window.location.origin + window.location.pathname);
  }, [title, description]);
}
