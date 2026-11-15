from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from ...services import documents as svc
from ..deps import DB, AppSettings, CurrentUser
from ..schemas_research import ChunkOut, DocumentOut, DocumentUpdate, GutenbergImportIn

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(db: DB, user: CurrentUser, project_id: int | None = None,
                   category: Literal["source_material", "user_work", "dataset"] | None = None,
                   origin: Literal["mine", "library"] | None = None):
    return svc.list_documents(db, user, project_id, category, origin)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED,
             summary="Importa un documento (PDF, DOCX, CSV, XLSX, TXT, MD)")
async def upload(
    db: DB,
    user: CurrentUser,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form(max_length=300)] = None,
    category: Annotated[Literal["source_material", "user_work", "dataset"], Form()] = "source_material",
    project_id: Annotated[int | None, Form()] = None,
    author: Annotated[str, Form(max_length=300)] = "",
):
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    return svc.import_bytes(
        db, user, settings, filename=file.filename or "documento", data=data, title=(title or "").strip() or None,
        category=category, project_id=project_id, author=author.strip(),
    )


@router.post("/gutenberg", response_model=DocumentOut, status_code=status.HTTP_201_CREATED,
             summary="Importa un singolo testo da Project Gutenberg (su richiesta dell'utente)")
def import_gutenberg(data: GutenbergImportIn, db: DB, user: CurrentUser, settings: AppSettings):
    return svc.import_gutenberg(db, user, settings, data.ebook_id, data.title, data.author, data.project_id)


def _trash_out(t) -> dict:
    return {"id": t.id, "document_id": t.document_id, "title": t.title, "filename": t.filename, "kind": t.kind, "size_bytes": t.size_bytes,
            "deleted_at": t.created_at.isoformat(), "purge_after": t.purge_after.isoformat(), "recoverable": bool(t.trash_key)}


@router.get("/trash", summary="Cestino: documenti eliminati ancora recuperabili")
def list_trash(db: DB, user: CurrentUser) -> list[dict]:
    from ...services import filesafety

    return [_trash_out(t) for t in filesafety.list_trash(db, user)]


@router.post("/trash/{trash_id}/restore", response_model=DocumentOut, summary="Ripristina un documento dal cestino (contenuto verificato con SHA-256)")
def restore_from_trash(trash_id: int, db: DB, user: CurrentUser, settings: AppSettings):
    from ...services import filesafety

    return filesafety.restore(db, user, settings, trash_id)


@router.delete("/trash/{trash_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Elimina definitivamente dal cestino (verificato)")
def purge_from_trash(trash_id: int, db: DB, user: CurrentUser, settings: AppSettings, confirm: bool = False) -> None:
    from ...services import filesafety

    filesafety.purge_one(db, user, settings, trash_id, confirm)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: DB, user: CurrentUser):
    return svc.get_document(db, user, document_id)


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(document_id: int, data: DocumentUpdate, db: DB, user: CurrentUser):
    return svc.update_document(db, user, document_id, data)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def get_chunks(document_id: int, db: DB, user: CurrentUser, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    return svc.get_chunks(db, user, document_id, offset, limit)


@router.get("/{document_id}/file", summary="Scarica il file originale")
def download(document_id: int, db: DB, user: CurrentUser, settings: AppSettings):
    d = svc.get_document(db, user, document_id)
    from urllib.parse import quote

    from fastapi import Response

    media = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "csv": "text/csv", "txt": "text/plain", "md": "text/markdown"}
    return Response(svc.file_bytes(settings, d), media_type=media.get(d.kind, "application/octet-stream"),
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(d.filename)}"})


@router.delete("/{document_id}", summary="Elimina (recuperabile dal cestino): completata solo dopo la verifica sullo storage")
def delete_document(document_id: int, db: DB, user: CurrentUser, settings: AppSettings, confirm: bool = False) -> dict:
    return svc.delete_document(db, user, settings, document_id, confirm)


@router.post("/{document_id}/extract", summary="Proposte AI di eventi, entità e relazioni, ciascuna con il passaggio che la sostiene")
def extract(document_id: int, db: DB, user: CurrentUser, settings: AppSettings) -> dict:
    from ...services import assist

    return assist.extract_from_document(db, user, settings, document_id)
