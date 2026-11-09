"""Conteggi della Biblioteca e dimensione del database."""

from __future__ import annotations

from sqlalchemy import func, select, text

from ..core.library import LIBRARY_EXTERNAL_ID


def print_stats(database) -> None:
    from ..models import (DiscoveryAnomaly, DiscoveryConnection, Document, DocumentChunk, Entity, HistoricalEvent, KnowledgeItem,
                          Observation, Relation, Series, Source, User)

    with database.session_factory() as db:
        lib = db.scalar(select(User.id).where(User.external_id == LIBRARY_EXTERNAL_ID))
        print(f"Biblioteca: {'presente (utente #' + str(lib) + ')' if lib else 'non ancora creata'}")
        for name, model, col in [("eventi", HistoricalEvent, HistoricalEvent.owner_id), ("entità", Entity, Entity.owner_id),
                                 ("relazioni", Relation, Relation.owner_id), ("fonti", Source, Source.owner_id),
                                 ("serie", Series, Series.owner_id), ("documenti", Document, Document.owner_id),
                                 ("passaggi documenti", DocumentChunk, DocumentChunk.owner_id),
                                 ("connessioni discovery", DiscoveryConnection, DiscoveryConnection.owner_id),
                                 ("anomalie discovery", DiscoveryAnomaly, DiscoveryAnomaly.owner_id)]:
            n = db.scalar(select(func.count()).select_from(model).where(col == lib)) if lib else 0
            print(f"  {name:<24}{n:>10}")
        if lib:
            obs = db.scalar(select(func.count()).select_from(Observation).join(Series, Series.id == Observation.series_id).where(Series.owner_id == lib))
            kn = db.scalar(select(func.count()).select_from(KnowledgeItem).join(HistoricalEvent).where(HistoricalEvent.owner_id == lib))
            print(f"  {'osservazioni':<24}{obs:>10}\n  {'informazioni datate':<24}{kn:>10}")
        url = str(db.get_bind().url)
        if url.startswith("postgresql"):
            size = db.scalar(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
        else:
            from pathlib import Path

            path = Path(db.get_bind().url.database or "")
            size = f"{path.stat().st_size / 1024 / 1024:.1f} MB" if path.exists() else "?"
        print(f"Dimensione del database: {size}")
