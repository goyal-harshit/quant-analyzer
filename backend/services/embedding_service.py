"""Embedding service — text → vector via Ollama (Phase D, RAG).

Uses the already-running Ollama server (`nomic-embed-text` by default), so it adds
**no new Python dependencies** (no torch/sentence-transformers). Every call degrades
gracefully: if embeddings are disabled or Ollama is unreachable, `embed()` returns
None and the RAG layer falls back to an empty result rather than raising.

`cosine_similarity` is a pure stdlib/math helper (no numpy needed) so the ranking
logic is trivially unit-testable.
"""

from __future__ import annotations

import logging
import math

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors. Returns 0.0 for degenerate
    inputs (empty, mismatched length, or a zero vector) — never raises."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


class EmbeddingService:
    def __init__(self) -> None:
        s = get_settings()
        self.enabled = s.embedding_enabled
        self.model = s.embedding_model
        self._client = httpx.AsyncClient(base_url=s.ollama_host, timeout=60.0)

    async def embed(self, text: str) -> list[float] | None:
        """Embed a single string. None if disabled / empty / Ollama unreachable."""
        if not self.enabled or not text or not text.strip():
            return None
        try:
            resp = await self._client.post(
                "/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            resp.raise_for_status()
            vec = resp.json().get("embedding")
            if isinstance(vec, list) and vec:
                return [float(x) for x in vec]
            return None
        except Exception as exc:  # noqa: BLE001 — embeddings are best-effort
            logger.warning("embedding failed (model=%s): %s", self.model, exc)
            return None

    async def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Embed many strings sequentially (Ollama has no native batch endpoint).
        Order is preserved; failed items are None."""
        out: list[list[float] | None] = []
        for t in texts:
            out.append(await self.embed(t))
        return out

    async def aclose(self) -> None:
        await self._client.aclose()


# Module-level singleton (mirrors ai_service / data_service style).
embedding_service = EmbeddingService()
