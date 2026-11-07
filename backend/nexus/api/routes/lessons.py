from fastapi import APIRouter, status

from ...core.lessons import LESSONS
from ...services import lessons as svc
from ..deps import DB, CurrentUser

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("", summary="Lezioni guidate disponibili")
def list_lessons(user: CurrentUser) -> list[dict]:
    return [{k: x[k] for k in ("id", "title", "level", "duration", "summary")} for x in LESSONS]


@router.get("/{lesson_id}", summary="Dettaglio di una lezione")
def get_lesson(lesson_id: str, user: CurrentUser) -> dict:
    return svc.get(lesson_id)


@router.post("/{lesson_id}/start", status_code=status.HTTP_201_CREATED, summary="Inizia la lezione: crea progetto, guida e letture")
def start_lesson(lesson_id: str, db: DB, user: CurrentUser) -> dict:
    return svc.start(db, user, lesson_id)
