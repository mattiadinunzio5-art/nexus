# Sicurezza e isolamento tra utenti

Ultimo controllo: 16/11/2026 (Fase 3, punto 13).

## Isolamento tra utenti (API)

`backend/tests/test_isolation.py` crea quattro account (proprietaria, editor e viewer di un progetto condiviso,
estraneo) e chiama **tutte** le rotte dell'API con un identificativo nel percorso, prese dallo schema OpenAPI (una rotta
nuova entra da sola nel controllo), con gli ID dei dati della proprietaria. Per ogni rotta si invia un corpo valido,
così il controllo dei permessi viene davvero raggiunto (un 422 di validazione farebbe fallire il test).

Verificato: nessun 2xx sui dati privati altrui (94 rotte × 3 utenti), nessun contenuto altrui nelle risposte, dati della
proprietaria identici dopo tutti i tentativi, manipolazione degli ID nei corpi (22 casi: collegare fonti, documenti, serie,
progetti, entità altrui ai propri oggetti), ruoli viewer/editor sul progetto condiviso, rotte di amministrazione,
elenchi e ricerca, credenziali (mai restituite).

## Intestazioni di sicurezza

| Dove | Intestazioni |
| --- | --- |
| Backend (tutte le risposte, anche errori) | CSP `default-src 'none'; frame-ancestors 'none'; sandbox` (per `/docs` una CSP che permette Swagger da cdn.jsdelivr.net), HSTS solo su HTTPS (anche dietro il proxy di Render), Permissions-Policy, COOP, X-Frame-Options, nosniff, Referrer-Policy |
| App (`frontend/vercel.json`) | CSP con `script-src 'self'`, `connect-src` verso l'API su Render e Supabase, HSTS, Permissions-Policy, COOP |
| Sito (`website/vercel.json`) | CSP con `script-src 'self'`, `connect-src` verso Supabase, HSTS, Permissions-Policy, COOP |

Verifica nel browser: build di produzione servite con le intestazioni di `vercel.json`, 16 pagine dell'app e 3 del sito,
zero violazioni CSP. **Da controllare dopo il primo deploy**: l'indirizzo reale dell'API nella variabile `VITE_API_URL`
(la CSP ammette solo `https://nexus-api-7w2q.onrender.com`; se il server cambia indirizzo va aggiornato `connect-src` in `frontend/vercel.json`).
Non è stato possibile leggere la configurazione Vercel: serve un'autorizzazione dell'account al team.

## XSS

React mostra i testi come testo; nessun `dangerouslySetInnerHTML`. I link costruiti da dati (`safeHref`) accettano solo
`http(s)`; il backend rifiuta URL non http(s) per fonti e serie caricate (prima le serie accettavano qualsiasi URL).
I file caricati sono serviti con CSP `sandbox` e `nosniff`. Test: `xss.test.tsx`, `test_isolation.py`, verifica nel
browser con payload salvati in fonti, eventi, progetti, appunti e rapporti (nessuno script eseguito).

## Sessioni e token

- Multi-utente: il logout invalida il token (cookie e Bearer); sessioni scadute rifiutate e cancellate; revoca di una
  singola sessione; il cambio password chiude le altre; un account disattivato perde tutte le sessioni.
- Online (Supabase): al logout l'app chiama prima il server, che toglie il token dalla cache e lo rifiuta fino alla sua
  scadenza naturale (prima restava valido fino a 2 minuti), poi chiude la sessione su Supabase.

## Supabase: policy RLS (sola lettura, nessuna modifica)

Progetto `oagwjjmtooulavziiioa`, controllato con SQL in sola lettura e con gli advisor di sicurezza.

**Stato**
- Tutte le 36 tabelle di `public` hanno RLS attiva e **nessuna policy**: per i ruoli `anon` e `authenticated`
  (chiave pubblica del sito/app) nessuna riga è leggibile o modificabile. Il backend usa la connessione diretta al
  database (proprietario delle tabelle), che non è soggetta a RLS. È la configurazione corretta per un'architettura in cui
  il browser non interroga mai direttamente il database.
- `anon`/`authenticated` non hanno SELECT/INSERT/UPDATE/DELETE sulle tabelle, ma hanno ancora **TRUNCATE, REFERENCES,
  TRIGGER** (permessi predefiniti di Supabase). TRUNCATE non è filtrato dalla RLS; via API REST non è esposto, ma è un
  permesso inutile.
- Un trigger di evento (`ensure_rls` → `rls_auto_enable`, SECURITY DEFINER, non eseguibile da anon/authenticated) attiva
  la RLS sulle tabelle nuove: le tabelle delle migrazioni 0018–0021 (`report_section_versions`, `deleted_documents`,
  `system_checks`) nasceranno protette.
- Bucket `nexus-documents` e `nexus-backups` privati, RLS attiva su `storage.objects`, nessuna policy di storage: solo la
  chiave di servizio del server può leggere e scrivere.
- Advisor: «RLS enabled, no policy» (informativo, voluto) su 36 tabelle; **«Leaked password protection» disattivata**
  (avviso).
- Database in produzione alla migrazione 0017: le migrazioni 0018–0021 di questa PR si applicheranno al deploy.

**Raccomandazioni** (da eseguire a mano, dopo averle valutate)
1. Attivare la protezione dalle password compromesse: Supabase → Authentication → Policies/Passwords → «Leaked password
   protection».
2. Togliere i permessi inutili ai ruoli pubblici:
   `REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM anon, authenticated;`
   e per il futuro `ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;`
3. Se l'API REST di Supabase non serve per lo schema `public`, toglierlo dagli schemi esposti (Settings → API → Exposed
   schemas): difesa in profondità.
4. Non aggiungere policy «permissive» (`using (true)`): se un giorno il browser dovesse leggere direttamente una tabella,
   usare policy per riga con `auth.uid()` collegato a `users.external_id`.
5. Controllare periodicamente gli advisor di sicurezza (Supabase → Advisors).
