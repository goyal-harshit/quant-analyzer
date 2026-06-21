"""
Trading Simulator service — paper-trading logic.

Holdings and P&L are derived from the immutable transaction ledger using the
average-cost method. Trades execute at live NSE/BSE prices (via data_service),
so the simulator reflects the same prices shown elsewhere in the app.
"""

import bisect
import logging
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.data_service import data_service
from .models import SimPortfolio, SimTransaction

logger = logging.getLogger(__name__)

# All-in transaction cost (~brokerage + STT + exchange + GST + stamp) on turnover.
# Approximate equity-delivery cost; transparent and applied to both buy and sell.
FEE_RATE = 0.0011

MAX_PORTFOLIOS_PER_USER = 25
MAX_EQUITY_POINTS = 120


# ── OWNERSHIP ──────────────────────────────────────────────────────
async def _get_portfolio(db: AsyncSession, portfolio_id: int, user_id: Optional[int]) -> SimPortfolio:
    """Fetch a portfolio, enforcing ownership. Owned (user_id set) portfolios are
    only visible to that user; anonymous (user_id NULL) ones are id-scoped."""
    result = await db.execute(select(SimPortfolio).where(SimPortfolio.id == portfolio_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if p.user_id is not None and p.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your portfolio")
    return p


# ── CRUD ───────────────────────────────────────────────────────────
async def create_portfolio(db: AsyncSession, user_id: Optional[int], name: str, starting_capital: float) -> SimPortfolio:
    if user_id is not None:
        existing = await db.execute(select(SimPortfolio).where(SimPortfolio.user_id == user_id))
        if len(existing.scalars().all()) >= MAX_PORTFOLIOS_PER_USER:
            raise HTTPException(status_code=400, detail="Portfolio limit reached")
    p = SimPortfolio(user_id=user_id, name=name.strip(), starting_capital=starting_capital, cash=starting_capital)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def list_portfolios(db: AsyncSession, user_id: Optional[int]) -> List[SimPortfolio]:
    if user_id is None:
        return []  # guests scope by id (stored client-side); nothing to list
    result = await db.execute(
        select(SimPortfolio).where(SimPortfolio.user_id == user_id).order_by(SimPortfolio.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_portfolio(db: AsyncSession, portfolio_id: int, user_id: Optional[int]) -> None:
    p = await _get_portfolio(db, portfolio_id, user_id)
    await db.delete(p)
    await db.commit()


async def _load_transactions(db: AsyncSession, portfolio_id: int) -> List[SimTransaction]:
    result = await db.execute(
        select(SimTransaction)
        .where(SimTransaction.portfolio_id == portfolio_id)
        .order_by(SimTransaction.timestamp, SimTransaction.id)
    )
    return list(result.scalars().all())


# ── HOLDINGS (derived, average-cost) ───────────────────────────────
def _compute_holdings(transactions: List[SimTransaction]) -> dict:
    """Net quantity + average cost per ticker from the ledger. Sells reduce
    quantity at the running average cost (FIFO-agnostic average-cost method)."""
    book: dict[str, dict] = {}
    for tx in transactions:
        h = book.setdefault(tx.ticker, {"qty": 0.0, "avg_cost": 0.0})
        if tx.side == "BUY":
            new_qty = h["qty"] + tx.quantity
            if new_qty > 0:
                # Roll the buy fee into cost basis so avg_cost is the true breakeven.
                h["avg_cost"] = (h["qty"] * h["avg_cost"] + tx.quantity * tx.price + tx.fees) / new_qty
            h["qty"] = new_qty
        else:  # SELL — quantity drops, avg_cost unchanged
            h["qty"] = max(0.0, h["qty"] - tx.quantity)
            if h["qty"] <= 1e-9:
                h["qty"] = 0.0
                h["avg_cost"] = 0.0
    return {t: h for t, h in book.items() if h["qty"] > 0}


# ── TRADE EXECUTION ────────────────────────────────────────────────
async def place_trade(
    db: AsyncSession, portfolio: SimPortfolio, ticker: str, side: str, quantity: float, price: Optional[float]
) -> SimTransaction:
    ticker = ticker.upper().strip()
    side = side.upper()

    # Execution price: explicit limit price, else live market price.
    exec_price = price
    if exec_price is None:
        quote = await data_service.get_quote(ticker)
        exec_price = (quote or {}).get("price")
        if not exec_price or exec_price <= 0:
            raise HTTPException(status_code=400, detail=f"No live price for {ticker}; pass an explicit price")

    turnover = quantity * exec_price
    fees = round(turnover * FEE_RATE, 2)

    transactions = await _load_transactions(db, portfolio.id)
    holdings = _compute_holdings(transactions)
    realized = 0.0

    if side == "BUY":
        cost = turnover + fees
        if cost > portfolio.cash + 1e-6:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient cash: need ₹{cost:,.2f}, have ₹{portfolio.cash:,.2f}",
            )
        portfolio.cash = round(portfolio.cash - cost, 2)
    elif side == "SELL":
        held = holdings.get(ticker, {"qty": 0.0, "avg_cost": 0.0})
        if quantity > held["qty"] + 1e-9:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot sell {quantity} {ticker}: only {held['qty']:g} held",
            )
        proceeds = turnover - fees
        realized = round((exec_price - held["avg_cost"]) * quantity - fees, 2)
        portfolio.cash = round(portfolio.cash + proceeds, 2)
    else:
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")

    tx = SimTransaction(
        portfolio_id=portfolio.id, ticker=ticker, side=side, quantity=quantity,
        price=round(exec_price, 2), fees=fees, realized_pnl=realized,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),  # naive UTC (see models._utcnow)
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)
    return tx


# ── PORTFOLIO STATE (mark-to-market) ───────────────────────────────
async def get_portfolio_state(db: AsyncSession, portfolio: SimPortfolio) -> dict:
    transactions = await _load_transactions(db, portfolio.id)
    holdings = _compute_holdings(transactions)

    quotes = {}
    if holdings:
        quotes = await data_service.get_batch_quotes(list(holdings.keys()))

    holding_rows = []
    market_value = 0.0
    invested = 0.0
    for ticker, h in holdings.items():
        q = quotes.get(ticker) or {}
        cur_price = q.get("price") or h["avg_cost"]
        mv = h["qty"] * cur_price
        inv = h["qty"] * h["avg_cost"]
        market_value += mv
        invested += inv
        holding_rows.append({
            "ticker": ticker,
            "name": q.get("name", ticker),
            "quantity": round(h["qty"], 4),
            "avg_cost": round(h["avg_cost"], 2),
            "current_price": round(cur_price, 2),
            "market_value": round(mv, 2),
            "invested": round(inv, 2),
            "unrealized_pnl": round(mv - inv, 2),
            "unrealized_pnl_pct": round((mv - inv) / inv * 100, 2) if inv > 0 else 0.0,
            "change_pct": round(q.get("change_pct", 0.0) or 0.0, 2),
            "weight_pct": 0.0,  # filled below once total known
            "source": q.get("source", "live"),
        })

    # Position weights as share of holdings market value.
    for row in holding_rows:
        row["weight_pct"] = round(row["market_value"] / market_value * 100, 2) if market_value > 0 else 0.0
    holding_rows.sort(key=lambda r: r["market_value"], reverse=True)

    realized_pnl = round(sum(tx.realized_pnl for tx in transactions if tx.side == "SELL"), 2)
    unrealized_pnl = round(market_value - invested, 2)
    total_value = round(portfolio.cash + market_value, 2)
    total_pnl = round(total_value - portfolio.starting_capital, 2)

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "starting_capital": round(portfolio.starting_capital, 2),
        "cash": round(portfolio.cash, 2),
        "invested": round(invested, 2),
        "market_value": round(market_value, 2),
        "total_value": total_value,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl / portfolio.starting_capital * 100, 2) if portfolio.starting_capital else 0.0,
        "holdings": holding_rows,
        "holdings_count": len(holding_rows),
        "created_at": portfolio.created_at,
    }


