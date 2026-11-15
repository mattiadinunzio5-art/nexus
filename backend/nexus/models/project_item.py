from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin

PROJECT_ITEM_TYPES = ("document", "source", "event", "entity", "series", "relation")


class ProjectItem(TimestampMixin, Base):
    """Elemento collegato a un progetto: propri o della Biblioteca (documenti, fonti, eventi, entità, serie, relazioni)."""

    __tablename__ = "project_items"
    __table_args__ = (UniqueConstraint("project_id", "item_type", "item_id", name="uq_project_item"),
                      Index("ix_project_items_item", "item_type", "item_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
