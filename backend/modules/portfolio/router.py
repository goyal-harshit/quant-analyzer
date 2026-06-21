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

    # Gather every position once, then batch-quote all unique tickers in a single
    # concurrent pass (avoids the N+1 sequential get_quote per position).
    portfolio_positions: dict = {}
    all_tickers: set = set()
    for p in portfolios:
        pos_res = await db.execute(
            select(PositionModel).where(PositionModel.portfolio_id == p.id)
        )
        positions = pos_res.scalars().all()
        portfolio_positions[p.id] = positions
        all_tickers.update(pos.ticker for pos in positions)

    quote_map = await data_service.get_batch_quotes(list(all_tickers)) if all_tickers else {}

    result = []
    for p in portfolios:
        positions = portfolio_positions[p.id]
        total_value = 0.0
        total_cost = 0.0
        for pos in positions:
            quote = quote_map.get(pos.ticker) or {}
            price = (quote.get("price") if isinstance(quote, dict) else None) or pos.avg_cost
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
async def get_portfolio(portfolio_id: int, refresh: bool = False, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
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

    _all = await _gather_limited(
        [
            *[data_service.get_quote(t, refresh=refresh) for t in tickers],
            *[data_service.get_fundamentals(t, refresh=refresh) for t in tickers],
            *[data_service.get_price_history(t, period="1y", refresh=refresh) for t in tickers],
        ],
        limit=8,
    )
    
    _all_cleaned = [None if isinstance(x, Exception) else x for x in _all]
    n = len(tickers)
    quotes, funds, hists = _all_cleaned[:n], _all_cleaned[n:2*n], _all_cleaned[2*n:]
    
    quote_map = {t: (q if isinstance(q, dict) else {}) for t, q in zip(tickers, quotes)}
    fund_map = {t: (f if isinstance(f, dict) else {}) for t, f in zip(tickers, funds)}
    for t in tickers:
        f = fund_map.get(t) or {}
        if not f.get("sector"):
            f["sector"] = data_service._SECTOR_MAP.get(t) or "Diversified"
            f["industry"] = data_service._INDUSTRY_MAP.get(t) or "General"
            fund_map[t] = f
    hist_map = {t: (h if isinstance(h, pd.DataFrame) else pd.DataFrame()) for t, h in zip(tickers, hists)}

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

        # Get factor score
        composite = None
        try:
            from services.cache_service import cache
            cv = await cache.get(f"fs_{pos.ticker}")
            if cv:
                import json
                composite = json.loads(cv).get("composite")
        except Exception:
            pass
        if composite is None:
            try:
                import services.seed_data as _sd
                s = _sd._stock_dict(pos.ticker)
                composite = s.get("composite")
            except Exception:
                composite = 60

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
            factor_score=composite,
            sector=fund.get("sector"),
        ))

        total_value += current_value
        total_cost += cost_basis

        hist = hist_map.get(pos.ticker)
        if hist is not None and not hist.empty:
            hist_normalized = hist.copy()
            hist_normalized.columns = [c.lower() for c in hist_normalized.columns]
            if "close" in hist_normalized.columns:
                portfolio_returns_components[pos.ticker] = hist_normalized["close"] * pos.quantity

    beta, sharpe, vol, mdd = None, None, None, None
    if portfolio_returns_components:
        portfolio_value_series = pd.DataFrame(portfolio_returns_components).sum(axis=1).dropna()
        if len(portfolio_value_series) > 30:
            returns = PortfolioAnalytics.compute_returns(portfolio_value_series)
            sharpe = round(PortfolioAnalytics.sharpe_ratio(returns), 2)
            vol = round(float(returns.std() * (252 ** 0.5) * 100), 2)
            mdd = round(PortfolioAnalytics.max_drawdown(portfolio_value_series) * 100, 2)

            benchmark_res = await _gather_limited(
                [data_service.get_price_history("^NSEI", period="1y")], limit=1
            )
            benchmark_hist = benchmark_res[0] if benchmark_res and not isinstance(benchmark_res[0], Exception) else None
            if benchmark_hist is not None and not benchmark_hist.empty:
                bench_hist_normalized = benchmark_hist.copy()
                bench_hist_normalized.columns = [c.lower() for c in bench_hist_normalized.columns]
                if "close" in bench_hist_normalized.columns:
                    bench_returns = bench_hist_normalized["close"].pct_change().dropna()
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
async def remove_position(portfolio_id: int, position_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Remove a position from a portfolio."""
    result = await db.execute(select(PortfolioModel).where(PortfolioModel.id == portfolio_id, PortfolioModel.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    result = await db.execute(select(PositionModel).where(PositionModel.id == position_id, PositionModel.portfolio_id == portfolio_id))
    position = result.scalar_one_or_none()
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    await db.delete(position)
    await db.commit()
    return {"deleted": True}


@router.get("/{portfolio_id}/sector-allocation")
async def get_sector_allocation(portfolio_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get portfolio breakdown by sector — useful for concentration analysis."""
    result = await db.execute(select(PortfolioModel).where(PortfolioModel.id == portfolio_id, PortfolioModel.user_id == current_user.id))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

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
    _all2_cleaned = [None if isinstance(x, Exception) else x for x in _all2]
    n2 = len(tickers)
    quotes2, funds2 = _all2_cleaned[:n2], _all2_cleaned[n2:]
    quote_map = {t: (q if isinstance(q, dict) else {}) for t, q in zip(tickers, quotes2)}
    fund_map = {t: (f if isinstance(f, dict) else {}) for t, f in zip(tickers, funds2)}
    for t in tickers:
        f = fund_map.get(t) or {}
        if not f.get("sector"):
            f["sector"] = data_service._SECTOR_MAP.get(t) or "Diversified"
            f["industry"] = data_service._INDUSTRY_MAP.get(t) or "General"
            fund_map[t] = f

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


@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    benchmark: str = "NIFTY50",
    period: str = "1y",
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get portfolio performance vs a benchmark, normalized to 100 at start.
    """
    res = await db.execute(
        select(PortfolioModel).where(PortfolioModel.id == portfolio_id, PortfolioModel.user_id == current_user.id)
    )
    portfolio = res.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    pos_res = await db.execute(
        select(PositionModel).where(PositionModel.portfolio_id == portfolio_id)
    )
    positions = pos_res.scalars().all()
    if not positions:
        return {"performance": [], "benchmark": benchmark}

    import pandas as pd
    # Fetch all position histories concurrently (avoids the N+1 sequential awaits).
    hist_results = await _gather_limited(
        [data_service.get_price_history(pos.ticker, period=period, refresh=refresh) for pos in positions],
        limit=8,
    )
    history_dfs = {}
    for pos, df in zip(positions, hist_results):
        if df is not None and not isinstance(df, Exception) and not df.empty:
            df_copy = df.copy()
            df_copy.columns = [c.lower() for c in df_copy.columns]
            if "close" in df_copy.columns:
                history_dfs[pos.ticker] = df_copy["close"]

    if not history_dfs:
        return {"performance": [], "benchmark": benchmark}

    weighted_history = {}
    for pos in positions:
        ticker = pos.ticker
        if ticker in history_dfs:
            weighted_history[ticker] = history_dfs[ticker] * pos.quantity

    if not weighted_history:
        return {"performance": [], "benchmark": benchmark}

    combined_df = pd.DataFrame(weighted_history).ffill().bfill()
    portfolio_growth = combined_df.sum(axis=1)
    if not portfolio_growth.empty:
        portfolio_growth = (portfolio_growth / portfolio_growth.iloc[0]) * 100

    bench_ticker = "^NSEI" if benchmark.upper() == "NIFTY50" else benchmark
    bench_df = await data_service.get_price_history(bench_ticker, period=period, refresh=refresh)
    if bench_df.empty:
        bench_df = await data_service.get_price_history("^NSEI", period=period, refresh=refresh)
        
    if not bench_df.empty:
        bench_df_copy = bench_df.copy()
        bench_df_copy.columns = [c.lower() for c in bench_df_copy.columns]
        if "close" in bench_df_copy.columns:
            bench_growth = bench_df_copy["close"]
            bench_growth = (bench_growth / bench_growth.iloc[0]) * 100
        else:
            bench_growth = pd.Series(100.0, index=portfolio_growth.index)
    else:
        bench_growth = pd.Series(100.0, index=portfolio_growth.index)

    performance_data = []
    for idx in portfolio_growth.index:
        date_str = idx.strftime("%Y-%m-%d")
        port_val = float(portfolio_growth.loc[idx])
        bench_val = float(bench_growth.loc[idx]) if idx in bench_growth.index else 100.0
        performance_data.append({
            "date": date_str,
            "portfolio": round(port_val, 2),
            "benchmark": round(bench_val, 2),
        })

    return {
        "performance": performance_data,
        "benchmark": benchmark,
    }

