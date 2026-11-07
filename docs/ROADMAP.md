# NEXUS — Roadmap (idee concordate, non ancora implementate)

## Piani e prezzi (aggiornamento futuro)

| Piano | Prezzo | Cosa sblocca |
|---|---|---|
| Free | 0 € | Online + locale, 2 progetti, 50 documenti, dati FRED, Timeline, Knowledge Graph (sola lettura), report con scritta DRAFT, AI solo con chiave propria / Ollama |
| Student | 5 €/mese o 39 €/anno | Come Pro con meno AI inclusa e meno spazio; verifica email universitaria |
| Pro | 15 €/mese o 129 €/anno | Progetti illimitati, tutti i moduli (War Room, Economic Lab, Time Machine), AI inclusa online con tetto mensile, 10 GB, export PDF/DOCX senza scritta |
| Lifetime | 100 € una tantum (primi 200) | Tutte le funzioni Pro per sempre, online + locale; AI non inclusa (chiave propria / Ollama) |

- Pagamenti: Paddle (merchant of record: fatture, IVA UE, rimborsi). Niente Stripe. Alternativa: PayPal.
- Ordine: 1) pagina Pricing + waitlist sul sito; 2) versione online multi-utente con limiti per piano; 3) integrazione Paddle (richiede account e dati fiscali dell'autore).
- Prima di vendere: partita IVA / commercialista, Termini, Privacy, diritto di recesso 14 giorni.

## Funzioni nuove — FATTE (novembre 2026)

- **Collaborazione**: commenti e cronologia nei progetti (ruoli già presenti). ✅
- **Avvisi**: nuovo dato o soglia superata su qualsiasi serie; script `scripts/check_alerts.py` da pianificare. ✅
- **Nuove fonti dati**: BCE e ISTAT aggiunti (Eurostat e Banca Mondiale c'erano già). ✅
- **Lezioni guidate**: crisi 1929, inflazione anni '70, crisi 2008. ✅
- **Export LaTeX + BibTeX** (import/export, compatibile Zotero). ✅
- **App installabile (PWA)**: attiva in HTTPS o localhost; su iPhone «Aggiungi a Home». ✅

## Sito — FATTO (novembre 2026)

- **Casi del mese**: sezione e pagine `/cases`, 2 casi di metodo (2008, inflazione italiana). ✅
- **Versione italiana** su `/it`, con selettore EN/IT, SEO e hreflang. ✅
