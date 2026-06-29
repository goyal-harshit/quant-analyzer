"""
vector_store.py — DB tables for RAG (Phase D): embeddings + conversation history.

Embeddings are stored as a portable JSON array of floats (`JSONB` on Postgres,
`JSON` on SQLite) and similarity is computed in-process (see `services.rag_store`).
This deliberately avoids a pgvector image swap — the current Postgres image
(`timescale/timescaledb:pg16`) ships no `vector` extension, and the corpus for a
single-user analyzer is small enough that brute-force cosine is instant. The
`rag_store` search is the seam where a pgvector ANN index can drop in later without
touching callers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import JSONB, Base, _utcnow


class Embedding(Base):
    """One embedded document. Unique per (kind, ref) so re-ingestion upserts in
    place (e.g. kind='stock', ref='TCS' → the canonical TCS profile doc)."""

    __tablename__ = "embeddings"
    __table_args__ = (UniqueConstraint("kind", "ref", name="uq_embeddings_kind_ref"),)

    id:        Mapped[int] = mapped_column(Integer, primary_key=True)
    kind:      Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    ref:       Mapped[str] = mapped_column(String(120), nullable=False)
    title:     Mapped[Optional[str]] = mapped_column(String(300))
    text:      Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(JSONB, nullable=False)  # list[float]
    dim:       Mapped[int] = mapped_column(Integer, default=0)
    meta:      Mapped[Optional[dict]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class Conversation(Base):
    """A per-user chat thread (Phase D #15 — persisted conversation history)."""

    __tablename__ = "conversations"

    id:         Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id:    Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title:      Mapped[str] = mapped_column(String(200), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id:              Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role:       Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content:    Mapped[str] = mapped_column(Text, nullable=False)
    sources:    Mapped[Optional[list]] = mapped_column(JSONB)  # citations for assistant turns
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
