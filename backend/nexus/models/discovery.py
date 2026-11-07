"""Discovery Intelligence: sessioni, connessioni, ipotesi, anomalie e analisi salvate."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base, TimestampMixin

SESSION_STATUSES = ("queued", "running", "paused", "stopped", "completed", "failed")
HYPOTHESIS_STATUSES = ("to_verify", "verifying", "confirmed", "rejected", "inconclusive")
FINDING_STATUSES = ("new", "accepted", "dismissed")


class DiscoverySession(TimestampMixin, Base):
    __tablename__ = "discovery_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(12), nullable=False)  # guided | autonomous
    query: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="queued", nullable=False)
    cursor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # prossimo passo da eseguire
    scope: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # registro dei passi eseguiti
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    limits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DiscoveryConnection(TimestampMixin, Base):
    __tablename__ = "discovery_connections"
    __table_args__ = (UniqueConstraint("owner_id", "fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_sessions.id", ondelete="SET NULL"), index=True, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    elements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    period: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    sources: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reliability: Mapped[str] = mapped_column(String(10), default="low", nullable=False)
    reliability_reasons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    caveats: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="new", nullable=False)
    graph_relation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DiscoveryHypothesis(TimestampMixin, Base):
    __tablename__ = "discovery_hypotheses"
    __table_args__ = (UniqueConstraint("owner_id", "fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_sessions.id", ondelete="SET NULL"), index=True, nullable=True)
    connection_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_connections.id", ondelete="SET NULL"), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    phenomena: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    motivation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    supporting: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    contrary: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missing: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    method: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), default="low", nullable=False)
    status: Mapped[str] = mapped_column(String(14), default="to_verify", nullable=False)
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    verification: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    decision_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    origin: Mapped[str] = mapped_column(String(10), default="rules", nullable=False)  # rules | ai | user
    graph_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DiscoveryAnomaly(TimestampMixin, Base):
    __tablename__ = "discovery_anomalies"
    __table_args__ = (UniqueConstraint("owner_id", "fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_sessions.id", ondelete="SET NULL"), index=True, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    what_changed: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reference: Mapped[str] = mapped_column(Text, default="", nullable=False)
    period: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    alternatives: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    refs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    verifiability: Mapped[str] = mapped_column(String(10), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="open", nullable=False)  # open | explained | dismissed
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)


class DiscoveryAnalysis(TimestampMixin, Base):
    """Analisi salvate: catene causali, catene di trasmissione tra serie, scenari."""

    __tablename__ = "discovery_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_sessions.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # causal_chain | transmission | foresight
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
