import { useEffect } from 'react';
import { counterpart, useI18n } from './i18n';

export const SITE_NAME = 'NEXUS';

function setMeta(selector: string, attr: string, value: string) {
  let el = document.head.querySelector<HTMLMetaElement | HTMLLinkElement>(selector);
  if (!el) {
    el = selector.startsWith('link') ? document.createElement('link') : document.createElement('meta');
    for (const m of selector.matchAll(/\[([a-z]+)="([^"]+)"\]/g)) el.setAttribute(m[1], m[2]);
    document.head.appendChild(el);
  }
  el.setAttribute(attr, value);
}

/** Titolo, descrizione, lingua, canonical, hreflang e Open Graph per pagina (anche pre-generati in build: seo.config.ts). */
export function usePageMeta(title: string | null, description?: string) {
  const { t, lang } = useI18n();
  const desc = description ?? t.meta.description;
  useEffect(() => {
    const full = title ? `${title} — ${SITE_NAME}` : t.meta.homeTitle;
    const { origin, pathname } = window.location;
    const other = counterpart(pathname, '');
    document.title = full;
    document.documentElement.lang = lang;
    setMeta('meta[name="description"]', 'content', desc);
    setMeta('meta[property="og:title"]', 'content', full);
    setMeta('meta[property="og:description"]', 'content', desc);
    setMeta('meta[property="og:locale"]', 'content', lang === 'it' ? 'it_IT' : 'en_US');
    setMeta('link[rel="canonical"]', 'href', origin + pathname);
    setMeta(`link[rel="alternate"][hreflang="${lang}"]`, 'href', origin + pathname);
    setMeta(`link[rel="alternate"][hreflang="${lang === 'it' ? 'en' : 'it'}"]`, 'href', origin + other);
  }, [title, desc, lang, t]);
}
