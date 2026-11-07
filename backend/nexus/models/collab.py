from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin

ALERT_KINDS = ("new_data", "above", "below")


class SeriesAlert(TimestampMixin, Base):
    """Avviso su una serie: nuovo dato pubblicato o valore oltre una soglia."""

    __tablename__ = "series_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Ultima data osservata già valutata: un avviso scatta una sola volta per ogni nuovo dato.
    last_seen_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class ProjectComment(TimestampMixin, Base):
    """Commento in un progetto condiviso."""

    __tablename__ = "project_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
