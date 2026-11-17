# NEXUS – cosa funziona sui social (memoria per i nuovi contenuti)

Aggiornato automaticamente ogni domenica dall'analisi settimanale (dati in `metriche.json`,
raccolti con `scripts/analytics/raccogli_metriche.py`). Da leggere PRIMA di creare nuovi video o post.

## Stato dei dati (17/11/2026)
- TikTok: 7 video, 3.757 visualizzazioni (media ~540). Instagram: 14 contenuti, 420 visualizzazioni, 1 follower.
- Campione ancora piccolo: le conclusioni sotto sono ipotesi da confermare, non regole.

## Decisioni in vigore
- **17/11/2026: caroselli Instagram IN PAUSA** (scelta dell'utente). Su Instagram escono solo i reel.
- **17/11/2026: due reel al giorno su Instagram (12:30 e 19:00)** fino al 25/11, quando finiscono i reel pronti. Confrontare 12:30 vs 19:00 a 72 ore. I caroselli restano pronti in `social/instagram/calendario.json` e `media/` per quando ci saranno più follower.

## Cosa sembra funzionare
1. **Reel >> caroselli su Instagram**: reel in media 57 visualizzazioni (migliore 188), caroselli 1–4.
   Con pochi follower i caroselli non vengono distribuiti; i reel sì (arrivano a non follower).
2. **TikTok: tono personale > dato secco.** I video in prima persona / rivolti allo spettatore
   («I spent months building NEXUS», «Tired of history content with zero sources?», «Writing a thesis…»)
   hanno fatto ~720–850 visualizzazioni; quelli che partono dal fatto storico («How bad was the Great Depression?»,
   «Historians call it hindsight bias») ~230–250.
3. **Aggancio con un numero forte** («1929 wasn't the first crash», «Prices up 23,773%») dà il tempo di visione
   migliore (2,8 s contro 1,3–1,8 s) e i reel Instagram migliori.

## Problema principale
- **Tempo medio di visione 1,3–2,8 secondi** su video di 25–48 s: quasi tutti scorrono via subito.
  L'algoritmo non spinge oltre la prima ondata. Priorità per i nuovi video:
  - prima frase = numero o domanda, scritta GRANDE a schermo entro 0,5 s, senza intro/logo;
  - video più corti (15–25 s);
  - movimento o cambio d'inquadratura entro i primi 2 s;
  - un solo concetto per video.

## Orari (esperimento in corso)
- Studi 2026 (Metricool, Buffer): TikTok meglio la sera 18–20 e la domenica; Reels sera/notte. Nessuno specifico per l'Italia.
- Dati nostri TikTok finora: pranzo (12–15) media ~600, mattina 847 (1 video), sera 257 (1 video, ancora giovane).
- Esperimento: dal 26/11 al 6/12 i TikTok ruotano tra **13:00, 08:00 e 19:00** (4 video per fascia).
  A fine esperimento si sceglie la fascia migliore confrontando le visualizzazioni a 72 ore.
- Instagram: reel alle 19:00 (il migliore è uscito alle 20:28), caroselli alle 12:30.

## Da fare quando si creano nuovi contenuti
- Su Instagram dare priorità ai reel; i caroselli servono soprattutto quando ci saranno follower.
- Su TikTok alternare video «personali» (perché ho creato NEXUS, come aiuta in tesi/esami) e video «numero shock».
- Riutilizzare gli argomenti che hanno funzionato: crisi finanziarie, iperinflazione, banche centrali.
