#!/usr/bin/env python3
"""Raccoglie le statistiche di Instagram (API Meta) e TikTok (via Buffer) per nexus.analytic.

Uso:
    python3 scripts/analytics/raccogli_metriche.py [--salva] [--report]

- Instagram: views, reach, saved, shares, total_interactions per ogni media.
- TikTok: metriche che Buffer riceve da TikTok (Video Views, Reach, Avg. Watch Time...).
- --salva  aggiorna social/analytics/metriche.json (ultima lettura per contenuto + storico).
- --report stampa una classifica e una sintesi per fascia oraria e per formato.
I token NON sono nel codice: li aggiunge il proxy dell'ambiente.
"""
import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "social", "analytics", "metriche.json")
IG = "17841414501167504"
GRAPH = "https://graph.facebook.com/v21.0"
BUFFER_ORG = "6afa122864a4f6318f8f3b03"
TZ = ZoneInfo("Europe/Rome")


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def instagram():
    out = []
    url = f"{GRAPH}/{IG}/media?fields=id,caption,timestamp,media_type,media_product_type,like_count,comments_count,permalink&limit=50"
    for m in get(url).get("data", []):
        try:
            r = get(f"{GRAPH}/{m['id']}/insights?metric=views,reach,saved,shares,total_interactions")
            ins = {x["name"]: x["values"][0]["value"] for x in r["data"]}
        except urllib.error.HTTPError:
            ins = {}
        out.append({
            "rete": "instagram",
            "id": m["id"],
            "formato": "reel" if m.get("media_type") == "VIDEO" else "carosello" if m.get("media_type") == "CAROUSEL_ALBUM" else m.get("media_type", "").lower(),
            "pubblicato": m["timestamp"],
            "titolo": (m.get("caption") or "").split("\n")[0][:80],
            "link": m.get("permalink"),
            "views": ins.get("views"),
            "reach": ins.get("reach"),
            "like": m.get("like_count"),
            "commenti": m.get("comments_count"),
            "salvataggi": ins.get("saved"),
            "condivisioni": ins.get("shares"),
            "interazioni": ins.get("total_interactions"),
        })
    return out


def tiktok():
    q = """query($org: OrganizationId!) { posts(first: 100, input: {organizationId: $org, filter: {status: [sent]}}) {
        edges { node { id text sentAt dueAt externalLink channelService metrics { name value } } } } }"""
    req = urllib.request.Request("https://api.buffer.com", method="POST",
                                 data=json.dumps({"query": q, "variables": {"org": BUFFER_ORG}}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    out = []
    for e in d["data"]["posts"]["edges"]:
        n = e["node"]
        if n.get("channelService") not in (None, "tiktok"):
            continue
        m = {x["name"]: x["value"] for x in n.get("metrics") or []}
        out.append({
            "rete": "tiktok",
            "id": n["id"],
            "formato": "video",
            "pubblicato": n.get("sentAt") or n.get("dueAt"),
            "titolo": (n.get("text") or "").split("\n")[0][:80],
            "link": n.get("externalLink"),
            "views": m.get("Video Views"),
            "reach": m.get("Reach"),
            "like": m.get("Reactions"),
            "commenti": m.get("Comments"),
            "condivisioni": m.get("Shares"),
            "tempo_medio_s": m.get("Avg. Watch Time (sec)"),
            "engagement_pct": m.get("Eng. Rate"),
        })
    return out


def arricchisci(rows):
    now = dt.datetime.now(dt.timezone.utc)
    for r in rows:
        t = dt.datetime.fromisoformat(r["pubblicato"].replace("Z", "+00:00").replace("+0000", "+00:00"))
        loc = t.astimezone(TZ)
        r["ora_locale"] = loc.strftime("%H:%M")
        r["giorno"] = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"][loc.weekday()]
        r["data"] = loc.date().isoformat()
        r["ore_dalla_pubblicazione"] = round((now - t).total_seconds() / 3600, 1)
    return rows


def fascia(hhmm):
    h = int(hhmm[:2])
    return "mattina (6-12)" if 6 <= h < 12 else "pranzo (12-15)" if h < 15 else "pomeriggio (15-18)" if h < 18 else "sera (18-22)" if h < 22 else "notte"


def report(rows):
    for rete in ("tiktok", "instagram"):
        rr = [r for r in rows if r["rete"] == rete and r.get("views") is not None]
        if not rr:
            continue
        print(f"\n=== {rete.upper()} ({len(rr)} contenuti, {sum(r['views'] for r in rr)} visualizzazioni) ===")
        for r in sorted(rr, key=lambda r: -r["views"])[:10]:
            extra = f" | {r['tempo_medio_s']}s visti" if r.get("tempo_medio_s") is not None else ""
            print(f"{r['views']:>6} vis | {r['formato']:9} | {r['data']} {r['ora_locale']} {r['giorno']}{extra} | {r['titolo'][:50]}")
        agg = {}
        for r in rr:
            for k in (fascia(r["ora_locale"]), r["formato"]):
                a = agg.setdefault(k, [0, 0])
                a[0] += r["views"]; a[1] += 1
        print("Media visualizzazioni per gruppo:", {k: round(v[0] / v[1]) for k, v in agg.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salva", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    rows = []
    for fn in (instagram, tiktok):
        try:
            rows += fn()
        except Exception as e:  # una rete non deve bloccare l'altra
            print(f"ATTENZIONE {fn.__name__}: {e}")
    rows = arricchisci(rows)
    if a.salva:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        db = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"contenuti": {}, "storico": []}
        oggi = dt.datetime.now(TZ).isoformat(timespec="minutes")
        for r in rows:
            db["contenuti"][f"{r['rete']}:{r['id']}"] = {**r, "letto_il": oggi}
            db["storico"].append({"k": f"{r['rete']}:{r['id']}", "t": oggi, "views": r.get("views"),
                                  "ore": r["ore_dalla_pubblicazione"]})
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=1)
        print(f"Salvati {len(rows)} contenuti in {OUT}")
    if a.report or not a.salva:
        report(rows)


if __name__ == "__main__":
    main()
