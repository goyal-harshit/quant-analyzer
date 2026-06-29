"""RAG service — semantic retrieval + grounded answer generation (Phase D #14).

Ties the embedding service, vector store, prompt templates, and the LLM
(ai_service) together. Everything degrades gracefully: no embeddings / no
indexed docs → empty retrieval and an ungrounded fallback answer, never an error.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from services.embedding_service import embedding_service
from services import rag_store
from services.prompts import RAG_SYSTEM_PROMPT, build_rag_user_prompt


def _source_list(passages: list[dict]) -> list[dict]:
    """Compact citation list (index matches the [1]/[2] markers in the prompt)."""
    return [
        {
            "n": i,
            "ref": p.get("ref"),
            "title": p.get("title"),
            "kind": p.get("kind"),
            "score": p.get("score"),
        }
        for i, p in enumerate(passages, start=1)
    ]


async def retrieve(
    db: AsyncSession, query: str, *, k: int | None = None, kind: str | None = None
) -> list[dict]:
    """Embed the query and return the top-k matching documents (with scores)."""
    s = get_settings()
    vec = await embedding_service.embed(query)
    if not vec:
        return []
    return await rag_store.search(
        db, vec, k=k or s.rag_top_k, kind=kind, min_score=s.rag_min_score
    )


async def answer(db: AsyncSession, query: str, *, k: int | None = None) -> dict:
    """Retrieve grounding context and generate a cited answer.

    Returns {answer, sources, grounded, model}. When no context is retrieved
    (embeddings off / nothing indexed), falls back to an ungrounded chat answer
    with grounded=False and no sources.
    """
    from services.ai_service import ai_service  # local import avoids cycle at module load

    passages = await retrieve(db, query, k=k)
    if not passages:
        result = await ai_service.chat([{"role": "user", "content": query}])
        return {
            "answer": result.get("response", ""),
            "sources": [],
            "grounded": False,
            "model": result.get("model"),
        }

    user_prompt = build_rag_user_prompt(query, passages)
    result = await ai_service._generate(
        RAG_SYSTEM_PROMPT, [{"role": "user", "content": user_prompt}], max_tokens=500
    )
    content = result.get("content")
    if not content:
        # LLM unreachable — still return the retrieved evidence so the UI is useful.
        content = (
            "AI model unavailable, but here are the most relevant indexed passages:\n\n"
            + "\n".join(f"[{i+1}] {p.get('title')}" for i, p in enumerate(passages))
        )
    return {
        "answer": content,
        "sources": _source_list(passages),
        "grounded": True,
        "model": result.get("model"),
    }
