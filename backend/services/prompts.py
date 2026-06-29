"""Externalized prompt templates (Phase D #15).

Keeping RAG prompts here (versioned, in one place) instead of inline string
literals scattered through ai_service. Pure string helpers — unit-testable.
"""

from __future__ import annotations

RAG_SYSTEM_PROMPT = """You are QuantAI, a research assistant for Indian equity markets (NSE/BSE).
Answer the user's question USING ONLY the numbered context passages provided below.
Rules:
- Ground every claim in the context. Cite the passages you use as [1], [2], etc.
- If the context does not contain the answer, say so plainly — do NOT invent data.
- Use ₹ for currency. Be concise (3-5 sentences) and data-driven.
- Never give explicit buy/sell recommendations; describe what the data shows.
- End with a one-line educational-purpose disclaimer."""


def build_context_block(passages: list[dict]) -> str:
    """Render retrieved passages as a numbered context block for the LLM prompt.

    Each passage dict needs `title` and `text`; numbering is 1-based to match the
    [1]/[2] citation convention in RAG_SYSTEM_PROMPT.
    """
    if not passages:
        return "(no context passages were retrieved)"
    lines = []
    for i, p in enumerate(passages, start=1):
        title = (p.get("title") or p.get("ref") or "Untitled").strip()
        text = (p.get("text") or "").strip()
        lines.append(f"[{i}] {title}\n{text}")
    return "\n\n".join(lines)


def build_rag_user_prompt(question: str, passages: list[dict]) -> str:
    """Compose the user-turn prompt: numbered context followed by the question."""
    context = build_context_block(passages)
    return f"Context:\n{context}\n\nQuestion: {question.strip()}"
