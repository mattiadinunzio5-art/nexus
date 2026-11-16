"""Archiviazione dei file originali dei documenti.

- ``local`` (predefinito): cartella dati sul computer dell'utente.
- ``supabase``: Supabase Storage, bucket privato (versione online, dove il disco del
  server non è permanente). Usa la chiave di servizio, che resta solo sul server.

Le chiavi dei file hanno sempre la forma ``uploads/<utente>/<sha256>.<tipo>``.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from ..core.config import Settings
from ..core.errors import NexusError, NotFoundError


class StorageError(NexusError):
    status_code = 502
    code = "storage_error"


class LocalStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not p.is_relative_to(self.root):
            raise NotFoundError("Percorso del file non valido.")
        return p

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes:
        p = self._path(key)
        if not p.is_file():
            raise NotFoundError("File originale non disponibile.")
        return p.read_bytes()

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.is_file():
            p.unlink()

    def stat(self, key: str) -> int | None:
        """Dimensione in byte, o None se il file non esiste."""
        p = self._path(key)
        return p.stat().st_size if p.is_file() else None

    def copy(self, src: str, dst: str) -> None:
        self.put(dst, self.get(src))

    def list(self, prefix: str) -> dict[str, int]:
        """Tutti i file sotto il prefisso (ricorsivo): chiave → dimensione."""
        base = self._path(prefix)
        if not base.is_dir():
            return {}
        return {p.relative_to(self.root).as_posix(): p.stat().st_size for p in base.rglob("*") if p.is_file()}


class SupabaseStorage:
    def __init__(self, url: str, service_key: str, bucket: str, client: httpx.Client | None = None):
        self.base = url.rstrip("/") + "/storage/v1"
        self.bucket = bucket
        self.headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
        self.http = client or httpx.Client(timeout=60.0)
        self._ready = False

    def _ensure_bucket(self) -> None:
        if self._ready:
            return
        r = self.http.get(f"{self.base}/bucket/{self.bucket}", headers=self.headers)
        if r.status_code == 200:
            self._ready = True
            return
        r = self.http.post(f"{self.base}/bucket", headers=self.headers, json={"id": self.bucket, "name": self.bucket, "public": False})
        if r.status_code not in (200, 201) and "already exists" not in r.text.lower():
            raise StorageError(f"Impossibile creare lo spazio per i documenti (HTTP {r.status_code}).")
        self._ready = True

    def _call(self, method: str, key: str, **kw) -> httpx.Response:
        self._ensure_bucket()
        try:
            return self.http.request(method, f"{self.base}/object/{self.bucket}/{key}", **kw)
        except httpx.HTTPError as exc:
            raise StorageError("Spazio documenti non raggiungibile: riprova tra poco.") from exc

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        r = self._call("POST", key, content=data, headers={**self.headers, "Content-Type": content_type, "x-upsert": "true"})
        if r.status_code not in (200, 201):
            raise StorageError(f"Salvataggio del file non riuscito (HTTP {r.status_code}).")

    def get(self, key: str) -> bytes:
        r = self._call("GET", key, headers=self.headers)
        if r.status_code in (400, 404):
            raise NotFoundError("File originale non disponibile.")
        if r.status_code != 200:
            raise StorageError(f"Lettura del file non riuscita (HTTP {r.status_code}).")
        return r.content

    def delete(self, key: str) -> None:
        self._ensure_bucket()
        try:
            r = self.http.request("DELETE", f"{self.base}/object/{self.bucket}", headers=self.headers, json={"prefixes": [key]})
        except httpx.HTTPError as exc:
            raise StorageError("Spazio documenti non raggiungibile: riprova tra poco.") from exc
        if r.status_code not in (200, 204):
            raise StorageError(f"Cancellazione del file non riuscita (HTTP {r.status_code}).")

    def _list_dir(self, prefix: str, search: str = "") -> list[dict]:
        self._ensure_bucket()
        out, offset = [], 0
        while True:
            body = {"prefix": prefix, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}}
            if search:
                body["search"] = search
            try:
                r = self.http.post(f"{self.base}/object/list/{self.bucket}", headers=self.headers, json=body)
            except httpx.HTTPError as exc:
                raise StorageError("Spazio documenti non raggiungibile: riprova tra poco.") from exc
            if r.status_code != 200:
                raise StorageError(f"Elenco dei file non riuscito (HTTP {r.status_code}).")
            page = r.json()
            out += page
            if len(page) < 1000:
                return out
            offset += 1000

    def stat(self, key: str) -> int | None:
        folder, _, name = key.rpartition("/")
        for o in self._list_dir(folder, name):
            if o.get("name") == name and o.get("id") is not None:
                return int((o.get("metadata") or {}).get("size") or 0)
        return None

    def copy(self, src: str, dst: str) -> None:
        self._ensure_bucket()
        try:
            r = self.http.post(f"{self.base}/object/copy", headers=self.headers,
                               json={"bucketId": self.bucket, "sourceKey": src, "destinationKey": dst})
        except httpx.HTTPError as exc:
            raise StorageError("Spazio documenti non raggiungibile: riprova tra poco.") from exc
        if r.status_code not in (200, 201):
            raise StorageError(f"Copia del file non riuscita (HTTP {r.status_code}).")

    def list(self, prefix: str) -> dict[str, int]:
        """Elenco ricorsivo (le «cartelle» di Supabase hanno id nullo)."""
        out: dict[str, int] = {}
        stack = [prefix.rstrip("/")]
        while stack:
            folder = stack.pop()
            for o in self._list_dir(folder):
                key = f"{folder}/{o['name']}" if folder else o["name"]
                if o.get("id") is None:
                    stack.append(key)
                else:
                    out[key] = int((o.get("metadata") or {}).get("size") or 0)
        return out


_cache: dict[tuple, object] = {}


def for_settings(settings: Settings):
    if settings.storage_backend == "supabase":
        if not settings.supabase_url or not settings.supabase_service_key:
            raise StorageError("Spazio documenti online non configurato (NEXUS_SUPABASE_URL / NEXUS_SUPABASE_SERVICE_KEY).")
        k = ("supabase", settings.supabase_url, settings.storage_bucket)
        if k not in _cache:
            _cache[k] = SupabaseStorage(settings.supabase_url, settings.supabase_service_key, settings.storage_bucket)
        return _cache[k]
    return LocalStorage(settings.data_dir)
