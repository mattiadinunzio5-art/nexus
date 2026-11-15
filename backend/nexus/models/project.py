from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin

PROJECT_STATUSES = ("active", "archived")


class Project(TimestampMixin, Base):
    """Progetto di ricerca dell'utente."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # I dati dimostrativi sono sempre marcati e mostrati come tali nella UI.
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Disegno della ricerca: domanda, obiettivi, periodo e perimetro (paesi, settori, fonti).
    research_question: Mapped[str] = mapped_column(Text, default="", nullable=False)
    objectives: Mapped[str] = mapped_column(Text, default="", nullable=False)
    hypotheses: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    period_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
