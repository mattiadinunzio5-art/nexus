"""Archivio documenti della Biblioteca: classici dell'economia di pubblico dominio da Project Gutenberg.

Si scarica da un mirror ufficiale (gutenberg.pglaf.org), come chiede la policy di Gutenberg per gli accessi
automatici, con pause lunghe e solo un elenco breve e dichiarato di opere. Il titolo nel file deve corrispondere
a quello atteso, altrimenti l'opera si salta (nessun ID «a memoria» viene accettato senza verifica).
Indicizzazione con il motore esistente (BM25 + semantica) tramite documents.import_bytes.
"""

from __future__ import annotations

import time

import httpx
from sqlalchemy import select

from ..models import Document
from ..services import documents
from .common import Run
from .wikidata import UA

MIRROR = "https://gutenberg.pglaf.org"
LICENSE = ("Project Gutenberg: opera di pubblico dominio negli Stati Uniti; licenza Project Gutenberg "
           "(https://www.gutenberg.org/policy/license.html). Verificare lo status nel proprio paese.")
# (ID ebook, parola attesa nel titolo, titolo, autore)
CLASSICS = [
    (3300, "wealth of nations", "An Inquiry into the Nature and Causes of the Wealth of Nations", "Adam Smith"),
    (33310, "principles of political economy", "On the Principles of Political Economy and Taxation", "David Ricardo"),
    (30107, "principles of political economy", "Principles of Political Economy", "John Stuart Mill"),
    (4359, "lombard street", "Lombard Street: A Description of the Money Market", "Walter Bagehot"),
    (15776, "economic consequences of the peace", "The Economic Consequences of the Peace", "John Maynard Keynes"),
    (4239, "principle of population", "An Essay on the Principle of Population", "Thomas Malthus"),
    (833, "leisure class", "The Theory of the Leisure Class", "Thorstein Veblen"),
    (24518, "popular delusions", "Memoirs of Extraordinary Popular Delusions and the Madness of Crowds", "Charles Mackay"),
    (55308, "progress and poverty", "Progress and Poverty", "Henry George"),
    (67363, "moral sentiments", "The Theory of Moral Sentiments", "Adam Smith"),
]


def _path(n: int, suffix: str) -> str:
    s = str(n)
    return f"{MIRROR}/{'/'.join(s[:-1])}/{s}/{s}{suffix}"


def run_docs(run: Run, client: httpx.Client | None = None) -> None:
    c = client or httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": UA})
    for ebook, expect, title, author in CLASSICS:
        if not run.budget_left():
            break
        key = f"gutenberg:{ebook}"
        url = f"https://www.gutenberg.org/ebooks/{ebook}"
        if run.db.scalar(select(Document.id).where(Document.owner_id == run.lib.id, Document.origin_url == url)):
            run.report.add("documents", "skipped")
            continue
        data = None
        for suffix in ("-0.txt", ".txt"):
            r = c.get(_path(ebook, suffix))
            time.sleep(max(run.pause, 2.0))
            if r.status_code == 200:
                data = r.content
                break
        if data is None:
            run.error("documents", key, "testo non trovato sul mirror")
            continue
        head = data[:6000].decode("utf-8", "ignore").lower()
        if expect not in head:
            run.report.note(f"Gutenberg {ebook} saltato: il titolo nel file non corrisponde a «{title}».")
            run.report.add("documents", "skipped")
            continue
        try:
            documents.import_bytes(run.db, run.lib, run.settings, filename=f"gutenberg-{ebook}.txt", data=data, title=title,
                                   author=author, project_id=None, origin="gutenberg", origin_url=url, license_note=LICENSE)
            run.tick()
            run.report.add("documents", "created")
        except Exception as exc:  # noqa: BLE001
            run.error("documents", key, repr(exc))
