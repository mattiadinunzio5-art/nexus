"""File e backup: upload verificato, eliminazione recuperabile e verificata, file orfani, integrità, Supabase simulato."""

import json

import httpx
import pytest

from nexus.models import DeletedDocument, SystemCheck
from nexus.services import filesafety, storage

from .factories import upload

TXT = "La lira fu introdotta nel 1861 come moneta nazionale del Regno d'Italia.".encode()


def _files(settings, prefix):
    root = settings.data_dir / prefix
    return sorted(p.relative_to(settings.data_dir).as_posix() for p in root.rglob("*") if p.is_file()) if root.exists() else []


def test_delete_goes_to_trash_and_restores_identical(client, settings):
    d = upload(client, "lira.txt", TXT, title="La lira").json()
    r = client.delete(f"/api/documents/{d['id']}?confirm=true")
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["storage_verified"] and out["recoverable"] and out["recoverable_until"]
    assert _files(settings, "uploads") == [] and len(_files(settings, "trash")) == 1
    assert client.get(f"/api/documents/{d['id']}").status_code == 404
    trash = client.get("/api/documents/trash").json()
    assert [t["title"] for t in trash] == ["La lira"] and trash[0]["recoverable"]
    restored = client.post(f"/api/documents/trash/{trash[0]['id']}/restore")
    assert restored.status_code == 200, restored.text
    nd = restored.json()
    assert nd["sha256"] == d["sha256"] and nd["title"] == "La lira" and nd["chunk_count"] == d["chunk_count"]
    assert client.get(f"/api/documents/{nd['id']}/file").content == TXT
    assert _files(settings, "trash") == [] and client.get("/api/documents/trash").json() == []
    # il testo è di nuovo cercabile
    assert client.get("/api/research/search?q=lira moneta").json()["hits"]


def test_failed_storage_deletion_keeps_document(client, settings, monkeypatch):
    d = upload(client, "lira.txt", TXT).json()
    monkeypatch.setattr(storage.LocalStorage, "delete", lambda self, key: None)  # lo storage «finge» di cancellare
    r = client.delete(f"/api/documents/{d['id']}?confirm=true")
    assert r.status_code == 502 and "ancora presente" in r.json()["error"]["message"]
    assert client.get(f"/api/documents/{d['id']}").status_code == 200  # niente dichiarato eliminato
    assert client.get("/api/documents/trash").json() == []


def test_unverifiable_trash_copy_blocks_deletion(client, settings, monkeypatch):
    d = upload(client, "lira.txt", TXT).json()
    monkeypatch.setattr(storage.LocalStorage, "copy", lambda self, src, dst: self.put(dst, b"troncato"))
    r = client.delete(f"/api/documents/{d['id']}?confirm=true")
    assert r.status_code == 502 and "NON eliminato" in r.json()["error"]["message"]
    assert client.get(f"/api/documents/{d['id']}/file").content == TXT


def test_upload_verified_and_no_orphan_when_db_fails(client, settings, monkeypatch):
    from nexus.services import documents

    def boom(*a, **k):
        raise RuntimeError("database non disponibile")

    monkeypatch.setattr(documents, "_register", boom)
    assert upload(client, "lira.txt", TXT).status_code == 500
    assert _files(settings, "uploads") == []  # il file non resta orfano
    monkeypatch.undo()
    monkeypatch.setattr(storage.LocalStorage, "stat", lambda self, key: 3)  # dimensione sbagliata
    r = upload(client, "lira.txt", TXT)
    assert r.status_code == 502 and "non risulta salvato" in r.json()["error"]["message"]


def test_purge_requires_confirmation_and_verifies(client, settings):
    d = upload(client, "lira.txt", TXT).json()
    client.delete(f"/api/documents/{d['id']}?confirm=true")
    t = client.get("/api/documents/trash").json()[0]
    assert client.delete(f"/api/documents/trash/{t['id']}").status_code == 409
    assert client.delete(f"/api/documents/trash/{t['id']}?confirm=true").status_code == 204
    assert _files(settings, "trash") == [] and client.post(f"/api/documents/trash/{t['id']}/restore").status_code == 404


def test_integrity_scan_finds_orphans_missing_and_corruption(client, settings, db):
    a = upload(client, "a.txt", TXT).json()
    b = upload(client, "b.txt", "Il Piano Marshall fu approvato nel 1948 dal Congresso.".encode()).json()
    root = settings.data_dir
    (root / "uploads" / "1" / "orfano.pdf").write_bytes(b"%PDF senza documento")
    (root / a["storage_path"] if "storage_path" in a else next((root / "uploads").rglob(f"{a['sha256']}.txt"))).write_bytes(b"alterato")
    next((root / "uploads").rglob(f"{b['sha256']}.txt")).unlink()
    chk = client.post("/api/admin/storage/check")
    assert chk.status_code == 200, chk.text
    res = chk.json()["result"]
    assert chk.json()["status"] == "problems"
    assert [o["key"] for o in res["orphan_files"]] == ["uploads/1/orfano.pdf"]
    assert [m["document_id"] for m in res["missing_files"]] == [b["id"]]
    assert [m["document_id"] for m in res["size_mismatch"]] == [a["id"]]
    assert client.get("/api/admin/storage/check").json()["last"]["id"] == chk.json()["id"]
    # Pulizia: solo i file orfani, mai quelli referenziati da un documento.
    assert client.post("/api/admin/storage/cleanup").status_code == 409
    cl = client.post("/api/admin/storage/cleanup?confirm=true").json()
    assert cl["removed_orphans"] == ["uploads/1/orfano.pdf"] and not cl["failed"]
    assert next((root / "uploads").rglob(f"{a['sha256']}.txt")).exists()


