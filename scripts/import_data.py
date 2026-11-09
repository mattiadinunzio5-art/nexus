"""Importa dati aperti, con fonte e licenza, nella Biblioteca NEXUS (condivisa, sola lettura).

Uso (dalla cartella del repository):
    scripts/py.sh scripts/import_data.py series   [--sources world-bank owid eurostat ecb] [--limit N] [--resume]
    scripts/py.sh scripts/import_data.py events   [--limit N] [--resume]      # Wikidata + estratti Wikipedia
    scripts/py.sh scripts/import_data.py graph    [--limit N] [--resume]      # entità e relazioni da Wikidata
    scripts/py.sh scripts/import_data.py biblio   [--limit N]                 # opere da Crossref / Open Library
    scripts/py.sh scripts/import_data.py docs     [--limit N]                 # classici di pubblico dominio (Gutenberg)
    scripts/py.sh scripts/import_data.py discovery                            # rilevatori deterministici sulla Biblioteca
    scripts/py.sh scripts/import_data.py all      [--profile online|full]     # tutto, nell'ordine
    scripts/py.sh scripts/import_data.py stats                                # conteggi e dimensione del database
    scripts/py.sh scripts/import_data.py delete --origin wikidata --yes       # cancella un lotto importato

Il database è quello configurato (NEXUS_DATABASE_URL nel file .env). Fai prima un backup:
    scripts/py.sh scripts/backup_db.py
Profili: "online" rispetta i limiti del piano gratuito (database da 500 MB), "full" è per il computer locale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from nexus.core.config import get_settings  # noqa: E402
from nexus.database.migrate import upgrade_to_head  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.importers import common  # noqa: E402

PROFILES = {
    # limiti per area (None = nessun limite)
    "online": {"series": 3500, "events": 25000, "graph": 80000, "biblio": 400, "docs": 25},
    "full": {"series": None, "events": None, "graph": None, "biblio": 2000, "docs": 80},
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("area", choices=["series", "events", "graph", "biblio", "docs", "discovery", "all", "stats", "delete"])
    p.add_argument("--limit", type=int, default=None, help="numero massimo di elementi da elaborare (per prove)")
    p.add_argument("--resume", action="store_true", help="riprende da dove si era interrotto")
    p.add_argument("--profile", choices=list(PROFILES), default="online")
    p.add_argument("--sources", nargs="*", default=None, help="solo alcune fonti (series)")
    p.add_argument("--origin", help="lotto da cancellare (delete)")
    p.add_argument("--yes", action="store_true", help="conferma la cancellazione (delete)")
    p.add_argument("--pause", type=float, default=None, help="secondi di pausa tra le richieste")
    a = p.parse_args()

    settings = get_settings()
    upgrade_to_head(settings.database_url)
    database = Database(settings.database_url)

    if a.area == "delete":
        if not a.origin or not a.yes:
            print("Indica --origin <lotto> e conferma con --yes (es. --origin wikidata --yes).")
            return 2
        print(common.delete_origin(database, a.origin))
        return 0
    if a.area == "stats":
        from nexus.importers.stats import print_stats

        print_stats(database)
        return 0

    areas = ["series", "events", "graph", "biblio", "docs", "discovery"] if a.area == "all" else [a.area]
    for area in areas:
        limit = a.limit if a.limit is not None else PROFILES[a.profile].get(area)
        run = common.Run(database, settings, area=area, limit=limit, resume=a.resume,
                         pause=a.pause if a.pause is not None else (1.0 if area in ("events", "graph") else 0.25))
        print(f"\n=== {area} (limite: {limit or 'nessuno'}) ===", flush=True)
        try:
            if area == "series":
                from nexus.importers.series import run_series

                run_series(run, a.sources)
            elif area == "events":
                from nexus.importers.wikidata import run_events

                run_events(run)
            elif area == "graph":
                from nexus.importers.wikidata import run_graph

                run_graph(run)
            elif area == "biblio":
                from nexus.importers.biblio import run_biblio

                run_biblio(run)
            elif area == "docs":
                from nexus.importers.docs import run_docs

                run_docs(run)
            elif area == "discovery":
                from nexus.importers.discovery_run import run_discovery

                run_discovery(run)
        except KeyboardInterrupt:
            run.report.note("Interrotto dall'utente: rilancia con --resume per continuare.")
            print(run.report.render())
            run.close()
            return 130
        print(run.report.render())
        print(f"Log errori: {run.log_path}" if run.log_path.exists() else "Nessun errore.")
        run.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
