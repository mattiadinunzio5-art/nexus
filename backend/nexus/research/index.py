"""Indicizzazione e recupero dei segmenti.

- Ricerca testuale: SQLite FTS5 con ranking BM25 (fallback LIKE su altri DB).
- Ricerca semantica: per impostazione predefinita LSA (TF-IDF + SVD troncata,
  scikit-learn), calcolata localmente sull'archivio dell'utente; in alternativa
  embedding neurali con sentence-transformers se installato e configurato.
- Ricerca ibrida: fusione dei due ranking con Reciprocal Rank Fusion (RRF).

Il metodo effettivamente usato è sempre riportato nella risposta.
"""

from __future__ import annotations

import re

import threading
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import DocumentChunk
from .text import terms

FTS_TABLE = "chunks_fts"


# --- FTS ---------------------------------------------------------------------


def fts_available(db: Session) -> bool:
    if db.get_bind().dialect.name != "sqlite":
        return False
    row = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"), {"n": FTS_TABLE}).first()
    return row is not None


def fts_add(db: Session, chunks: list[DocumentChunk]) -> None:
    if not fts_available(db):
        return
    db.execute(
        text(f"INSERT INTO {FTS_TABLE}(rowid, text, owner_id, document_id) VALUES (:id, :t, :o, :d)"),
        [{"id": c.id, "t": c.text, "o": c.owner_id, "d": c.document_id} for c in chunks],
    )


def fts_delete_document(db: Session, document_id: int) -> None:
    if fts_available(db):
        db.execute(text(f"DELETE FROM {FTS_TABLE} WHERE document_id = :d"), {"d": document_id})


def _fts_query(q: str) -> str:
    # Ogni termine tra virgolette: nessuna sintassi FTS controllabile dall'utente.
    toks = terms(q)
    return " OR ".join(f'"{t}"*' for t in toks[:20])


def text_search(db: Session, owner_id: int, q: str, limit: int, document_ids: list[int] | None = None) -> list[tuple[int, float]]:
    """Restituisce (chunk_id, punteggio) ordinati per rilevanza."""
    if fts_available(db):
        match = _fts_query(q)
        if not match:
            return []
        sql = f"SELECT rowid, bm25({FTS_TABLE}) AS s FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH :m AND owner_id = :o"
        params: dict = {"m": match, "o": owner_id}
        if document_ids:
            sql += f" AND document_id IN ({','.join(str(int(d)) for d in document_ids)})"
        sql += " ORDER BY s LIMIT :l"
        params["l"] = limit
        return [(int(r[0]), float(-r[1])) for r in db.execute(text(sql), params)]
    toks = terms(q)[:8]
    if db.get_bind().dialect.name == "postgresql" and toks:
        # PostgreSQL: ricerca full-text nel database (indice GIN, migrazione 0013), senza caricare i testi in memoria.
        tsq = " | ".join(re.sub(r"[^\w]", "", t) for t in toks if re.sub(r"[^\w]", "", t))
        if not tsq:
            return []
        sql = ("SELECT id, ts_rank(to_tsvector('simple', text), to_tsquery('simple', :q)) AS s FROM document_chunks "
               "WHERE owner_id = :o AND to_tsvector('simple', text) @@ to_tsquery('simple', :q)")
        params2: dict = {"q": tsq, "o": owner_id, "l": limit}
        if document_ids:
            sql += f" AND document_id IN ({','.join(str(int(d)) for d in document_ids)})"
        sql += " ORDER BY s DESC LIMIT :l"
        return [(int(r[0]), float(r[1])) for r in db.execute(text(sql), params2)]
    # Fallback portabile (altri database).
    if not toks:
        return []
    stmt = select(DocumentChunk.id, DocumentChunk.text).where(DocumentChunk.owner_id == owner_id)
    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
    scored = []
    for cid, t in db.execute(stmt):
        low = t.lower()
        s = sum(low.count(tok) for tok in toks)
        if s:
            scored.append((cid, float(s)))
    return sorted(scored, key=lambda x: -x[1])[:limit]


# --- Semantica ---------------------------------------------------------------


@dataclass
class _LSAModel:
    version: tuple
    ids: np.ndarray
    vectorizer: object
    svd: object | None
    matrix: np.ndarray = field(repr=False)


MAX_FEATURES = 15000  # termini del vocabolario
N_COMPONENTS = 100  # dimensioni LSA
MAX_CHUNKS = 5000  # segmenti più recenti indicizzati per utente
MAX_MODELS = 3  # indici tenuti in memoria (i meno usati vengono scartati)


