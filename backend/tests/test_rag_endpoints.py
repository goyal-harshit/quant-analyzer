"""Endpoint tests for Phase D: semantic search, grounded ask, reindex (admin),
and conversation history. Offline-deterministic via a fake embedder + fake LLM."""

import pytest
from sqlalchemy import select

import models.vector_store  # noqa: F401 — register tables before create_all
from services import rag_store

PW = "securepass123"


def _fake_embed_vector(text: str) -> list[float]:
    """Deterministic keyword-count embedding so cosine ranking is predictable."""
    t = (text or "").lower()
    return [float(t.count("tcs")), float(t.count("infy")), float(t.count("bank"))]


@pytest.fixture(autouse=True)
def _patch_ai(monkeypatch):
    from services import embedding_service as es
    from services.ai_service import ai_service

    async def fake_embed(text):
        v = _fake_embed_vector(text)
        return v if any(v) else None

    async def fake_generate(system, messages, max_tokens=500, **kw):
        return {"content": "Grounded answer [1].", "model": "fake", "tokens": 1, "source": "fake"}

    async def fake_chat(messages, **kw):
        return {"response": "plain answer", "model": "fake", "tokens_used": 0, "source": "fake"}

    monkeypatch.setattr(es.embedding_service, "embed", fake_embed)
    monkeypatch.setattr(ai_service, "_generate", fake_generate)
    monkeypatch.setattr(ai_service, "chat", fake_chat)
    yield


async def _login(client, email, admin=False):
    await client.post("/api/v1/auth/register", json={"email": email, "password": PW})
    if admin:
        from models.database import AsyncSessionLocal, User
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.email == email))).scalar_one()
            u.role = "admin"
            await db.commit()
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": PW})
    return r.json()["csrf_token"]


async def _seed_docs():
    from models.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await rag_store.upsert_embedding(db, kind="stock", ref="TCS", title="TCS",
                                         text="tcs tcs it services", embedding=_fake_embed_vector("tcs tcs"))
        await rag_store.upsert_embedding(db, kind="stock", ref="HDFCBANK", title="HDFCBANK",
                                         text="bank bank lending", embedding=_fake_embed_vector("bank bank"))


async def test_semantic_search_ranks_relevant_doc_first(client):
    await _seed_docs()
    r = await client.post("/api/v1/ai/semantic-search", json={"query": "tcs", "k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert body["results"][0]["ref"] == "TCS"
    assert body["results"][0]["snippet"]            # snippet present
    assert body["results"][0]["text"] is None       # full text trimmed out


async def test_ask_is_grounded_with_sources(client):
    await _seed_docs()
    r = await client.post("/api/v1/ai/ask", json={"query": "tell me about tcs"})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    assert body["answer"] == "Grounded answer [1]."
    assert body["sources"] and body["sources"][0]["ref"] == "TCS"


async def test_ask_falls_back_when_no_match(client):
    # No docs match "xyz" → ungrounded fallback chat answer.
    r = await client.post("/api/v1/ai/ask", json={"query": "xyz unknown"})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is False
    assert body["answer"] == "plain answer"
    assert body["sources"] == []


async def test_rag_status(client):
    await _seed_docs()
    r = await client.get("/api/v1/ai/rag/status")
    assert r.status_code == 200
    assert r.json()["stock_documents"] >= 2


async def test_reindex_requires_admin(client, monkeypatch):
    csrf = await _login(client, "user-noadmin@example.com")
    r = await client.post("/api/v1/ai/rag/reindex", json={}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 403


async def test_reindex_allowed_for_admin(client, monkeypatch):
    from services import rag_ingest

    async def fake_ingest(db, tickers=None):
        return {"embedded": 3, "skipped": 0, "universe": 3}

    monkeypatch.setattr(rag_ingest, "ingest_stocks", fake_ingest)
    csrf = await _login(client, "boss-rag@example.com", admin=True)
    r = await client.post("/api/v1/ai/rag/reindex", json={"tickers": ["TCS"]},
                          headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    assert r.json()["embedded"] == 3


# ── Conversation history ──────────────────────────────────────────────────────

async def test_conversation_crud_and_rag_reply(client):
    await _seed_docs()
    csrf = await _login(client, "conv@example.com")
    hdr = {"X-CSRF-Token": csrf}

    conv = (await client.post("/api/v1/ai/conversations", json={}, headers=hdr)).json()
    cid = conv["id"]

    msg = await client.post(f"/api/v1/ai/conversations/{cid}/messages",
                            json={"content": "tell me about tcs", "use_rag": True}, headers=hdr)
    assert msg.status_code == 200
    assert msg.json()["content"] == "Grounded answer [1]."

    full = (await client.get(f"/api/v1/ai/conversations/{cid}")).json()
    assert len(full["messages"]) == 2                  # user + assistant persisted
    assert full["title"] == "tell me about tcs"        # title seeded from first msg

    listing = (await client.get("/api/v1/ai/conversations")).json()
    assert any(c["id"] == cid for c in listing)

    d = await client.delete(f"/api/v1/ai/conversations/{cid}", headers=hdr)
    assert d.status_code == 200
    assert (await client.get(f"/api/v1/ai/conversations/{cid}")).status_code == 404


async def test_conversation_ownership_enforced(client):
    csrf_a = await _login(client, "owner-conv@example.com")
    cid = (await client.post("/api/v1/ai/conversations", json={}, headers={"X-CSRF-Token": csrf_a})).json()["id"]
    await _login(client, "intruder-conv@example.com")  # switches the client's cookies
    assert (await client.get(f"/api/v1/ai/conversations/{cid}")).status_code == 404
