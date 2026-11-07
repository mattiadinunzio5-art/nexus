# NEXUS — Official Website

Public website for NEXUS, the Historical & Financial Intelligence Platform.
Vite + React + TypeScript + Tailwind v4 + Framer Motion. Auth via Supabase (optional).

## Run locally

```bash
cd website
npm install
npm run dev        # http://localhost:5173
npm test           # unit + route tests
npm run build      # static output in dist/ (per-route SEO pages, sitemap, robots)
```

## Structure

```
website/
├── index.html, vercel.json, seo.config.ts (per-page meta, sitemap, robots)
├── public/            favicon.svg, og-image.png, apple-touch-icon.png
└── src/
    ├── content/       modules.ts (12 modules), story.ts (workflow, 2008 case study, capabilities)
    ├── components/    Navbar, Footer, HeroGraph (canvas), ModuleVisual, Reveal, sections/*
    ├── pages/         Home, ModulePage (/architecture/:slug), Cases, Auth (signin/signup/reset/account), NotFound
    └── lib/           supabase.ts, auth.tsx, meta.ts, i18n.tsx, strings.ts
```

## Languages and content

- English at `/`, Italian at `/it` (same pages: `/it/architecture/...`, `/it/cases/...`). The EN/IT switch keeps you on the same page.
- Interface strings: `src/lib/strings.ts`. Module guides: `src/content/modules.ts` (EN) and `modules.it.ts` (IT). Workflow, case study and capabilities: `story.ts` / `story.it.ts`.
- **Cases of the month**: add an entry to `src/content/cases.ts` (both `en` and `it`, with official sources). The page, the home preview, SEO and sitemap update automatically. Only documented facts — no invented figures.

## Enable registration (Supabase)

Without these variables the site states honestly that online registration is not open yet.

1. Create a project at supabase.com.
2. Authentication → Providers → Email: enabled (keep "Confirm email" on).
3. Authentication → URL Configuration:
   - Site URL: `https://your-domain`
   - Redirect URLs: `https://your-domain/account`, `https://your-domain/reset-password`,
     `https://your-domain/it/account`, `https://your-domain/it/reset-password`
     (plus the same paths on `http://localhost:5173` for local testing).
4. Project Settings → API: copy **Project URL** and **anon public** key.
5. Copy `.env.example` to `.env.local` and fill in `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
   Never use the `service_role` key in the website.
6. Test: sign up → confirm email → /account → sign out → forgot password → reset.

## Deploy on Vercel

1. vercel.com → Add New Project → import the `nexus` repository.
2. **Root Directory: `website`** (framework Vite is detected; `vercel.json` handles SPA routes).
3. Environment variables: `SITE_URL` (e.g. `https://nexus.example.com`, used for canonical URLs and sitemap),
   `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
4. Deploy. Add your domain under Settings → Domains, then update `SITE_URL` and Supabase URLs and redeploy.

## Still to configure

- Supabase keys (login is not active until configured and tested).
- Final domain → `SITE_URL` (without it no sitemap/canonical is generated).
- The 2008 case study is a labelled demonstration of the workflow, not research results.
