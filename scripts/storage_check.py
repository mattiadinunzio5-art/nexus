"""Controllo di integrità dei file: database ↔ storage (locale o Supabase).

Uso:
    scripts/py.sh scripts/storage_check.py            # solo controllo (sola lettura), esito registrato
    scripts/py.sh scripts/storage_check.py --fix      # rimuove i file orfani e le copie scadute del cestino (con verifica)
    scripts/py.sh scripts/storage_check.py --json     # esito completo in JSON

Segnala: documenti senza file, file senza documento (orfani), dimensioni diverse, contenuto alterato
(SHA-256 su un campione), copie del cestino mancanti o scadute. Codice di uscita 1 se ci sono problemi.
I file referenziati da un documento non vengono mai rimossi.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from nexus.core.config import get_settings  # noqa: E402
from nexus.database.session import Database  # noqa: E402
from nexus.services import filesafety  # noqa: E402


def main(argv: list[str]) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    with db.session_factory() as s:
        chk = filesafety.run_check(s, settings, "script")
        res = chk.result
        if "--json" in argv:
            print(json.dumps(filesafety.check_out(chk), indent=1, ensure_ascii=False))
        else:
            print(f"Controllo n. {chk.id}: {chk.status}")
            if "error" in res:
                print("  Errore:", res["error"])
            else:
                print(f"  Documenti: {res['documents']} · file nello storage: {res['files']} · cestino: {res['trash_items']} · SHA-256 verificati: {res['hash_checked']}")
                for k, label in (("missing_files", "Documenti senza file"), ("size_mismatch", "Dimensione diversa"), ("hash_mismatch", "Contenuto alterato"),
                                 ("orphan_files", "File orfani"), ("trash_missing", "Copie del cestino mancanti"), ("expired_trash", "Cestino scaduto")):
                    if res[k]:
                        print(f"  {label}: {len(res[k])}")
                        for x in res[k][:20]:
                            print("    -", x)
        if "--fix" in argv:
            out = filesafety.cleanup(s, settings, None, confirm=True)
            print(f"Pulizia: {len(out['removed_orphans'])} file orfani rimossi, {len(out['purged_trash'])} elementi del cestino eliminati, "
                  f"{len(out['failed'])} non riusciti.")
            for f in out["failed"]:
                print("    !", f)
    db.engine.dispose()
    return 0 if chk.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