class SemanticIndex:
    """Indice semantico in memoria per utente, ricostruito quando l'archivio cambia (al massimo MAX_MODELS in memoria)."""

    def __init__(self) -> None:
        from collections import OrderedDict

        self._cache: OrderedDict[int, _LSAModel] = OrderedDict()
        self._lock = threading.Lock()

    def has(self, owner_id: int) -> bool:
        return owner_id in self._cache

    def invalidate(self, owner_id: int) -> None:
        with self._lock:
            self._cache.pop(owner_id, None)

    def _version(self, db: Session, owner_id: int) -> tuple:
        row = db.execute(
            text("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM document_chunks WHERE owner_id = :o"), {"o": owner_id}
        ).first()
        return (int(row[0]), int(row[1]))

    def _build(self, db: Session, owner_id: int, version: tuple) -> _LSAModel | None:
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        rows = db.execute(
            select(DocumentChunk.id, DocumentChunk.text).where(DocumentChunk.owner_id == owner_id).order_by(DocumentChunk.id.desc()).limit(MAX_CHUNKS)
        ).all()
        if not rows:
            return None
        ids = np.array([r[0] for r in rows])
        # Vocabolario limitato e float32: sul server gratuito (512 MB) l'indice deve restare piccolo.
        vec = TfidfVectorizer(analyzer=lambda s: terms(s), sublinear_tf=True, min_df=2 if len(rows) > 2000 else 1,
                              max_features=MAX_FEATURES, dtype=np.float32)
        tfidf = vec.fit_transform([r[1] for r in rows])
        del rows
        svd = None
        n_comp = min(N_COMPONENTS, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
        if n_comp >= 2 and tfidf.shape[0] >= 200:  # su archivi piccoli la TF-IDF piena è già leggera e più precisa
            svd = TruncatedSVD(n_components=n_comp, algorithm="randomized", n_iter=4, random_state=0)
            mat = svd.fit_transform(tfidf).astype(np.float32)
        else:
            mat = tfidf.toarray()
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        mat = mat / np.where(norms == 0, 1, norms)
        return _LSAModel(version, ids, vec, svd, mat)

    def search_lsa(self, db: Session, owner_id: int, q: str, limit: int) -> list[tuple[int, float]]:
        version = self._version(db, owner_id)
        with self._lock:
            model = self._cache.get(owner_id)
            if model is None or model.version != version:
                self._cache.pop(owner_id, None)
                while len(self._cache) >= MAX_MODELS:
                    self._cache.popitem(last=False)
                import gc

                gc.collect()
                model = self._build(db, owner_id, version)
                if model is None:
                    return []
                self._cache[owner_id] = model
            self._cache.move_to_end(owner_id)
        qv = model.vectorizer.transform([q]).astype(np.float32)
        if qv.nnz == 0:
            return []
        qv = model.svd.transform(qv) if model.svd is not None else qv.toarray()
        n = np.linalg.norm(qv)
        if n == 0:
            return []
        sims = model.matrix @ (qv[0] / n)
        order = np.argsort(-sims)[:limit]
        return [(int(model.ids[i]), float(sims[i])) for i in order if sims[i] > 0.05]


semantic_index = SemanticIndex()


class NeuralEmbedder:
    """Embedding con sentence-transformers (facoltativo, locale)."""

    _models: dict[str, object] = {}

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - dipende dall'installazione
            raise RuntimeError("sentence-transformers non installato (vedi requirements-ml.txt)") from exc
        if model_name not in self._models:
            self._models[model_name] = SentenceTransformer(model_name)
        self.model = self._models[model_name]
        self.name = model_name

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def neural_search(db: Session, owner_id: int, embedder: NeuralEmbedder, q: str, limit: int) -> list[tuple[int, float]]:
    rows = db.execute(
        select(DocumentChunk.id, DocumentChunk.embedding).where(
            DocumentChunk.owner_id == owner_id, DocumentChunk.embedding_model == embedder.name
        )
    ).all()
    if not rows:
        return []
    mat = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
    sims = mat @ embedder.encode([q])[0]
    order = np.argsort(-sims)[:limit]
    return [(int(rows[i][0]), float(sims[i])) for i in order]


# --- Ibrida ------------------------------------------------------------------


def rrf(rankings: list[list[tuple[int, float]]], k: int = 60) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, (cid, _) in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])
