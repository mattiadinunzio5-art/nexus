from typing import Literal

from fastapi import APIRouter, File, Query, UploadFile, status

from ...services import sources as svc
from ..deps import DB, CurrentUser
from ..schemas_research import SourceIn, SourceOut, SourceVerifyIn

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: DB, user: CurrentUser, q: str | None = None, limit: int = Query(500, ge=1, le=1000),
                 offset: int = Query(0, ge=0), origin: Literal["mine", "library"] | None = None):
    return [_out(s, user) for s in svc.list_sources(db, user, q, limit=limit, offset=offset, origin=origin)]


def _out(s, user) -> SourceOut:
    out = svc.to_out(s)
    out.library = s.owner_id != user.id
    return out


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(data: SourceIn, db: DB, user: CurrentUser):
    return svc.to_out(svc.create_source(db, user, data))


@router.get("/export.bib", summary="Esporta la bibliografia in BibTeX (per Zotero, LaTeX, Mendeley)")
def export_bibtex(db: DB, user: CurrentUser):
    from fastapi import Response

    return Response(svc.export_bibtex(db, user), media_type="application/x-bibtex; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=nexus-bibliografia.bib"})


@router.post("/import/bibtex", summary="Importa fonti da un file BibTeX (entrano come non verificate)")
async def import_bibtex(db: DB, user: CurrentUser, file: UploadFile = File(...)) -> dict:
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        from ...core.errors import ValidationFailedError

        raise ValidationFailedError("File troppo grande (massimo 5 MB).")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return svc.import_bibtex(db, user, text)


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: int, db: DB, user: CurrentUser):
    return _out(svc.get_source(db, user, source_id), user)


@router.put("/{source_id}", response_model=SourceOut)
def update_source(source_id: int, data: SourceIn, db: DB, user: CurrentUser):
    return svc.to_out(svc.update_source(db, user, source_id, data))


@router.post("/{source_id}/verify", response_model=SourceOut,
             summary="Verifica: dichiarazione dell'utente o controllo DOI su Crossref")
def verify_source(source_id: int, data: SourceVerifyIn, db: DB, user: CurrentUser):
    return svc.to_out(svc.verify_source(db, user, source_id, data.method, data.note))


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: int, db: DB, user: CurrentUser, confirm: bool = False) -> None:
    svc.delete_source(db, user, source_id, confirm)
