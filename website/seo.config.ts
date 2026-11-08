import fs from 'node:fs';
import path from 'node:path';
import type { Plugin } from 'vite';
import { MODULES } from './src/content/modules';
import { MODULES_IT } from './src/content/modules.it';
import { CASES } from './src/content/cases';
import { STRINGS } from './src/lib/strings';

type Lang = 'en' | 'it';
export interface Page { path: string; title: string; description: string; index: boolean; lang: Lang; alt: string }

const it = (p: string) => (p === '/' ? '/it' : `/it${p}`);

function pagesFor(lang: Lang): Page[] {
  const t = STRINGS[lang];
  const mods = lang === 'it' ? MODULES_IT : MODULES;
  const loc = (p: string) => (lang === 'it' ? it(p) : p);
  const alt = (p: string) => (lang === 'it' ? p : it(p));
  const page = (p: string, title: string, description: string, index = true): Page => ({ path: loc(p), title, description, index, lang, alt: alt(p) });
  return [
    page('/', t.meta.homeTitle, t.meta.description),
    ...mods.map((m) => page(`/architecture/${m.slug}`, `${m.title} — ${t.mod.guide} — NEXUS`, `${m.tagline} ${m.mainFunction}`)),
    page('/cases', `${t.cases.pageTitle} — NEXUS`, t.cases.pageDescription),
    ...CASES.map((c) => page(`/cases/${c.slug}`, `${c[lang].title} — NEXUS`, c[lang].dek)),
    page('/signin', `${t.auth.signInTitle} — NEXUS`, t.auth.signInSub, false),
    page('/signup', `${t.auth.createAccount} — NEXUS`, t.auth.signUpSub, false),
    page('/privacy', `${lang === 'it' ? 'Informativa sulla privacy' : 'Privacy policy'} — NEXUS`,
      lang === 'it' ? 'Quali dati personali tratta NEXUS, perché e con quali diritti.' : 'Which personal data NEXUS processes, why, and your rights.'),
  ];
}

export const PAGES: Page[] = [...pagesFor('en'), ...pagesFor('it')];

/** URL pubblico: SITE_URL esplicito, oppure l'indirizzo di produzione fornito da Vercel in build. */
export function siteUrl(): string | null {
  const explicit = process.env.SITE_URL?.trim();
  if (explicit) return explicit.replace(/\/+$/, '');
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL?.trim();
  return vercel ? `https://${vercel}` : null;
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

export function renderHead(html: string, page: Page, base: string | null): string {
  let out = html
    .replace(/<html lang="[a-z]+">/, `<html lang="${page.lang}">`)
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(page.title)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*(")/, `$1${esc(page.description)}$2`)
    .replace(/(<meta property="og:title" content=")[^"]*(")/, `$1${esc(page.title)}$2`)
    .replace(/(<meta property="og:description" content=")[^"]*(")/, `$1${esc(page.description)}$2`);
  const extra: string[] = [`<meta property="og:locale" content="${page.lang === 'it' ? 'it_IT' : 'en_US'}" />`];
  if (base) {
    const url = base + page.path;
    const other = base + page.alt;
    const en = page.lang === 'en' ? url : other;
    extra.push(
      `<link rel="canonical" href="${url}" />`,
      `<meta property="og:url" content="${url}" />`,
      `<link rel="alternate" hreflang="${page.lang}" href="${url}" />`,
      `<link rel="alternate" hreflang="${page.lang === 'it' ? 'en' : 'it'}" href="${other}" />`,
      `<link rel="alternate" hreflang="x-default" href="${en}" />`,
    );
    out = out.replace(/(<meta property="og:image" content=")\/og-image\.png(")/, `$1${base}/og-image.png$2`);
  }
  if (!page.index) extra.push('<meta name="robots" content="noindex" />');
  return out.replace('</head>', `    ${extra.join('\n    ')}\n  </head>`);
}

export function seoPages(): Plugin {
  let outDir = 'dist';
  return {
    name: 'nexus-seo-pages',
    apply: 'build',
    configResolved(c) { outDir = path.resolve(c.root, c.build.outDir); },
    closeBundle() {
      const base = siteUrl();
      const template = fs.readFileSync(path.join(outDir, 'index.html'), 'utf8');
      for (const page of PAGES) {
        const file = page.path === '/' ? path.join(outDir, 'index.html') : path.join(outDir, page.path, 'index.html');
        fs.mkdirSync(path.dirname(file), { recursive: true });
        fs.writeFileSync(file, renderHead(template, page, base));
      }
      const robots = ['User-agent: *', 'Allow: /', 'Disallow: /account', 'Disallow: /reset-password', 'Disallow: /it/account', 'Disallow: /it/reset-password'];
      if (base) {
        const today = new Date().toISOString().slice(0, 10);
        const urls = PAGES.filter((p) => p.index).map((p) =>
          `  <url><loc>${base}${p.path}</loc><lastmod>${today}</lastmod>` +
          `<xhtml:link rel="alternate" hreflang="${p.lang === 'it' ? 'en' : 'it'}" href="${base}${p.alt}"/></url>`);
        fs.writeFileSync(path.join(outDir, 'sitemap.xml'),
          `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n${urls.join('\n')}\n</urlset>\n`);
        robots.push(`Sitemap: ${base}/sitemap.xml`);
      } else {
        this.warn('SITE_URL non impostato: sitemap.xml non generata e URL canonici omessi (su Vercel vengono ricavati automaticamente).');
      }
      fs.writeFileSync(path.join(outDir, 'robots.txt'), robots.join('\n') + '\n');
    },
  };
}
