# NEXUS online (gratis): Render + Supabase + Vercel

| Parte | Dove | Costo |
|---|---|---|
| Server della piattaforma (FastAPI) | Render, piano Free (`render.yaml`) | 0 € — si addormenta dopo 15 min senza visite, il primo accesso dopo richiede ~1 minuto |
| Database PostgreSQL | Supabase (stesso progetto del sito) | 0 € |
| File dei documenti | Supabase Storage, bucket privato `nexus-documents` (creato in automatico) | 0 € fino a 1 GB |
| Interfaccia (cartella `frontend`) | Vercel, secondo progetto | 0 € |
| Account | Supabase Auth: **gli stessi del sito** | 0 € |

## Variabili del server (Render)

| Variabile | Valore |
|---|---|
| `NEXUS_DATABASE_URL` | Supabase → Connect → **Session pooler** (URI con la password del database) |
| `NEXUS_SUPABASE_URL` | `https://<progetto>.supabase.co` |
| `NEXUS_SUPABASE_ANON_KEY` | chiave publishable/anon |
| `NEXUS_SUPABASE_SERVICE_KEY` | chiave **secret / service_role** — solo qui, mai nel sito o nell'interfaccia |
| `NEXUS_CORS_ORIGINS` | indirizzo dell'interfaccia su Vercel |
| `NEXUS_SITE_URL` | indirizzo del sito |
| `NEXUS_ADMIN_EMAILS` | email che diventano amministratori |
| `NEXUS_SECRET_KEY` | generata da Render (cifra le chiavi API salvate dagli utenti) |

## Variabili dell'interfaccia (Vercel, progetto con Root Directory `frontend`)

`VITE_API_URL` = indirizzo del server su Render (es. `https://nexus-api.onrender.com`).

## Variabili del sito

`VITE_APP_URL` = indirizzo dell'interfaccia: il sito mostra «Apri la piattaforma».

## Note

- Ogni utente ha i propri dati; i limiti del piano «free» si applicano (vedi `backend/nexus/core/plans.py`).
- L'AI resta facoltativa: ogni utente usa le proprie chiavi (cifrate con `NEXUS_SECRET_KEY`). Ollama non è disponibile online.
- In locale non cambia nulla: `scripts/dev.sh` usa SQLite, la cartella `data/` e gli account locali.
