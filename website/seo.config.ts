import fs from 'node:fs';
import path from 'node:path';
import type { Plugin } from 'vite';
import { MODULES } from './src/content/modules';

const DEFAULT_DESC =
  'NEXUS is an integrated research environment to collect, connect, analyze and simulate complex historical, economic and financial knowledge — with verifiable sources.';

interface Page { path: string; title: string; description: string; index: boolean }

export const PAGES: Page[] = [
  { path: '/', title: 'NEXUS — Research. Intelligence. Knowledge.', description: DEFAULT_DESC, index: true },
  ...MODULES.map((m) => ({ path: `/architecture/${m.slug}`, title: `${m.title} — guide — NEXUS`, description: `${m.tagline} ${m.mainFunction}`, index: true })),
  { path: '/signin', title: 'Sign in — NEXUS', description: 'Sign in to your NEXUS account.', index: false },
  { path: '/signup', title: 'Create account — NEXUS', description: 'Create your NEXUS account.', index: false },
];

/** URL pubblico: SITE_URL esplicito, oppure l'indirizzo di produzione fornito da Vercel in build. */
export function siteUrl(): string | null {
  const explicit = process.env.SITE_URL?.trim();
  if (explicit) return explicit.replace(/\/+$/, '');
  const vercel = process.env.VERCEL_PROJECT_PRODUCTION_URL?.trim();
  return vercel ? `https://${vercel}` : null;
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

export function renderHead(html: string, page: Page, base: string | null): string {
  const url = base ? base + (page.path === '/' ? '/' : page.path) : null;
  let out = html
    .replace(/<title>[^<]*<\/title>/, `<title>${esc(page.title)}</title>`)
    .replace(/(<meta name="description" content=")[^"]*(")/, `$1${esc(page.description)}$2`)
    .replace(/(<meta property="og:title" content=")[^"]*(")/, `$1${esc(page.title)}$2`)
    .replace(/(<meta property="og:description" content=")[^"]*(")/, `$1${esc(page.description)}$2`);
  const extra: string[] = [];
  if (url) {
    extra.push(`<link rel="canonical" href="${url}" />`, `<meta property="og:url" content="${url}" />`);
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
      const robots = ['User-agent: *', 'Allow: /', 'Disallow: /account', 'Disallow: /reset-password'];
      if (base) {
        const today = new Date().toISOString().slice(0, 10);
        const urls = PAGES.filter((p) => p.index).map((p) => `  <url><loc>${base}${p.path === '/' ? '/' : p.path}</loc><lastmod>${today}</lastmod></url>`);
        fs.writeFileSync(path.join(outDir, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>\n`);
        robots.push(`Sitemap: ${base}/sitemap.xml`);
      } else {
        this.warn('SITE_URL non impostato: sitemap.xml non generata e URL canonici omessi (su Vercel vengono ricavati automaticamente).');
      }
      fs.writeFileSync(path.join(outDir, 'robots.txt'), robots.join('\n') + '\n');
    },
  };
}
