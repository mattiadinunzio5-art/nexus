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
    ├── pages/         Home, ModulePage (/architecture/:slug), Auth (signin/signup/reset/account), NotFound
    └── lib/           supabase.ts, auth.tsx, meta.ts
```

## Enable registration (Supabase)

Without these variables the site states honestly that online registration is not open yet.

1. Create a project at supabase.com.
2. Authentication → Providers → Email: enabled (keep "Confirm email" on).
3. Authentication → URL Configuration:
   - Site URL: `https://your-domain`
   - Redirect URLs: `https://your-domain/account`, `https://your-domain/reset-password`
     (plus `http://localhost:5173/account` and `http://localhost:5173/reset-password` for local testing).
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