async def list_transactions(db: AsyncSession, portfolio_id: int) -> List[dict]:
    txns = await _load_transactions(db, portfolio_id)
    return [{
        "id": tx.id, "ticker": tx.ticker, "side": tx.side, "quantity": tx.quantity,
        "price": tx.price, "fees": tx.fees, "realized_pnl": tx.realized_pnl,
        "timestamp": tx.timestamp,
    } for tx in reversed(txns)]


# ── PERFORMANCE (equity curve + stats) ─────────────────────────────
def _period_for_span(days: int) -> str:
    if days <= 30:
        return "3mo"
    if days <= 180:
        return "6mo"
    if days <= 365:
        return "1y"
    if days <= 730:
        return "2y"
    return "5y"


async def get_performance(db: AsyncSession, portfolio: SimPortfolio) -> dict:
    transactions = await _load_transactions(db, portfolio.id)
    state = await get_portfolio_state(db, portfolio)
    current_value = state["total_value"]

    sells = [tx for tx in transactions if tx.side == "SELL"]
    wins = [tx.realized_pnl for tx in sells if tx.realized_pnl > 0]
    losses = [tx.realized_pnl for tx in sells if tx.realized_pnl < 0]
    realized = [tx.realized_pnl for tx in sells]

    # ── Equity curve: reconstruct daily portfolio value from historical closes ──
    equity: List[dict] = []
    if transactions:
        import pandas as pd

        first_day = transactions[0].timestamp.date()
        today = datetime.now(timezone.utc).date()
        span_days = max(1, (today - first_day).days)
        period = _period_for_span(span_days)

        tickers = sorted({tx.ticker for tx in transactions})
        # Per ticker: parallel-sorted (dates, closes) for as-of lookups via bisect.
        hist: dict[str, tuple[list, list]] = {}
        for tk in tickers:
            try:
                df = await data_service.get_price_history(tk, period=period)
            except Exception:
                df = None
            if df is None or getattr(df, "empty", True):
                continue
            df = df.copy()
            df.columns = [str(c).lower() for c in df.columns]
            if "close" not in df.columns:
                continue
            ds, cs = [], []
            for ts, close in df["close"].items():
                if pd.isna(close):
                    continue
                ds.append(pd.Timestamp(ts).date())
                cs.append(float(close))
            if ds:
                hist[tk] = (ds, cs)

        def close_as_of(tk: str, d: date, fallback: float) -> float:
            pair = hist.get(tk)
            if not pair:
                return fallback
            dates, closes = pair
            i = bisect.bisect_right(dates, d) - 1
            return closes[i] if i >= 0 else (closes[0] if closes else fallback)

        # Date axis = union of all trading dates in range, plus today.
        axis = sorted({d for ds, _ in hist.values() for d in ds if first_day <= d <= today} | {today})
        if not axis:
            axis = [today]

        for d in axis:
            cash = portfolio.starting_capital
            qty: dict[str, float] = {}
            avg: dict[str, float] = {}
            for tx in transactions:
                if tx.timestamp.date() > d:
                    break
                if tx.side == "BUY":
                    nq = qty.get(tx.ticker, 0.0) + tx.quantity
                    if nq > 0:
                        avg[tx.ticker] = (qty.get(tx.ticker, 0.0) * avg.get(tx.ticker, 0.0)
                                          + tx.quantity * tx.price + tx.fees) / nq
                    qty[tx.ticker] = nq
                    cash -= tx.quantity * tx.price + tx.fees
                else:
                    qty[tx.ticker] = max(0.0, qty.get(tx.ticker, 0.0) - tx.quantity)
                    cash += tx.quantity * tx.price - tx.fees
            holdings_val = sum(q * close_as_of(tk, d, avg.get(tk, 0.0)) for tk, q in qty.items() if q > 0)
            equity.append({"date": d.isoformat(), "value": round(cash + holdings_val, 2)})

        # Thin to keep the chart light.
        if len(equity) > MAX_EQUITY_POINTS:
            step = len(equity) // MAX_EQUITY_POINTS
            equity = equity[::step] + [equity[-1]]
    else:
        today = datetime.now(timezone.utc).date()
        equity = [{"date": today.isoformat(), "value": round(portfolio.starting_capital, 2)}]

    # ── Risk stats from the equity curve ──
    max_dd = 0.0
    sharpe = 0.0
    if len(equity) >= 2:
        peak = equity[0]["value"]
        rets = []
        prev = equity[0]["value"]
        for pt in equity:
            v = pt["value"]
            peak = max(peak, v)
            if peak > 0:
                max_dd = min(max_dd, (v - peak) / peak)
            if prev:
                rets.append((v - prev) / prev)
            prev = v
        if rets:
            import statistics
            mean_r = statistics.fmean(rets)
            std_r = statistics.pstdev(rets) if len(rets) > 1 else 0.0
            if std_r > 0:
                sharpe = (mean_r / std_r) * (252 ** 0.5)

    return {
        "starting_capital": round(portfolio.starting_capital, 2),
        "current_value": current_value,
        "total_return_pct": round((current_value / portfolio.starting_capital - 1) * 100, 2) if portfolio.starting_capital else 0.0,
        "realized_pnl": round(sum(realized), 2),
        "unrealized_pnl": state["unrealized_pnl"],
        "trades_total": len(transactions),
        "sells_closed": len(sells),
        "win_rate": round(len(wins) / len(sells), 4) if sells else 0.0,
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "best_trade": round(max(realized), 2) if realized else 0.0,
        "worst_trade": round(min(realized), 2) if realized else 0.0,
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "equity_curve": equity,
    }
