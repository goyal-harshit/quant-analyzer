"""Pure-unit tests for Phase D RAG building blocks (no DB / network)."""

import math

from services.embedding_service import cosine_similarity
from services.prompts import build_context_block, build_rag_user_prompt, RAG_SYSTEM_PROMPT
from services.rag_ingest import build_stock_doc


def test_cosine_similarity_identical_and_orthogonal():
    assert cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0
    assert cosine_similarity([1, 0], [0, 1]) == 0.0
    assert math.isclose(cosine_similarity([1, 1], [1, 0]), 1 / math.sqrt(2), rel_tol=1e-9)


def test_cosine_similarity_degenerate_inputs():
    assert cosine_similarity([], [1, 2]) == 0.0
    assert cosine_similarity([1, 2], [1, 2, 3]) == 0.0   # length mismatch
    assert cosine_similarity([0, 0], [1, 2]) == 0.0       # zero vector


def test_build_context_block_numbered():
    block = build_context_block([
        {"title": "TCS", "text": "IT services."},
        {"title": "INFY", "text": "Also IT."},
    ])
    assert "[1] TCS" in block and "[2] INFY" in block
    assert "IT services." in block


def test_build_context_block_empty():
    assert "no context" in build_context_block([]).lower()


def test_build_rag_user_prompt_contains_question_and_context():
    p = build_rag_user_prompt("What is TCS?", [{"title": "TCS", "text": "An IT firm."}])
    assert "Question: What is TCS?" in p
    assert "[1] TCS" in p


def test_rag_system_prompt_demands_citations():
    assert "[1]" in RAG_SYSTEM_PROMPT
    assert "context" in RAG_SYSTEM_PROMPT.lower()


def test_build_stock_doc_includes_key_metrics():
    title, text, meta = build_stock_doc(
        "TCS", "Tata Consultancy",
        fundamentals={"sector": "IT", "pe_ratio": 30, "roe": 45, "market_cap": 1400000},
        factors={"composite_score": 78, "momentum_score": 80},
        quote={"price": 3800, "name": "Tata Consultancy"},
    )
    assert "TCS" in title and "IT" in title
    assert "P/E 30" in text
    assert "ROE 45%" in text
    assert "composite 78" in text
    assert meta["ticker"] == "TCS"
    assert meta["composite_score"] == 78


def test_build_stock_doc_handles_missing_data():
    title, text, meta = build_stock_doc("XYZ", None, None, None, None)
    assert "XYZ" in title
    assert "n/a" in text  # missing metrics render as n/a, never crash
