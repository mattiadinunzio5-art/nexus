#!/usr/bin/env python3
"""Programma su Buffer (canale TikTok nexus.analytic) i video del calendario.

Uso:
    python3 scripts/tiktok/programma_buffer.py [--giorni 3] [--dry-run] [--solo ID]

- Legge social/tiktok/calendario.json e social/tiktok/registro.json.
- Programma (mode customScheduled) i video con data tra oggi e oggi+giorni,
  la cui ora di uscita e' almeno 20 minuti nel futuro. Il piano gratuito di Buffer
  tiene al massimo 10 post in coda: con 2 video al giorno e --giorni 3 (al massimo 8 post) la coda resta sotto il limite.
- Non duplica mai: salta se l'id e' nel registro OPPURE se su Buffer esiste gia'
  un post del canale con lo stesso testo.
- La chiave API NON e' nel codice: il proxy dell'ambiente aggiunge l'header
  Authorization alle richieste verso api.buffer.com (oppure variabile BUFFER_API_KEY).
- Scrive l'esito nel registro; il commit lo fa chi lancia lo script.
"""
import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAL = os.path.join(ROOT, "social", "tiktok", "calendario.json")
REG = os.path.join(ROOT, "social", "tiktok", "registro.json")
API = "https://api.buffer.com"


def gql(query, variables=None):
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("BUFFER_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ERRORE Buffer HTTP {e.code}: {e.read().decode(errors='replace')}")
    if out.get("errors"):
        raise SystemExit(f"ERRORE Buffer: {out['errors']}")
    return out["data"]


def testi_esistenti(org_id, channel_id):
    q = """query($org: OrganizationId!, $ch: [ChannelId!], $after: String) {
      posts(first: 50, after: $after, input: {organizationId: $org, filter: {channelIds: $ch}}) {
        edges { node { id text status dueAt } }
        pageInfo { hasNextPage endCursor }
      }
    }"""
    testi, after = {}, None
    for _ in range(20):
        d = gql(q, {"org": org_id, "ch": [channel_id], "after": after})["posts"]
        for e in d["edges"]:
            n = e["node"]
            testi[(n.get("text") or "").strip()] = n
        if not d["pageInfo"]["hasNextPage"]:
            break
        after = d["pageInfo"]["endCursor"]
    return testi


def url_ok(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
            return r.status == 200
    except urllib.error.URLError:
        return False


def salva(reg):
    with open(REG, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--giorni", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--solo", help="programma solo questo id (es. S1G1-tiktok)")
    a = ap.parse_args()

    cal = json.load(open(CAL, encoding="utf-8"))
    reg = json.load(open(REG, encoding="utf-8")) if os.path.exists(REG) else {"programmati": []}
    tz = ZoneInfo(cal["fuso_orario"])
    ora = dt.datetime.now(tz)
    oggi = ora.date()
    fine = oggi + dt.timedelta(days=a.giorni)
    fatti = {p["id"] for p in reg["programmati"]}

    esistenti = testi_esistenti(cal["organizzazione_buffer_id"], cal["canale_buffer_id"])
    base = os.environ.get("TIKTOK_MEDIA_BASE", cal["base_url_media"])

    n = 0
    for v in cal["voci"]:
        if a.solo and v["id"] != a.solo:
            continue
        giorno = dt.date.fromisoformat(v["data"])
        if not (oggi <= giorno <= fine):
            continue
        hh, mm = map(int, v["ora"].split(":"))
        uscita = dt.datetime(giorno.year, giorno.month, giorno.day, hh, mm, tzinfo=tz)
        if v["id"] in fatti:
            print(f"{v['id']}: gia' nel registro, salto.")
            continue
        gia = esistenti.get(v["didascalia"].strip())
        if gia:
            print(f"{v['id']}: gia' presente su Buffer ({gia['status']}), aggiorno solo il registro.")
            reg["programmati"].append({"id": v["id"], "buffer_post_id": gia["id"], "dueAt": gia.get("dueAt"),
                                       "nota": "trovato gia' su Buffer"})
            if not a.dry_run:
                salva(reg)
            continue
        if uscita < ora + dt.timedelta(minutes=20):
            print(f"{v['id']}: orario {uscita.isoformat()} troppo vicino o passato, salto.")
            continue
        url = f"{base}/{v['media']}"
        if not url_ok(url):
            raise SystemExit(f"ERRORE: video non raggiungibile: {url}")
        video = {"url": url}
        if v.get("copertina_ms") is not None:  # copertina = fotogramma scelto (Buffer non accetta immagini per TikTok)
            video["metadata"] = {"thumbnailOffset": int(v["copertina_ms"])}
        due = uscita.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        print(f"{v['id']}: programmo per {uscita.isoformat()} ({due}) con {url}")
        if a.dry_run:
            continue
        m = """mutation($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess { post { id dueAt status } }
            ... on MutationError { message }
          }
        }"""
        inp = {"channelId": cal["canale_buffer_id"], "text": v["didascalia"], "schedulingType": "automatic",
               "mode": "customScheduled", "dueAt": due, "needsApproval": False,
               "assets": [{"video": video}],
               "metadata": {"tiktok": {"title": v["titolo"][:90]}}}
        res = gql(m, {"input": inp})["createPost"]
        if "post" not in res:
            raise SystemExit(f"ERRORE createPost {v['id']}: {res.get('message')}")
        p = res["post"]
        reg["programmati"].append({"id": v["id"], "buffer_post_id": p["id"], "dueAt": p.get("dueAt"),
                                   "stato": p.get("status")})
        salva(reg)
        n += 1
        print(f"PROGRAMMATO {v['id']}: {p['id']} {p.get('dueAt')} {p.get('status')}")
    print(f"Fatto: {n} nuovi video programmati.")


if __name__ == "__main__":
    main()
