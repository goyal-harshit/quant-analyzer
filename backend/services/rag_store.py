"""RAG vector store — upsert embedded docs and retrieve by cosine similarity.

Brute-force in-process ranking (see models.vector_store for why pgvector is not
used yet). `search` is the single seam where an ANN index would slot in. All DB
access goes through a caller-supplied AsyncSession.
"""

from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.vector_store import Embedding
from services.embedding_service import cosine_similarity


async def upsert_embedding(
    db: AsyncSession,
    *,
    kind: str,
    ref: str,
    title: str | None,
    text: str,
    embedding: list[float],
    meta: dict | None = None,
) -> Embedding:
    """Insert or update the (kind, ref) document in place."""
    existing = (
        await db.execute(
            select(Embedding).where(Embedding.kind == kind, Embedding.ref == ref)
        )
    ).scalar_one_or_none()

    if existing:
        existing.title = title
        existing.text = text
        existing.embedding = embedding
        existing.dim = len(embedding)
        existing.meta = meta
        row = existing
    else:
        row = Embedding(
            kind=kind, ref=ref, title=title, text=text,
            embedding=embedding, dim=len(embedding), meta=meta,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def count_embeddings(db: AsyncSession, kind: str | None = None) -> int:
    stmt = select(func.count()).select_from(Embedding)
    if kind:
        stmt = stmt.where(Embedding.kind == kind)
    return int((await db.execute(stmt)).scalar_one())


async def search(
    db: AsyncSession,
    query_embedding: list[float],
    *,
    k: int = 5,
    kind: str | None = None,
    min_score: float = 0.0,
) -> list[dict]:
    """Return the top-k documents by cosine similarity to `query_embedding`.

    Loads candidate rows (optionally filtered by kind) and ranks them in Python.
    Each result: {score, id, kind, ref, title, text, meta}.
    """
    if not query_embedding:
        return []
    stmt = select(Embedding)
    if kind:
        stmt = stmt.where(Embedding.kind == kind)
    rows = (await db.execute(stmt)).scalars().all()

    scored = []
    for row in rows:
        score = cosine_similarity(query_embedding, row.embedding or [])
        if score >= min_score:
            scored.append((score, row))
    scored.sort(key=lambda t: t[0], reverse=True)

    return [
        {
            "score": round(float(score), 4),
            "id": row.id,
            "kind": row.kind,
            "ref": row.ref,
            "title": row.title,
            "text": row.text,
            "meta": row.meta,
        }
        for score, row in scored[:k]
    ]
