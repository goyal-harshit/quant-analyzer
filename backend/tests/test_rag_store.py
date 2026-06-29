"""DB tests for the RAG vector store (upsert + cosine ranking) against SQLite."""

import pytest
from sqlalchemy import delete

import models.vector_store  # noqa: F401 — register tables on Base before create_all
from models.vector_store import Embedding
from services import rag_store


@pytest.fixture(autouse=True)
async def _clean_embeddings(db_session):
    # db_engine is session-scoped, so wipe embeddings before each test for isolation.
    await db_session.execute(delete(Embedding))
    await db_session.commit()
    yield


async def test_upsert_inserts_then_updates_in_place(db_session):
    await rag_store.upsert_embedding(
        db_session, kind="stock", ref="TCS", title="TCS", text="v1", embedding=[1.0, 0.0]
    )
    assert await rag_store.count_embeddings(db_session, kind="stock") == 1

    # Same (kind, ref) updates in place — no duplicate row.
    row = await rag_store.upsert_embedding(
        db_session, kind="stock", ref="TCS", title="TCS", text="v2", embedding=[0.0, 1.0]
    )
    assert await rag_store.count_embeddings(db_session, kind="stock") == 1
    assert row.text == "v2"
    assert row.dim == 2


async def test_search_ranks_by_cosine(db_session):
    await rag_store.upsert_embedding(db_session, kind="stock", ref="A", title="A", text="a", embedding=[1.0, 0.0])
    await rag_store.upsert_embedding(db_session, kind="stock", ref="B", title="B", text="b", embedding=[0.0, 1.0])
    await rag_store.upsert_embedding(db_session, kind="stock", ref="C", title="C", text="c", embedding=[0.9, 0.1])

    results = await rag_store.search(db_session, [1.0, 0.0], k=2)
    assert [r["ref"] for r in results] == ["A", "C"]   # closest two to [1,0]
    assert results[0]["score"] >= results[1]["score"]
    assert results[0]["score"] == 1.0


async def test_search_filters_by_kind_and_min_score(db_session):
    await rag_store.upsert_embedding(db_session, kind="stock", ref="A", title="A", text="a", embedding=[1.0, 0.0])
    await rag_store.upsert_embedding(db_session, kind="news", ref="N", title="N", text="n", embedding=[1.0, 0.0])

    only_news = await rag_store.search(db_session, [1.0, 0.0], k=5, kind="news")
    assert [r["ref"] for r in only_news] == ["N"]

    # A high min_score filters out an orthogonal match.
    none_pass = await rag_store.search(db_session, [0.0, 1.0], k=5, kind="stock", min_score=0.5)
    assert none_pass == []


async def test_search_empty_query_embedding(db_session):
    assert await rag_store.search(db_session, [], k=5) == []
