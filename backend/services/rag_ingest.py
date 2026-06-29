"""RAG ingestion — turn platform data into embedded documents (Phase D #13).

`build_stock_doc` is pure (data dict → natural-language doc) and unit-tested.
`ingest_stocks` fetches via the existing data_service, embeds via Ollama, and
upserts into the vector store. It degrades gracefully: a ticker whose embedding
fails is skipped, not fatal.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from services.embedding_service import embedding_service
from services import rag_store

logger = logging.getLogger(__name__)


def _fmt(v, suffix: str = "") -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:g}{suffix}"
    return f"{v}{suffix}"


def build_stock_doc(
    ticker: str,
    name: str | None,
    fundamentals: dict | None,
    factors: dict | None,
    quote: dict | None,
) -> tuple[str, str, dict]:
    """Build (title, text, meta) for a stock's canonical profile document.

    A compact natural-language summary of valuation, profitability, growth and
    factor scores — the unit the LLM retrieves and cites.
    """
    f = fundamentals or {}
    fa = factors or {}
    q = quote or {}
    display = name or f.get("name") or ticker
    sector = f.get("sector") or "Diversified"
    title = f"{display} ({ticker}) — {sector}"

    text = (
        f"{display} ({ticker}) is an NSE-listed company in the {sector} sector"
        f"{(' (' + f.get('industry') + ')') if f.get('industry') else ''}. "
        f"Price ₹{_fmt(q.get('price'))}, market cap ₹{_fmt(f.get('market_cap'))} Cr. "
        f"Valuation: P/E {_fmt(f.get('pe_ratio'))}, P/B {_fmt(f.get('pb_ratio'))}, "
        f"EV/EBITDA {_fmt(f.get('ev_ebitda'))}. "
        f"Profitability: ROE {_fmt(f.get('roe'), '%')}, "
        f"net margin {_fmt(f.get('net_margin'), '%')}, "
        f"debt/equity {_fmt(f.get('debt_equity'))}. "
        f"Growth: revenue {_fmt(f.get('revenue_growth'), '%')}, "
        f"earnings {_fmt(f.get('earnings_growth'), '%')}. "
        f"Quant factor scores (0-100): composite {_fmt(fa.get('composite_score'))}, "
        f"momentum {_fmt(fa.get('momentum_score'))}, quality {_fmt(fa.get('quality_score'))}, "
        f"value {_fmt(fa.get('value_score'))}, growth {_fmt(fa.get('growth_score'))}. "
        f"RSI(14) {_fmt(fa.get('rsi_14'))}, 60-day volatility {_fmt(fa.get('volatility_60d'), '%')}."
    )
    meta = {
        "ticker": ticker,
        "name": display,
        "sector": sector,
        "composite_score": fa.get("composite_score"),
        "pe_ratio": f.get("pe_ratio"),
    }
    return title, text, meta


async def ingest_stocks(db: AsyncSession, tickers: list[str] | None = None) -> dict:
    """Embed + upsert canonical docs for the given tickers (default: liquid universe)."""
    from services.data_service import data_service, NIFTY_50_TICKERS
    from services.fast_data import compute_quant_factors

    universe = tickers or NIFTY_50_TICKERS
    embedded = 0
    skipped = 0
    for ticker in universe:
        try:
            fundamentals = await data_service.get_fundamentals(ticker)
            quote = await data_service.get_quote(ticker)
            try:
                prices = await data_service.get_price_history(ticker, period="1y")
                factors = compute_quant_factors(prices, fundamentals or {}) if prices is not None and not prices.empty else {}
            except Exception:
                factors = {}
            name = (quote or {}).get("name")
            title, text, meta = build_stock_doc(ticker, name, fundamentals, factors, quote)
            vec = await embedding_service.embed(text)
            if not vec:
                skipped += 1
                continue
            await rag_store.upsert_embedding(
                db, kind="stock", ref=ticker, title=title, text=text, embedding=vec, meta=meta
            )
            embedded += 1
        except Exception as exc:  # noqa: BLE001 — one bad ticker must not abort the batch
            logger.warning("RAG ingest failed for %s: %s", ticker, exc)
            skipped += 1
    return {"embedded": embedded, "skipped": skipped, "universe": len(universe)}
