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
        self.http.request("DELETE", f"{self.base}/object/{self.bucket}", headers=self.headers, json={"prefixes": [key]})


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
