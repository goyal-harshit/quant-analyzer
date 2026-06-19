"""Portfolio Router — Position tracking and risk analytics"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from models.database import (
    get_db,
    User,
    Portfolio as PortfolioModel,
    Position as PositionModel,
)
from models.schemas import PortfolioCreate, PortfolioOut, PositionCreate, PositionOut, PortfolioSummary
from services.data_service import data_service, _gather_limited
from services.factor_engine import PortfolioAnalytics
from services.auth_service import get_current_user

router = APIRouter()


# _ensure_demo_user removed, auth middleware used instead


@router.get("", response_model=list[PortfolioSummary])
async def list_portfolios(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all portfolios for the current user."""
    user_id = current_user.id
    res = await db.execute(
        select(PortfolioModel).where(PortfolioModel.user_id == user_id)
    )
    portfolios = res.scalars().all()
    result = []
    for p in portfolios:
        pos_res = await db.execute(
            select(PositionModel).where(PositionModel.portfolio_id == p.id)
        )
        positions = pos_res.scalars().all()
        total_value = 0.0
        total_cost = 0.0
        for pos in positions:
            quote = await data_service.get_quote(pos.ticker)
            price = quote.get("price") or pos.avg_cost
            total_value += price * pos.quantity
            total_cost += pos.avg_cost * pos.quantity
        total_pnl = total_value - total_cost
        result.append(PortfolioSummary(
            id=p.id,
            name=p.name,
            total_value=round(total_value, 2),
            total_cost=round(total_cost, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round((total_pnl / total_cost * 100), 2) if total_cost > 0 else 0,
            position_count=len(positions),
        ))
    return result


@router.post("", response_model=dict)
async def create_portfolio(payload: PortfolioCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new portfolio for the user."""
    user_id = current_user.id
    portfolio = PortfolioModel(
        user_id=user_id,
        name=payload.name,
        currency=payload.currency,
        benchmark=payload.benchmark,
        description=payload.description,
    )
    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)
    return {"id": portfolio.id, "name": portfolio.name, "created": True}


@router.post("/{portfolio_id}/positions", response_model=dict)
async def add_position(portfolio_id: int, payload: PositionCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Add a position to a portfolio."""
    result = await db.execute(select(PortfolioModel).where(PortfolioModel.id == portfolio_id, PortfolioModel.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    position = PositionModel(
        portfolio_id=portfolio_id,
        ticker=payload.ticker.upper(),
        quantity=payload.quantity,
        avg_cost=payload.avg_cost,
        notes=payload.notes,
    )
    db.add(position)
    await db.commit()
    await db.refresh(position)
    return {"id": position.id, "ticker": position.ticker, "added": True}


@router.get("/{portfolio_id}")
async def get_portfolio(portfolio_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get full portfolio with live valuations, P&L, and risk analytics
    (beta, Sharpe, volatility, max drawdown vs benchmark).
    """
    result = await db.execute(select(PortfolioModel).where(PortfolioModel.id == portfolio_id, PortfolioModel.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    pos_result = await db.execute(
        select(PositionModel).where(PositionModel.portfolio_id == portfolio_id)
    )
    positions = pos_result.scalars().all()

    if not positions:
        return {
            "id": portfolio.id, "name": portfolio.name, "positions": [],
            "total_value": 0, "total_cost": 0, "total_pnl": 0, "total_pnl_pct": 0,
        }

    tickers = [p.ticker for p in positions]

    # Fetch everything in parallel with bounded concurrency so we don't
    # trigger Yahoo's HTTP 429 rate-limiter. (Was: serial `for pos in positions`
    # with 3 awaits per position + 1 benchmark = (3N+1) sequential calls.)
    # _gather_limited returns a flat list; slice it into groups.
    _all = await _gather_limited(
        [
            *[data_service.get_quote(t) for t in tickers],
            *[data_service.get_fundamentals(t) for t in tickers],
            *[data_service.get_price_history(t, period="1y") for t in tickers],
        ],
        limit=8,
    )
    n = len(tickers)
    quotes, funds, hists = _all[:n], _all[n:2*n], _all[2*n:]
    quote_map = dict(zip(tickers, quotes))
    fund_map = dict(zip(tickers, funds))
    # Fill sector/industry from hardcoded maps if missing
    for t in tickers:
        f = fund_map.get(t)
        if f and not f.get("sector"):
            f["sector"] = data_service._SECTOR_MAP.get(t)
            f["industry"] = data_service._INDUSTRY_MAP.get(t)
    hist_map = dict(zip(tickers, hists))

    position_outs = []
    total_value = 0.0
    total_cost = 0.0
    portfolio_returns_components = {}

    for pos in positions:
        quote = quote_map.get(pos.ticker) or {}
        fund = fund_map.get(pos.ticker) or {}

        current_price = quote.get("price") or pos.avg_cost
        current_value = current_price * pos.quantity
        cost_basis = pos.avg_cost * pos.quantity
        pnl = current_value - cost_basis

        position_outs.append(PositionOut(
            id=pos.id,
            ticker=pos.ticker,
            quantity=pos.quantity,
            avg_cost=pos.avg_cost,
            current_price=current_price,
            current_value=round(current_value, 2),
            cost_basis=round(cost_basis, 2),
            pnl=round(pnl, 2),
            pnl_pct=round((pnl / cost_basis * 100), 2) if cost_basis > 0 else 0,
            factor_score=None,  # populate from factor_scores table in production
            sector=fund.get("sector"),
        ))

        total_value += current_value
        total_cost += cost_basis

        hist = hist_map.get(pos.ticker)
        if hist is not None and not hist.empty:
            portfolio_returns_components[pos.ticker] = hist["close"] * pos.quantity

    # Compute portfolio-level risk metrics
    beta, sharpe, vol, mdd = None, None, None, None
    if portfolio_returns_components:
        portfolio_value_series = pd.DataFrame(portfolio_returns_components).sum(axis=1).dropna()
        if len(portfolio_value_series) > 30:
            returns = PortfolioAnalytics.compute_returns(portfolio_value_series)
            sharpe = round(PortfolioAnalytics.sharpe_ratio(returns), 2)
            vol = round(float(returns.std() * (252 ** 0.5) * 100), 2)
            mdd = round(PortfolioAnalytics.max_drawdown(portfolio_value_series) * 100, 2)

            # Benchmark fetch — bounded gather, single call
            (benchmark_hist,) = await _gather_limited(
                [data_service.get_price_history("^NSEI", period="1y")], limit=1
            )
            if benchmark_hist is not None and not benchmark_hist.empty:
                bench_returns = benchmark_hist["close"].pct_change().dropna()
                beta = round(PortfolioAnalytics.beta(returns, bench_returns), 2)

    total_pnl = total_value - total_cost

    return PortfolioOut(
        id=portfolio.id,
        name=portfolio.name,
        currency=portfolio.currency,
        benchmark=portfolio.benchmark,
        positions=position_outs,
        total_value=round(total_value, 2),
        total_cost=round(total_cost, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round((total_pnl / total_cost * 100), 2) if total_cost > 0 else 0,
        beta=beta,
        sharpe=sharpe,
        volatility=vol,
        max_drawdown=mdd,
    )


@router.delete("/{portfolio_id}/positions/{position_id}")
async def remove_position(portfolio_id: int, position_id: int, db: AsyncSession = Depends(get_db)):
    """Remove a position from a portfolio."""
    result = await db.execute(select(PositionModel).where(PositionModel.id == position_id))
    position = result.scalar_one_or_none()
    if not position or position.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail="Position not found")

    await db.delete(position)
    await db.commit()
    return {"deleted": True}


@router.get("/{portfolio_id}/sector-allocation")
async def get_sector_allocation(portfolio_id: int, db: AsyncSession = Depends(get_db)):
    """Get portfolio breakdown by sector — useful for concentration analysis."""
    pos_result = await db.execute(
        select(PositionModel).where(PositionModel.portfolio_id == portfolio_id)
    )
    positions = pos_result.scalars().all()

    if not positions:
        return {"allocation": [], "total_value": 0}

    tickers = [p.ticker for p in positions]
    _all2 = await _gather_limited(
        [
            *[data_service.get_quote(t) for t in tickers],
            *[data_service.get_fundamentals(t) for t in tickers],
        ],
        limit=8,
    )
    n2 = len(tickers)
    quotes2, funds2 = _all2[:n2], _all2[n2:]
    quote_map = dict(zip(tickers, quotes2))
    fund_map = dict(zip(tickers, funds2))
    for t in tickers:
        f = fund_map.get(t)
        if f and not f.get("sector"):
            f["sector"] = data_service._SECTOR_MAP.get(t)
            f["industry"] = data_service._INDUSTRY_MAP.get(t)

    sector_values: dict = {}
    total = 0.0
    for pos in positions:
        quote = quote_map.get(pos.ticker) or {}
        fund = fund_map.get(pos.ticker) or {}
        value = (quote.get("price") or pos.avg_cost) * pos.quantity
        sector = fund.get("sector") or "Unknown"
        sector_values[sector] = sector_values.get(sector, 0) + value
        total += value

    return {
        "allocation": [
            {"sector": s, "value": round(v, 2), "pct": round(v / total * 100, 1) if total > 0 else 0}
            for s, v in sorted(sector_values.items(), key=lambda x: -x[1])
        ],
        "total_value": round(total, 2),
    }


@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a portfolio and all its positions."""
    res = await db.execute(select(PortfolioModel).where(PortfolioModel.id == portfolio_id, PortfolioModel.user_id == current_user.id))
    portfolio = res.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    from sqlalchemy import delete
    await db.execute(delete(PositionModel).where(PositionModel.portfolio_id == portfolio_id))
    await db.delete(portfolio)
    await db.commit()
    return {"deleted": True, "id": portfolio_id}

