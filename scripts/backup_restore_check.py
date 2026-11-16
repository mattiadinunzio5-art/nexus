"""Prova di ripristino completo di un backup PostgreSQL in un database temporaneo.

Uso (in CI, con un PostgreSQL di servizio):

    python scripts/backup_restore_check.py seed     postgresql://…/sorgente      # crea dati reali tramite l'API
    python scripts/backup_restore_check.py compare  postgresql://…/sorgente  postgresql://…/ripristino
    python scripts/backup_restore_check.py app      postgresql://…/ripristino   # l'app legge il database ripristinato

«compare» confronta tabella per tabella numero di righe e un'impronta (MD5) del contenuto ordinato;
esce con codice 1 alla prima differenza. Non scrive mai sul database di origine (solo SELECT).
Il dump e il ripristino li esegue il workflow con pg_dump / pg_restore, con le stesse opzioni del
backup settimanale (.github/workflows/backup-db.yml).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import create_engine, inspect, text  # noqa: E402

from nexus.database.session import normalize_url  # noqa: E402

H = {"X-Nexus-Client": "web"}


def _client(url: str, data_dir: Path):
    from fastapi.testclient import TestClient

    from nexus.core.config import Settings
    from nexus.main import create_app

    s = Settings(env="test", database_url=url, auto_migrate=True, data_dir=data_dir, secret_key="backup-restore-check")
    return TestClient(create_app(s))


def seed(url: str) -> int:
    """Dati di prova creati come li crea un utente (API), in tutte le aree principali."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp, _client(url, Path(tmp)) as c:
        def ok(r, code=201):
            assert r.status_code == code, r.text
            return r.json()

        p = ok(c.post("/api/projects", json={"title": "Prova di ripristino"}, headers=H))
        s = ok(c.post("/api/sources", json={"title": "Fonte di prova", "authors": ["A. Rossi"], "year": 1950, "evidence_class": "primary"}, headers=H))
        e = ok(c.post("/api/history/events", json={"title": "Evento di prova", "start_year": 1948, "start_month": 4}, headers=H))
        ok(c.post(f"/api/history/events/{e['id']}/knowledge", json={"content": "Informazione datata", "published_on": "1948-05-01"}, headers=H), 200)
        ok(c.post("/api/finance/series/upload", files={"file": ("s.csv", b"anno,valore\n2001,1\n2002,2\n2003,3\n")},
                  data={"name": "Serie di prova", "source_label": "Prova"}, headers=H))
        ok(c.post("/api/documents", files={"file": ("d.txt", "Testo di prova: àèìòù «virgolette» e simboli €.".encode())}, data={}, headers=H))
        r = ok(c.post("/api/reports", json={"title": "Rapporto di prova", "project_id": p["id"]}, headers=H))
        sec = r["sections"][3]
        ok(c.put(f"/api/reports/{r['id']}/sections/{sec['id']}", json={"body": f"Nel 1948 il dato era 3 [@{s['id']}, p. 2]."}, headers=H), 200)
        ok(c.put(f"/api/reports/{r['id']}/sections/{sec['id']}", json={"body": f"Nel 1948 il dato era 4 [@{s['id']}, p. 2]."}, headers=H), 200)
    print("Dati di prova creati.")
    return 0


def snapshot(url: str) -> dict[str, tuple[int, str]]:
    eng = create_engine(normalize_url(url))
    out = {}
    with eng.connect() as conn:
        for t in sorted(inspect(conn).get_table_names(schema="public")):
            n = conn.execute(text(f'SELECT count(*) FROM public."{t}"')).scalar_one()
            h = conn.execute(text(f'SELECT md5(coalesce(string_agg(x::text, \'|\' ORDER BY x::text), \'\')) FROM public."{t}" AS x')).scalar_one()
            out[t] = (n, h)
    eng.dispose()
    return out


def compare(src: str, dst: str) -> int:
    a, b = snapshot(src), snapshot(dst)
    problems = []
    for t in sorted(set(a) | set(b)):
        if t not in b:
            problems.append(f"tabella mancante nel ripristino: {t}")
        elif t not in a:
            problems.append(f"tabella in più nel ripristino: {t}")
        elif a[t] != b[t]:
            problems.append(f"{t}: origine {a[t][0]} righe, ripristino {b[t][0]} righe (impronte {'uguali' if a[t][1] == b[t][1] else 'diverse'})")
    rows = sum(n for n, _ in a.values())
    if problems:
        print("RIPRISTINO NON CONFORME:\n  " + "\n  ".join(problems))
        return 1
    print(f"Ripristino conforme: {len(a)} tabelle, {rows} righe, contenuto identico (MD5 per tabella).")
    return 0


def app_check(url: str) -> int:
    """L'app parte sul database ripristinato (migrazioni già al livello attuale) e legge i dati."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp, _client(url, Path(tmp)) as c:
        checks = {
            "progetti": len(c.get("/api/projects").json()) >= 1,
            "fonti": any(x["title"] == "Fonte di prova" for x in c.get("/api/sources").json()),
            "eventi": len(c.get("/api/history/events").json()) >= 1,
            "rapporti": len(c.get("/api/reports").json()) >= 1,
            "documenti (ricerca nel testo)": bool(c.get("/api/research/search?q=virgolette").json()["hits"]),
        }
        rep = c.get("/api/reports").json()[0]
        full = c.get(f"/api/reports/{rep['id']}").json()
        sec = full["sections"][3]
        checks["versioni del rapporto"] = len(c.get(f"/api/reports/{rep['id']}/sections/{sec['id']}/versions").json()) >= 1
    bad = [k for k, v in checks.items() if not v]
    print("Lettura dal database ripristinato: " + ("OK (" + ", ".join(checks) + ")" if not bad else "PROBLEMI: " + ", ".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    raise SystemExit({"seed": seed, "compare": compare, "app": app_check}[cmd](*args))
