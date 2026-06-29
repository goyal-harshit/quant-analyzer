"""AI Router — LLM-powered research endpoints (+ Phase D RAG & conversations)"""

import asyncio
from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import (
    ChatRequest, ChatResponse, AIReportRequest, AIReportResponse,
    EarningsSummaryRequest,
)
from models.database import get_db, User
from models.vector_store import Conversation, ConversationMessage
from services.ai_service import ai_service, _STOCKS, buildOfflineReport
from services.data_service import data_service
from services.fast_data import compute_quant_factors
from services.validation import validate_ticker
from services.rate_limit import limiter
from services.auth_service import get_current_user, require_admin
from services import rag_service, rag_ingest, rag_store

router = APIRouter()


# ── Phase D request models ───────────────────────────────────────────────────
class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=25)
    kind: str | None = None


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int | None = Field(default=None, ge=1, le=25)


class ReindexRequest(BaseModel):
    tickers: list[str] | None = None


class ConversationCreate(BaseModel):
    title: str | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1)
    use_rag: bool = True


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, payload: ChatRequest):
    """
    Conversational research assistant.
    Maintains context across a message thread; optionally biased toward
    a specific stock the user is currently viewing.
    """
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    result = await ai_service.chat(
        messages,
        context_ticker=payload.context_ticker,
        provider=payload.provider,
        model=payload.model,
        api_key=payload.api_key,
    )
    return ChatResponse(**result)


