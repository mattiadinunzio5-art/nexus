# Pubblicazione automatica Instagram (nexus.analytic)

- `calendario.json`: cosa pubblicare e quando (Europe/Rome). 17 post carosello alle 12:30
  (16/11–2/12/2026) e 12 reel alle 19:00 (21/11–2/12/2026). I reel dal 16 al 20/11 sono su Metricool.
- `media/`: copie dei materiali di Drive (PNG convertiti in JPEG, richiesto dall'API Meta;
  reel invariati). I file originali su Drive non vengono toccati. `media/_sorgenti_drive.json`
  dice da quale file di Drive viene ogni copia.
- `registro.json`: ciò che è stato pubblicato (id contenuto, id media, link). Serve a non duplicare.
- Script: `scripts/instagram/pubblica.py --tipo post|reel [--data AAAA-MM-GG] [--dry-run]`.

Il token Meta non è nel repository: è salvato come segreto dell'ambiente Claude e il proxy lo
aggiunge alle richieste verso graph.facebook.com.
