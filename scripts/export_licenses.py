"""Genera website/src/content/dataPolicy.ts dal registro delle licenze del backend (unica fonte di verità).

Uso: dalla cartella del repository, ``backend/.venv/bin/python scripts/export_licenses.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from nexus.core import licenses  # noqa: E402
from nexus.core.locale import current_lang  # noqa: E402


def entries(lang: str) -> list[dict]:
    token = current_lang.set(lang)
    try:
        return licenses.registry()
    finally:
        current_lang.reset(token)


OUT = ROOT / "website" / "src" / "content" / "dataPolicy.ts"


def render() -> str:
    data = {"version": licenses.POLICY_VERSION, "updated": licenses.POLICY_DATE, "library": list(licenses.LIBRARY_LICENSES),
            "it": entries("it"), "en": entries("en")}
    return (
        "/** Generato da scripts/export_licenses.py a partire da backend/nexus/core/licenses.py: non modificare a mano. */\n"
        "export type Permission = 'yes' | 'conditional' | 'no';\n"
        "export interface LicenseEntry {\n"
        "  id: string; name: string; publisher: string; homepage: string; applies_to: string; license: string; license_url: string;\n"
        "  attribution: string; commercial: Permission; commercial_note: string; redistribution: Permission; redistribution_note: string;\n"
        "  territorial: string; modifications: string; terms_url: string; verified_on: string; status: string; notes: string;\n"
        "}\n"
        "export const DATA_POLICY: { version: string; updated: string; library: string[]; it: LicenseEntry[]; en: LicenseEntry[] } =\n"
        + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    )


def main() -> None:
    OUT.write_text(render(), encoding="utf-8")
    print(f"Scritto {OUT.relative_to(ROOT)} ({len(licenses.LICENSES)} schede)")


if __name__ == "__main__":
    main()