@router.post("/report/{ticker}", response_model=AIReportResponse)
@limiter.limit("20/minute")
async def generate_report(request: Request, ticker: str, payload: AIReportRequest = None):
    """
    Generate a full AI research report for a stock combining fundamentals,
    factor scores, and qualitative analysis.
    """
    ticker = validate_ticker(ticker)
    fundamentals = await data_service.get_fundamentals(ticker)
    quote = await data_service.get_quote(ticker)

    if not fundamentals:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")

    # Defensive: never unpack a None into a dict literal.
    stock_data = {**(fundamentals or {}), **(quote or {}), "ticker": ticker}
    report_type = payload.report_type if payload else "full"

    content = await ai_service.generate_stock_report(stock_data, report_type)

    return AIReportResponse(
        ticker=ticker,
        report_type=report_type,
        content=content,
        model="ollama-llama3.2",
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/insight/{ticker}")
@limiter.limit("30/minute")
async def get_stock_insight(request: Request, ticker: str):
    """
    Get real stock data + quant factors + AI analysis for ANY ticker.
    Uses direct Yahoo Finance API calls (fast, reliable from Docker).
    """
    ticker = validate_ticker(ticker).replace(".NS", "").replace(".BO", "")

    # Single cached call per data type — all parallel, fast fallback
    _f, _q, _prices = await asyncio.gather(
        data_service.get_fundamentals(ticker),
        data_service.get_quote(ticker),
        data_service.get_price_history(ticker, period="1y"),
        return_exceptions=True,
    )

    fundamentals = _f if not isinstance(_f, Exception) else {}
    quote = _q if not isinstance(_q, Exception) else {}
    prices_df = _prices if not isinstance(_prices, Exception) else None

    year_change_pct = None
    if prices_df is not None and not prices_df.empty and len(prices_df) > 1:
        current = prices_df["close"].iloc[-1]
        year_ago = prices_df["close"].iloc[0]
        if year_ago and year_ago > 0:
            year_change_pct = round(((current - year_ago) / year_ago) * 100, 2)
        fifty_two_week_high = round(float(prices_df["high"].max()), 2)
        fifty_two_week_low = round(float(prices_df["low"].min()), 2)
        if quote:
            quote["year_change_pct"] = year_change_pct
            quote["fifty_two_week_high"] = fifty_two_week_high
            quote["fifty_two_week_low"] = fifty_two_week_low

    # Compute quant factors from real data (works even without fundamentals)
    factors = {}
    if prices_df is not None and not prices_df.empty:
        factors = compute_quant_factors(prices_df, fundamentals or {})

    # Build compact data summary for Ollama
    price = quote.get("price") if quote else None
    year_hi = quote.get("fifty_two_week_high") if quote else None
    year_lo = quote.get("fifty_two_week_low") if quote else None
    chg = quote.get("year_change_pct") if quote else None

    data_str = f"Price: ₹{price}" if price else ""
    if year_hi: data_str += f", 52W High: ₹{year_hi}"
    if year_lo: data_str += f", 52W Low: ₹{year_lo}"
    if chg: data_str += f", 1Y Change: {chg}%"

    if factors:
        score = factors.get("composite_score")
        mom = factors.get("momentum_score")
        rsi = factors.get("rsi_14")
        vol = factors.get("volatility_60d")
        parts = []
        if score is not None: parts.append(f"Composite={score}")
        if mom is not None: parts.append(f"Momentum={mom}")
        if rsi is not None: parts.append(f"RSI={rsi}")
        if vol is not None: parts.append(f"Vol60d={vol}%")
        if parts: data_str += "\nScores: " + ", ".join(parts)

    prompt = f"""Analyze {ticker} ({quote.get('name', ticker) if quote else ticker}).
Data: {data_str}

Give exactly 4 short bullet points (1 line each):
- Valuation: is it cheap/fair/expensive?
- Momentum: trend direction and strength
- Risk: key concern from the data
- Verdict: buy/hold/sell with 1 reason

Be brief. Use numbers. No headers."""

    SYSTEM_PROMPT_INSIGHT = """You are a quantitative equity analyst specializing in Indian equities.
    Provide a very brief 4-bullet analysis.
    You must output exactly 4 bullet points, one for each category: Valuation, Momentum, Risk, and Verdict.
    Be concise, use numbers, and do not include headers or other text.
    Format precisely as:
    - Valuation: [details]
    - Momentum: [details]
    - Risk: [details]
    - Verdict: [details]"""

    analysis = "Analysis unavailable"
    try:
        result = await asyncio.wait_for(
            ai_service._generate(SYSTEM_PROMPT_INSIGHT, [{"role": "user", "content": prompt}], max_tokens=300),
            timeout=120.0,
        )
        analysis = result.get("content", analysis)
    except Exception:
        stock = next((s for s in _STOCKS if s["ticker"] == ticker), None)
        if stock:
            analysis = buildOfflineReport(stock)
        else:
            comp = factors.get("composite_score") or 0
            price = quote.get("price") if quote else 0
            pe = (fundamentals or {}).get("pe_ratio") or 0
            roe = (fundamentals or {}).get("roe") or 0
            sector = (fundamentals or {}).get("sector", "Diversified")
            analysis = (
                f"**Quick Snapshot**\n"
                f"{ticker} trades at ₹{price:,.0f} with P/E {pe:.1f}x and ROE {roe:.1f}%. "
                f"Composite score {comp}/100.\n\n"
                f"⚠️ Offline engine. For full LLM analysis, run Ollama locally."
            )

    return {
        "ticker": ticker,
        "name": quote.get("name", ticker) if quote else ticker,
        "quote": quote if quote else None,
        "fundamentals": fundamentals if fundamentals else None,
        "factors": factors if factors else None,
        "analysis": analysis,
        "model": "ollama-llama3.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/earnings-summary")
@limiter.limit("20/minute")
async def summarise_earnings(request: Request, payload: EarningsSummaryRequest):
    """
    Summarise earnings release for a ticker.
    In production: fetch raw filing text from NSE/BSE corporate
    announcements or earnings call transcript providers.
    """
    # Placeholder: in production, fetch actual filing text
    ticker = validate_ticker(payload.ticker)
    placeholder_text = f"[Earnings filing text for {ticker}, period {payload.period} would be fetched from NSE/BSE corporate announcements API here]"

    summary = await ai_service.summarise_earnings(ticker, placeholder_text)
    return {
        "ticker": ticker,
        "period": payload.period,
        "summary": summary,
    }


@router.post("/thesis/{ticker}")
@limiter.limit("20/minute")
async def generate_thesis(request: Request, ticker: str):
    """Generate a structured bull/bear investment thesis."""
    ticker = validate_ticker(ticker)
    fundamentals = await data_service.get_fundamentals(ticker)
    quote = await data_service.get_quote(ticker)

    if not fundamentals:
        raise HTTPException(status_code=404, detail=f"No data available for {ticker}")

    # Defensive: never unpack a None into a dict literal.
    stock_data = {**(fundamentals or {}), **(quote or {}), "ticker": ticker}
    thesis = await ai_service.generate_investment_thesis(stock_data)

    return {"ticker": ticker, "thesis": thesis}


@router.post("/portfolio-risk-narrative")
async def portfolio_risk_narrative(portfolio_data: dict):
    """Generate plain-language explanation of portfolio risk metrics."""
    narrative = await ai_service.analyse_portfolio_risk(portfolio_data)
    return {"narrative": narrative}


# ── RAG / semantic search (Phase D) ──────────────────────────────────────────

@router.post("/semantic-search")
@limiter.limit("30/minute")
async def semantic_search(request: Request, payload: SemanticSearchRequest, db: AsyncSession = Depends(get_db)):
    """Embed the query and return the most similar indexed documents (no LLM)."""
    results = await rag_service.retrieve(db, payload.query, k=payload.k, kind=payload.kind)
    return {
        "query": payload.query,
        "count": len(results),
        # Trim the full text to a snippet for the list response.
        "results": [
            {**r, "snippet": (r.get("text") or "")[:280], "text": None}
            for r in results
        ],
    }


@router.post("/ask")
@limiter.limit("20/minute")
async def ask(request: Request, payload: AskRequest, db: AsyncSession = Depends(get_db)):
    """Answer a question grounded in indexed platform data, with citations."""
    return await rag_service.answer(db, payload.query, k=payload.k)


@router.get("/rag/status")
async def rag_status(db: AsyncSession = Depends(get_db)):
    """How many documents are indexed (overall and for stocks)."""
    return {
        "documents": await rag_store.count_embeddings(db),
        "stock_documents": await rag_store.count_embeddings(db, kind="stock"),
    }


@router.post("/rag/reindex")
async def rag_reindex(
    payload: ReindexRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """(Admin) Embed + upsert canonical stock docs into the vector store."""
    return await rag_ingest.ingest_stocks(db, tickers=payload.tickers)


# ── Conversation history (Phase D #15) ───────────────────────────────────────

def _conv_out(c: Conversation) -> dict:
    return {"id": c.id, "title": c.title, "created_at": c.created_at, "updated_at": c.updated_at}


async def _owned_conversation(conv_id: int, db: AsyncSession, user: User) -> Conversation:
    conv = (
        await db.execute(
            select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/conversations")
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = Conversation(user_id=current_user.id, title=payload.title or "New conversation")
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return _conv_out(conv)


@router.get("/conversations")
async def list_conversations(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    rows = (
        await db.execute(
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(Conversation.updated_at.desc())
        )
    ).scalars().all()
    return [_conv_out(c) for c in rows]


@router.get("/conversations/{conv_id}")
async def get_conversation(
    conv_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    conv = await _owned_conversation(conv_id, db, current_user)
    msgs = (
        await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conv_id)
            .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
        )
    ).scalars().all()
    return {
        **_conv_out(conv),
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content,
             "sources": m.sources, "created_at": m.created_at}
            for m in msgs
        ],
    }


@router.post("/conversations/{conv_id}/messages")
async def add_message(
    conv_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Append a user message, generate an (optionally RAG-grounded) reply, persist both."""
    conv = await _owned_conversation(conv_id, db, current_user)

    db.add(ConversationMessage(conversation_id=conv_id, role="user", content=payload.content))

    if payload.use_rag:
        result = await rag_service.answer(db, payload.content)
        reply, sources = result["answer"], result.get("sources") or None
    else:
        chat = await ai_service.chat([{"role": "user", "content": payload.content}])
        reply, sources = chat.get("response", ""), None

    assistant = ConversationMessage(
        conversation_id=conv_id, role="assistant", content=reply, sources=sources
    )
    db.add(assistant)
    # First user message seeds the conversation title.
    if conv.title in (None, "", "New conversation"):
        conv.title = payload.content[:60]
    await db.commit()
    await db.refresh(assistant)
    return {
        "id": assistant.id,
        "role": "assistant",
        "content": reply,
        "sources": sources,
        "created_at": assistant.created_at,
    }


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    conv = await _owned_conversation(conv_id, db, current_user)
    await db.delete(conv)
    await db.commit()
    return {"deleted": True, "id": conv_id}