def test_expired_trash_is_purged_and_check_is_periodic(client, settings, db):
    from datetime import timedelta

    from nexus.database.base import utcnow

    d = upload(client, "lira.txt", TXT).json()
    client.delete(f"/api/documents/{d['id']}?confirm=true")
    t = db.query(DeletedDocument).one()
    t.purge_after = utcnow() - timedelta(days=1)
    db.commit()
    assert filesafety.scan(db, settings)["expired_trash"] == [t.id]
    assert filesafety.cleanup(db, settings, None, confirm=True)["purged_trash"] == [t.id]
    assert _files(settings, "trash") == []
    # controllo periodico: dovuto se non c'è mai stato o è vecchio
    assert filesafety.due(db, settings)
    filesafety.run_check(db, settings, "scheduled")
    assert not filesafety.due(db, settings)
    db.query(SystemCheck).update({"started_at": utcnow() - timedelta(hours=settings.integrity_interval_hours + 1)})
    db.commit()
    assert filesafety.due(db, settings)


def test_worker_runs_scheduled_integrity_check(client, settings, db):
    from nexus.services.jobs import Worker

    w = Worker(client.app.state.database, settings)
    w._periodic()
    assert db.query(SystemCheck).filter_by(trigger="scheduled").count() == 1
    w._periodic()  # non ancora dovuto
    assert db.query(SystemCheck).count() == 1


class FakeSupabase:
    """Server Supabase Storage simulato: oggetti, elenco per cartelle, copia, cancellazione."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def __call__(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path.split("/storage/v1", 1)[1]
        if path.startswith("/bucket"):
            return httpx.Response(200, json={"name": "b"})
        if req.method == "POST" and path == "/object/copy":
            b = json.loads(req.content)
            self.objects[b["destinationKey"]] = self.objects[b["sourceKey"]]
            return httpx.Response(200, json={"Key": b["destinationKey"]})
        if req.method == "POST" and path.startswith("/object/list/"):
            b = json.loads(req.content)
            prefix = b["prefix"].strip("/")
            seen, out = set(), []
            for k, v in sorted(self.objects.items()):
                if prefix and not k.startswith(prefix + "/"):
                    continue
                rest = k[len(prefix) + 1:] if prefix else k
                head = rest.split("/", 1)[0]
                if b.get("search") and not head.startswith(b["search"]):
                    continue
                if "/" in rest:
                    if head not in seen:
                        seen.add(head)
                        out.append({"name": head, "id": None, "metadata": None})
                else:
                    out.append({"name": head, "id": "x", "metadata": {"size": len(v)}})
            return httpx.Response(200, json=out[b.get("offset", 0): b.get("offset", 0) + b["limit"]])
        if req.method == "DELETE" and path.startswith("/object/"):
            for k in json.loads(req.content)["prefixes"]:
                self.objects.pop(k, None)
            return httpx.Response(200, json=[])
        key = path.split("/object/b/", 1)[1]
        if req.method == "POST":
            self.objects[key] = req.content
            return httpx.Response(200, json={"Key": key})
        if req.method == "GET":
            return httpx.Response(200, content=self.objects[key]) if key in self.objects else httpx.Response(404)
        return httpx.Response(405)


def test_supabase_storage_stat_list_copy_delete():
    fake = FakeSupabase()
    st = storage.SupabaseStorage("https://x.supabase.co", "k", "b", client=httpx.Client(transport=httpx.MockTransport(fake)))
    st.put("uploads/1/aa.txt", b"ciao")
    st.put("uploads/2/bb.pdf", b"12345")
    assert st.stat("uploads/1/aa.txt") == 4 and st.stat("uploads/1/zz.txt") is None
    st.copy("uploads/1/aa.txt", "trash/1/aa.txt.1")
    assert st.list("uploads") == {"uploads/1/aa.txt": 4, "uploads/2/bb.pdf": 5}
    assert st.list("trash") == {"trash/1/aa.txt.1": 4}
    st.delete("uploads/1/aa.txt")
    assert st.stat("uploads/1/aa.txt") is None


def test_supabase_failed_delete_is_reported():
    st = storage.SupabaseStorage("https://x.supabase.co", "k", "b",
                                 client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200 if "/bucket" in r.url.path else 500))))
    with pytest.raises(storage.StorageError, match="Cancellazione"):
        st.delete("uploads/1/a.txt")
