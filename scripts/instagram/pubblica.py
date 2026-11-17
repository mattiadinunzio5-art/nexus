#!/usr/bin/env python3
"""Pubblica su Instagram (nexus.analytic) il contenuto del giorno dal calendario.

Uso:
    python3 scripts/instagram/pubblica.py --tipo post|reel [--ora HH:MM] [--data AAAA-MM-GG] [--dry-run]

- Legge social/instagram/calendario.json e social/instagram/registro.json.
- Non pubblica mai due volte: salta se l'id e' nel registro OPPURE se tra gli
  ultimi media dell'account c'e' gia' una didascalia identica.
- Controlla il limite di pubblicazione (content_publishing_limit) prima di pubblicare.
- Il token NON e' nel codice: il proxy dell'ambiente aggiunge l'header
  Authorization alle richieste verso graph.facebook.com. In alternativa si puo'
  impostare la variabile IG_ACCESS_TOKEN.
- Scrive l'esito nel registro; il commit lo fa chi lancia lo script.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAL = os.path.join(ROOT, "social", "instagram", "calendario.json")
REG = os.path.join(ROOT, "social", "instagram", "registro.json")
GRAPH = "https://graph.facebook.com/v21.0"


def api(method, path, params=None):
    params = dict(params or {})
    headers = {}
    token = os.environ.get("IG_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{GRAPH}/{path}"
    data = None
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"ERRORE Graph API {method} {path}: {e.code} {body}")


def url_ok(url):
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status == 200
    except urllib.error.URLError:
        return False


def attendi(container_id, max_sec=600):
    t0 = time.time()
    while True:
        st = api("GET", container_id, {"fields": "status_code,status"})
        code = st.get("status_code")
        if code in ("FINISHED", "PUBLISHED"):
            return
        if code in ("ERROR", "EXPIRED"):
            raise SystemExit(f"ERRORE contenitore {container_id}: {st}")
        if time.time() - t0 > max_sec:
            raise SystemExit(f"ERRORE: contenitore {container_id} non pronto dopo {max_sec}s ({st})")
        time.sleep(10)


def carica_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", choices=["post", "reel"], required=True)
    ap.add_argument("--data", help="AAAA-MM-GG (default: oggi, Europe/Rome)")
    ap.add_argument("--ora", help="HH:MM: sceglie il contenuto di quell'orario (utile con piu' reel al giorno)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cal = carica_json(CAL, None)
    reg = carica_json(REG, {"pubblicati": []})
    ig = cal["account_instagram_id"]
    oggi = a.data or dt.datetime.now(ZoneInfo(cal["fuso_orario"])).date().isoformat()

    voci = [v for v in cal["voci"] if v["tipo"] == a.tipo and v["data"] == oggi and (not a.ora or v["ora"] == a.ora)]
    if not voci:
        print(f"Niente da pubblicare: nessun {a.tipo} in calendario per {oggi}" + (f" alle {a.ora}" if a.ora else "") + ".")
        return
    v = voci[0]
    print(f"Contenuto: {v['id']} ({v['titolo']}) del {v['data']} ore {v['ora']}")

    if any(p["id"] == v["id"] for p in reg["pubblicati"]):
        print("Gia' nel registro: non ripubblico.")
        return

    recenti = api("GET", f"{ig}/media", {"fields": "id,caption,permalink,timestamp", "limit": 30})
    for m in recenti.get("data", []):
        if (m.get("caption") or "").strip() == v["didascalia"].strip():
            print(f"Didascalia gia' presente su Instagram ({m['permalink']}): aggiorno solo il registro.")
            reg["pubblicati"].append({"id": v["id"], "media_id": m["id"], "permalink": m.get("permalink"),
                                      "pubblicato_il": m.get("timestamp"), "nota": "trovato gia' pubblicato"})
            if not a.dry_run:
                salva(reg)
            return

    lim = api("GET", f"{ig}/content_publishing_limit", {"fields": "config,quota_usage"})["data"][0]
    usati, tot = lim.get("quota_usage", 0), lim["config"]["quota_total"]
    print(f"Limite pubblicazioni: {usati}/{tot} nelle ultime 24 ore.")
    if usati >= tot:
        raise SystemExit("ERRORE: limite di pubblicazione raggiunto.")

    base = os.environ.get("IG_MEDIA_BASE", cal["base_url_media"])
    urls = [f"{base}/{p}" for p in v["media"]]
    mancanti = [u for u in urls if not url_ok(u)]
    if mancanti:
        raise SystemExit(f"ERRORE: media non raggiungibili: {mancanti}")
    print(f"Media raggiungibili: {len(urls)}")

    if a.dry_run:
        print("DRY-RUN: mi fermo prima di creare i contenitori.")
        return

    if a.tipo == "post":
        figli = []
        for u in urls:
            c = api("POST", f"{ig}/media", {"image_url": u, "is_carousel_item": "true"})
            figli.append(c["id"])
        for c in figli:
            attendi(c)
        cont = api("POST", f"{ig}/media", {"media_type": "CAROUSEL", "children": ",".join(figli),
                                           "caption": v["didascalia"]})["id"]
    else:
        cont = api("POST", f"{ig}/media", {"media_type": "REELS", "video_url": urls[0],
                                           "caption": v["didascalia"], "share_to_feed": "true"})["id"]
    attendi(cont)
    pub = api("POST", f"{ig}/media_publish", {"creation_id": cont})
    media_id = pub["id"]
    info = api("GET", media_id, {"fields": "permalink,timestamp"})
    reg["pubblicati"].append({"id": v["id"], "media_id": media_id, "permalink": info.get("permalink"),
                              "pubblicato_il": info.get("timestamp")})
    salva(reg)
    print(f"PUBBLICATO {v['id']}: {info.get('permalink')}")


def salva(reg):
    with open(REG, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
